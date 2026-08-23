// SPDX-License-Identifier: Apache-2.0
//
// parseSsl used to recognise only `disable` and `require`; every other libpq
// sslmode fell through to "no TLS". That inverted the security ordering — an
// operator who hardened their connection string to `verify-full`, libpq's
// strongest mode, silently got a plaintext connection, while the weaker
// `require` at least got encryption. These tests pin the mapping so the
// inversion cannot come back.

import { mkdtempSync, rmSync, writeFileSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';
import { afterEach, describe, expect, it } from 'bun:test';
import { parseSsl } from '../../../src/storage/postgres/config.js';

const REMOTE = 'postgres://u:p@db.example.com:5432/app';
const url = (query: string) => `${REMOTE}?${query}`;
const noEnv = {} as NodeJS.ProcessEnv;

const tempDirs: string[] = [];
function caFile(contents = '-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----\n'): string {
  const dir = mkdtempSync(join(tmpdir(), 'pg-ssl-'));
  tempDirs.push(dir);
  const path = join(dir, 'root.crt');
  writeFileSync(path, contents);
  return path;
}

afterEach(() => {
  while (tempDirs.length) {
    rmSync(tempDirs.pop()!, { recursive: true, force: true });
  }
});

describe('parseSsl sslmode mapping', () => {
  it('leaves the plaintext modes plaintext', () => {
    // node-postgres decides `ssl` before connecting, so it cannot do libpq's
    // allow/prefer negotiation; both resolve to plaintext, which is the
    // direction that still works against a server without TLS.
    for (const mode of ['disable', 'allow', 'prefer']) {
      expect(parseSsl(url(`sslmode=${mode}`), noEnv)).toBe(false);
    }
    expect(parseSsl(REMOTE, noEnv)).toBe(false);
  });

  it('encrypts without verifying for require, matching libpq', () => {
    const ssl = parseSsl(url('sslmode=require'), noEnv);
    expect(ssl).toEqual({ rejectUnauthorized: false });
  });

  it('verifies the chain but not the hostname for verify-ca', () => {
    const ssl = parseSsl(url('sslmode=verify-ca'), noEnv);
    expect(ssl).toMatchObject({ rejectUnauthorized: true });
    // The hostname override is exactly what separates verify-ca from verify-full.
    expect(typeof (ssl as { checkServerIdentity?: unknown }).checkServerIdentity).toBe('function');
  });

  it('verifies chain and hostname for verify-full', () => {
    const ssl = parseSsl(url('sslmode=verify-full'), noEnv);
    expect(ssl).toMatchObject({ rejectUnauthorized: true });
    // No override: Node performs its default hostname identity check.
    expect((ssl as { checkServerIdentity?: unknown }).checkServerIdentity).toBeUndefined();
  });

  // The regression itself, stated as an ordering property rather than as
  // specific values: a stricter mode must never produce a weaker connection.
  it('never makes a stricter mode weaker than a looser one', () => {
    const strength = (mode: string): number => {
      const ssl = parseSsl(url(`sslmode=${mode}`), noEnv);
      if (ssl === false) return 0;              // plaintext
      if (!ssl.rejectUnauthorized) return 1;    // encrypted, unverified
      return ssl.checkServerIdentity ? 2 : 3;   // chain, then chain + hostname
    };
    expect(strength('disable')).toBe(0);
    expect(strength('prefer')).toBe(0);
    expect(strength('require')).toBe(1);
    expect(strength('verify-ca')).toBe(2);
    expect(strength('verify-full')).toBe(3);
    // Before the fix verify-ca and verify-full both scored 0 — below require.
    expect(strength('verify-full')).toBeGreaterThan(strength('require'));
    expect(strength('verify-ca')).toBeGreaterThan(strength('require'));
  });
});

describe('parseSsl invalid input', () => {
  it('refuses an unknown sslmode instead of downgrading', () => {
    // A typo used to mean "no TLS". It now means "do not start".
    expect(() => parseSsl(url('sslmode=verify-fulll'), noEnv)).toThrow(/Invalid Postgres sslmode/);
    expect(() => parseSsl(REMOTE, { PGSSLMODE: 'yes' } as NodeJS.ProcessEnv)).toThrow(
      /Invalid Postgres sslmode "yes" from PGSSLMODE/,
    );
  });

  it('still honours an env sslmode when the connection string is unparseable', () => {
    const ssl = parseSsl('not-a-url', { CLAUDE_MEM_POSTGRES_SSL: 'verify-full' } as NodeJS.ProcessEnv);
    expect(ssl).toMatchObject({ rejectUnauthorized: true });
  });
});

describe('parseSsl precedence and root certificate', () => {
  it('lets env override the connection string', () => {
    const env = { CLAUDE_MEM_POSTGRES_SSL: 'verify-full' } as NodeJS.ProcessEnv;
    expect(parseSsl(url('sslmode=disable'), env)).toMatchObject({ rejectUnauthorized: true });
    // CLAUDE_MEM_POSTGRES_SSL wins over PGSSLMODE.
    const both = { CLAUDE_MEM_POSTGRES_SSL: 'disable', PGSSLMODE: 'verify-full' } as NodeJS.ProcessEnv;
    expect(parseSsl(REMOTE, both)).toBe(false);
  });

  it('loads a root certificate for the verify modes', () => {
    const path = caFile();
    const ssl = parseSsl(url('sslmode=verify-full'), { PGSSLROOTCERT: path } as NodeJS.ProcessEnv);
    expect(ssl).toMatchObject({ rejectUnauthorized: true });
    expect((ssl as { ca?: string }).ca).toContain('BEGIN CERTIFICATE');
  });

  it('reads sslrootcert from the connection string', () => {
    const path = caFile();
    const ssl = parseSsl(url(`sslmode=verify-ca&sslrootcert=${encodeURIComponent(path)}`), noEnv);
    expect((ssl as { ca?: string }).ca).toContain('BEGIN CERTIFICATE');
  });

  it('fails when a configured root certificate cannot be read', () => {
    // Ignoring it would silently fall back to the system trust store.
    expect(() =>
      parseSsl(url('sslmode=verify-full'), { PGSSLROOTCERT: '/nope/missing.crt' } as NodeJS.ProcessEnv),
    ).toThrow(/Failed to read Postgres SSL root certificate/);
  });

  it('does not read a certificate for the non-verifying modes', () => {
    const ssl = parseSsl(url('sslmode=require'), { PGSSLROOTCERT: '/nope/missing.crt' } as NodeJS.ProcessEnv);
    expect(ssl).toEqual({ rejectUnauthorized: false });
  });
});
