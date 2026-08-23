// SPDX-License-Identifier: Apache-2.0
import { readFileSync } from 'fs';
import { logger } from '../../utils/logger.js';

/**
 * TLS options handed to node-postgres, a subset of Node's tls.ConnectionOptions.
 * `false` means the connection is made in plaintext.
 */
export type PostgresSslConfig =
  | false
  | {
      rejectUnauthorized: boolean;
      ca?: string;
      /** Present only for verify-ca, which checks the chain but not the hostname. */
      checkServerIdentity?: () => undefined;
    };

export interface PostgresConfig {
  connectionString: string;
  max: number;
  idleTimeoutMillis: number;
  connectionTimeoutMillis: number;
  statementTimeoutMillis: number;
  ssl: PostgresSslConfig;
}

export interface ParsePostgresConfigOptions {
  env?: NodeJS.ProcessEnv;
  requireDatabaseUrl?: boolean;
}

const DEFAULT_POOL_MAX = 10;
const DEFAULT_IDLE_TIMEOUT_MS = 30_000;
const DEFAULT_CONNECTION_TIMEOUT_MS = 5_000;
const DEFAULT_STATEMENT_TIMEOUT_MS = 30_000;

/**
 * The libpq sslmode values, and what each one means here.
 *
 * Previously only `disable` and `require` were recognised and anything else
 * fell through to "no TLS". That inverted the security ordering: an operator
 * who hardened their connection string to `verify-full` — libpq's STRONGEST
 * mode — got a plaintext connection, while `require` at least got encryption.
 * Unknown values now fail at startup instead of silently downgrading.
 *
 * `allow` and `prefer` negotiate in libpq: try one transport, fall back to the
 * other. node-postgres cannot express that (its `ssl` option is decided before
 * the connection opens), so both resolve to plaintext, which is the direction
 * that keeps working against a server without TLS. That matches the previous
 * behaviour for these values; it is called out in the type so nobody reads
 * `prefer` as "encrypted".
 */
const SSL_MODES = ['disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'] as const;
type SslMode = (typeof SSL_MODES)[number];

/** libpq's own default, and the behaviour this module had before. */
const DEFAULT_SSL_MODE: SslMode = 'prefer';

export function getPostgresDatabaseUrl(env: NodeJS.ProcessEnv = process.env): string | null {
  return env.CLAUDE_MEM_SERVER_DATABASE_URL || null;
}

export function parsePostgresConfig(options: ParsePostgresConfigOptions = {}): PostgresConfig | null {
  const env = options.env ?? process.env;
  const connectionString = getPostgresDatabaseUrl(env);
  if (!connectionString) {
    if (options.requireDatabaseUrl) {
      throw new Error('Postgres requires CLAUDE_MEM_SERVER_DATABASE_URL');
    }
    return null;
  }

  return {
    connectionString,
    max: parsePositiveInt(env.CLAUDE_MEM_POSTGRES_POOL_MAX, DEFAULT_POOL_MAX),
    idleTimeoutMillis: parsePositiveInt(env.CLAUDE_MEM_POSTGRES_IDLE_TIMEOUT_MS, DEFAULT_IDLE_TIMEOUT_MS),
    connectionTimeoutMillis: parsePositiveInt(env.CLAUDE_MEM_POSTGRES_CONNECTION_TIMEOUT_MS, DEFAULT_CONNECTION_TIMEOUT_MS),
    statementTimeoutMillis: parsePositiveInt(env.CLAUDE_MEM_POSTGRES_STATEMENT_TIMEOUT_MS, DEFAULT_STATEMENT_TIMEOUT_MS),
    ssl: parseSsl(connectionString, env)
  };
}

function parsePositiveInt(value: string | undefined, fallback: number): number {
  if (!value) {
    return fallback;
  }
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

/** Parse the connection string, tolerating a malformed one. */
function tryParseUrl(connectionString: string): URL | null {
  try {
    return new URL(connectionString);
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    logger.warn('DB', 'Failed to parse Postgres connection string; reading TLS settings from env only', {}, err);
    return null;
  }
}

function assertSslMode(value: string, source: string): SslMode {
  if ((SSL_MODES as readonly string[]).includes(value)) {
    return value as SslMode;
  }
  // Loud, at startup. A typo used to mean "no TLS"; now it means "don't start".
  throw new Error(
    `Invalid Postgres sslmode "${value}" from ${source}. Valid values: ${SSL_MODES.join(', ')}.`,
  );
}

/** Env wins over the connection string, matching how the other options resolve. */
function resolveSslMode(url: URL | null, env: NodeJS.ProcessEnv): SslMode {
  if (env.CLAUDE_MEM_POSTGRES_SSL) {
    return assertSslMode(env.CLAUDE_MEM_POSTGRES_SSL, 'CLAUDE_MEM_POSTGRES_SSL');
  }
  if (env.PGSSLMODE) {
    return assertSslMode(env.PGSSLMODE, 'PGSSLMODE');
  }
  const fromUrl = url?.searchParams.get('sslmode');
  if (fromUrl) {
    return assertSslMode(fromUrl, 'the connection string sslmode parameter');
  }
  return DEFAULT_SSL_MODE;
}

/**
 * Root certificate for the verify-* modes. Without one, Node validates against
 * the system trust store, which is what publicly-issued provider certificates
 * need; a private CA (RDS, an internal cluster) requires the file.
 */
function resolveRootCert(url: URL | null, env: NodeJS.ProcessEnv): string | undefined {
  const path =
    env.CLAUDE_MEM_POSTGRES_SSL_ROOT_CERT
    || env.PGSSLROOTCERT
    || url?.searchParams.get('sslrootcert')
    || null;
  if (!path) {
    return undefined;
  }
  try {
    return readFileSync(path, 'utf8');
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    // Fail loudly: silently ignoring the CA would fall back to the system store
    // and could either fail confusingly or verify against the wrong root.
    throw new Error(`Failed to read Postgres SSL root certificate at ${path}: ${err.message}`);
  }
}

function isLoopbackHost(host: string): boolean {
  return host === 'localhost' || host === '127.0.0.1' || host === '::1' || host === '[::1]';
}

export function parseSsl(connectionString: string, env: NodeJS.ProcessEnv): PostgresSslConfig {
  const url = tryParseUrl(connectionString);
  const mode = resolveSslMode(url, env);

  if (mode === 'disable' || mode === 'allow' || mode === 'prefer') {
    const host = url?.hostname ?? '';
    if (host && !isLoopbackHost(host)) {
      // Not an error — plaintext to a remote database is a deployment choice —
      // but it must be visible rather than a silent default.
      logger.warn('DB', 'Connecting to a non-local Postgres without TLS', {
        sslmode: mode,
        host,
        hint: 'Set sslmode=verify-full for a verified connection.',
      });
    }
    return false;
  }

  if (mode === 'require') {
    // libpq's own semantics: encrypted, but the certificate is not checked, so
    // this stops passive sniffing and not an active machine-in-the-middle.
    return { rejectUnauthorized: false };
  }

  const ca = resolveRootCert(url, env);
  if (mode === 'verify-ca') {
    // Chain verified, hostname deliberately not: that is what distinguishes
    // verify-ca from verify-full.
    return { rejectUnauthorized: true, ...(ca ? { ca } : {}), checkServerIdentity: () => undefined };
  }
  // verify-full — chain and hostname, Node's default identity check.
  return { rejectUnauthorized: true, ...(ca ? { ca } : {}) };
}
