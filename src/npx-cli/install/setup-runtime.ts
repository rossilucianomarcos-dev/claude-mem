import { existsSync, readFileSync, writeFileSync } from 'fs';
import { exec, execSync, spawnSync, type SpawnSyncOptionsWithStringEncoding } from 'child_process';
import { createRequire } from 'module';
import { join } from 'path';
import { homedir } from 'os';
import { ErrorSeverity } from './error-taxonomy.js';
import { installerError, type InstallSummary } from './error-reporter.js';
import { USER_SETTINGS_PATH } from '../../shared/paths.js';
import { buildSpawnSyncInvocation, lookupWindowsCommand } from '../../shared/spawn.js';
import { IS_WINDOWS } from '../utils/paths.js';
import { parseJsonWithBom } from '../../shared/atomic-json.js';

const INSTALL_TIMEOUT_MS = (() => {
  const override = process.env.CLAUDE_MEM_INSTALL_TIMEOUT_MS;
  if (override && Number.isFinite(Number(override))) return Number(override);
  return 5 * 60 * 1000;
})();

/**
 * Platform-specific manual-install instructions, surfaced as the PRIMARY ABORT
 * message when auto-install fails or the binary can't be found afterward.
 */
export function platformBunRemediation(): string {
  return IS_WINDOWS
    ? 'Install Bun manually: `winget install Oven-sh.Bun` (or `powershell -c "irm bun.sh/install.ps1 | iex"`), then re-run `npx claude-mem install`.'
    : 'Install Bun manually: `brew install oven-sh/bun/bun` (or `curl -fsSL https://bun.sh/install | bash`), then re-run `npx claude-mem install`.';
}

export function platformUvRemediation(): string {
  return IS_WINDOWS
    ? 'Install uv manually: `winget install astral-sh.uv` (or `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`), then re-run `npx claude-mem install`.'
    : 'Install uv manually: `brew install uv` (or `curl -LsSf https://astral.sh/uv/install.sh | sh`), then re-run `npx claude-mem install`.';
}

function userHasOptedOutOfVectorSearch(): boolean {
  // Read the settings file directly (the value is not in the typed defaults).
  // Honors both a top-level key and an `env`-nested key.
  let raw: unknown;
  try {
    if (!existsSync(USER_SETTINGS_PATH)) return false;
    raw = parseJsonWithBom(readFileSync(USER_SETTINGS_PATH, 'utf-8'));
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    console.warn(`claude-mem: could not read ${USER_SETTINGS_PATH} while checking vector-search opt-out:`, err);
    return false;
  }
  if (!raw || typeof raw !== 'object') return false;
  const record = raw as Record<string, unknown>;
  const envBlock = (record.env && typeof record.env === 'object')
    ? (record.env as Record<string, unknown>)
    : {};
  const value = record.CLAUDE_MEM_DISABLE_VECTOR_SEARCH ?? envBlock.CLAUDE_MEM_DISABLE_VECTOR_SEARCH;
  return value === true || value === 'true' || value === '1';
}

const BUN_COMMON_PATHS = IS_WINDOWS
  ? [join(homedir(), '.bun', 'bin', 'bun.exe')]
  : [join(homedir(), '.bun', 'bin', 'bun'), '/usr/local/bin/bun', '/opt/homebrew/bin/bun', '/home/linuxbrew/.linuxbrew/bin/bun'];

const UV_COMMON_PATHS = IS_WINDOWS
  ? [join(homedir(), '.local', 'bin', 'uv.exe'), join(homedir(), '.cargo', 'bin', 'uv.exe')]
  : [join(homedir(), '.local', 'bin', 'uv'), join(homedir(), '.cargo', 'bin', 'uv'), '/usr/local/bin/uv', '/opt/homebrew/bin/uv'];

interface MarkerSchema {
  version: string;
  bun?: string;
  uv?: string;
  installedAt?: string;
}

const LEGACY_VERSION_MARKER_RE =
  /^v?\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/;

function markerPath(targetDir: string): string {
  return join(targetDir, '.install-version');
}

function spawnVersionProbe(command: string, args: string[]) {
  const options: SpawnSyncOptionsWithStringEncoding = {
    encoding: 'utf-8',
    stdio: ['pipe', 'pipe', 'pipe'],
  };
  const invocation = buildSpawnSyncInvocation(command, args, options);
  return spawnSync(invocation.command, invocation.args, invocation.options);
}

function getToolPath(command: string, commonPaths: string[]): string | null {
  const pathCommand = IS_WINDOWS ? lookupWindowsCommand(command) : command;
  try {
    if (pathCommand) {
      const result = spawnVersionProbe(pathCommand, ['--version']);
      if (result.status === 0) return pathCommand;
    }
  } catch {
    // Not in PATH
  }

  return commonPaths.find(existsSync) || null;
}

export function getBunPath(): string | null {
  return getToolPath('bun', BUN_COMMON_PATHS);
}

function isBunInstalled(): boolean {
  return getBunPath() !== null;
}

export function getBunVersion(): string | null {
  const bunPath = getBunPath();
  if (!bunPath) return null;

  try {
    const result = spawnVersionProbe(bunPath, ['--version']);
    return result.status === 0 ? result.stdout.trim() : null;
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    console.warn('claude-mem: bun --version probe failed:', err);
    return null;
  }
}

function getUvPath(): string | null {
  return getToolPath('uv', UV_COMMON_PATHS);
}

function isUvInstalled(): boolean {
  return getUvPath() !== null;
}

export function getUvVersion(): string | null {
  const uvPath = getUvPath();
  if (!uvPath) return null;

  try {
    const result = spawnVersionProbe(uvPath, ['--version']);
    return result.status === 0 ? result.stdout.trim() : null;
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    console.warn('claude-mem: uv --version probe failed:', err);
    return null;
  }
}

function describeExecError(error: unknown): string {
  if (error && typeof error === 'object') {
    const e = error as { message?: string; stdout?: Buffer | string; stderr?: Buffer | string };
    const parts: string[] = [];
    if (e.message) parts.push(e.message);
    const stderr = e.stderr ? e.stderr.toString().trim() : '';
    if (stderr) parts.push(`stderr: ${stderr}`);
    const stdout = e.stdout ? e.stdout.toString().trim() : '';
    if (!stderr && stdout) parts.push(`stdout: ${stdout}`);
    return parts.join('\n');
  }
  return String(error);
}

/**
 * Runtime auto-install.
 *
 * THE PROBLEM THIS SHAPE SOLVES
 * -----------------------------
 * `npx claude-mem install` used to run `curl -fsSL https://bun.sh/install | bash`
 * (and the astral.sh equivalent for uv) unattended: no prompt, no checksum, no
 * signature, no version pin. The user asked to install claude-mem and got two
 * pieces of remote code executed on their machine as a side effect. A
 * compromise of either vendor domain — or of the TLS path to it — is arbitrary
 * code execution during install.
 *
 * The scripts themselves cannot be pinned to a checksum: they are rolling
 * installers whose contents change with every upstream release, so a pinned
 * hash would break on the vendor's next publish rather than protect anything.
 * What CAN be improved is the order of preference and the consent:
 *
 *   1. A package manager first, when one is present. winget and Homebrew
 *      verify what they install; that is real verification, and it costs the
 *      user nothing when the manager is already there.
 *   2. The vendor script only as a fallback, and only with consent — an
 *      interactive confirm, or an explicit opt-in for non-interactive runs.
 *
 * Note on the uv PowerShell line: `-ExecutionPolicy ByPass` looks like an extra
 * weakening but is not meaningfully one — piping to `iex` already runs the
 * script regardless of policy. It stays because dropping it breaks installs on
 * machines with a restrictive policy while buying nothing.
 */

/** Opt-in for non-interactive runs (CI, Docker builds, provisioning scripts). */
export const REMOTE_INSTALL_OPT_IN = 'CLAUDE_MEM_ALLOW_REMOTE_RUNTIME_INSTALL';

export interface RuntimeInstallSpec {
  /** Display name used in prompts and errors. */
  tool: string;
  /** Package-manager attempts, tried in order and skipped when absent. */
  packageManagers: { manager: string; command: string }[];
  /** Vendor script fallback: unverified remote code, so it needs consent. */
  remote: { url: string; command: string; shell: string };
  /** Post-install check — the installer can exit 0 and still leave nothing usable. */
  isInstalled: () => boolean;
  /** Manual steps, shown when everything else is refused or fails. */
  manualInstructions: string;
}

export function bunSpec(): RuntimeInstallSpec {
  return {
    tool: 'Bun',
    packageManagers: IS_WINDOWS
      ? [{ manager: 'winget', command: 'winget install --silent --accept-package-agreements --accept-source-agreements Oven-sh.Bun' }]
      : [{ manager: 'brew', command: 'brew install oven-sh/bun/bun' }],
    remote: IS_WINDOWS
      ? { url: 'https://bun.sh/install.ps1', command: 'powershell -c "irm bun.sh/install.ps1 | iex"', shell: process.env.ComSpec ?? 'cmd.exe' }
      : { url: 'https://bun.sh/install', command: 'curl -fsSL https://bun.sh/install | bash', shell: '/bin/bash' },
    isInstalled: isBunInstalled,
    manualInstructions: IS_WINDOWS
      ? '  - winget install Oven-sh.Bun\n  - Or: powershell -c "irm bun.sh/install.ps1 | iex"'
      : '  - brew install oven-sh/bun/bun\n  - Or: curl -fsSL https://bun.sh/install | bash',
  };
}

export function uvSpec(): RuntimeInstallSpec {
  return {
    tool: 'uv',
    packageManagers: IS_WINDOWS
      ? [{ manager: 'winget', command: 'winget install --silent --accept-package-agreements --accept-source-agreements astral-sh.uv' }]
      : [{ manager: 'brew', command: 'brew install uv' }],
    remote: IS_WINDOWS
      ? { url: 'https://astral.sh/uv/install.ps1', command: 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"', shell: process.env.ComSpec ?? 'cmd.exe' }
      : { url: 'https://astral.sh/uv/install.sh', command: 'curl -LsSf https://astral.sh/uv/install.sh | sh', shell: '/bin/bash' },
    isInstalled: isUvInstalled,
    manualInstructions: IS_WINDOWS
      ? '  - winget install astral-sh.uv\n  - Or: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"'
      : '  - brew install uv\n  - Or: curl -LsSf https://astral.sh/uv/install.sh | sh',
  };
}

/** Is this package manager callable? Absent is the normal case, not an error. */
function hasPackageManager(manager: string): boolean {
  try {
    const command = IS_WINDOWS ? lookupWindowsCommand(manager) : manager;
    if (!command) return false;
    return spawnVersionProbe(command, ['--version']).status === 0;
  } catch {
    return false;
  }
}

function runInstallCommand(command: string, shell: string): void {
  execSync(command, { stdio: 'pipe', timeout: INSTALL_TIMEOUT_MS, shell });
}

/**
 * Consent for executing a vendor script fetched at install time.
 *
 * Interactive: ask. Non-interactive: refuse unless the opt-in env var is set —
 * a CI job silently executing remote code is exactly the case worth stopping,
 * and the refusal names both the variable and the manual commands.
 */
async function consentToRemoteInstall(spec: RuntimeInstallSpec): Promise<boolean> {
  if (process.env[REMOTE_INSTALL_OPT_IN] === '1') return true;
  if (!process.stdin.isTTY) return false;

  const p = await import('@clack/prompts');
  p.log.warn(
    `${spec.tool} is required and no package manager was available to install it.\n`
    + `The fallback runs a script downloaded from ${spec.remote.url}:\n`
    + `  ${spec.remote.command}\n`
    + 'That executes code from the vendor with no checksum or signature to verify it.',
  );
  const answer = await p.confirm({
    message: `Run the ${spec.tool} installer from ${new URL(spec.remote.url).host}?`,
    initialValue: false,
  });
  return !p.isCancel(answer) && answer === true;
}

/**
 * Seams for tests: this function's whole job is deciding what to execute and
 * whether consent was given, and neither is observable if it really installs a
 * runtime. Production passes nothing and gets the real implementations.
 */
export interface RuntimeInstallDependencies {
  hasPackageManager: (manager: string) => boolean;
  run: (command: string, shell: string) => void;
  consent: (spec: RuntimeInstallSpec) => Promise<boolean>;
  isInteractive: () => boolean;
}

function defaultInstallDependencies(): RuntimeInstallDependencies {
  return {
    hasPackageManager,
    run: runInstallCommand,
    consent: consentToRemoteInstall,
    isInteractive: () => Boolean(process.stdin.isTTY),
  };
}

/**
 * Install one runtime: package manager first, vendor script second and only
 * with consent. Throws with manual instructions when nothing succeeded.
 */
export async function installRuntime(
  spec: RuntimeInstallSpec,
  dependencies: RuntimeInstallDependencies = defaultInstallDependencies(),
): Promise<void> {
  const attempts: string[] = [];

  for (const { manager, command } of spec.packageManagers) {
    if (!dependencies.hasPackageManager(manager)) continue;
    try {
      dependencies.run(command, IS_WINDOWS ? (process.env.ComSpec ?? 'cmd.exe') : '/bin/sh');
      if (spec.isInstalled()) return;
      attempts.push(`${manager}: completed but ${spec.tool} was still not found`);
    } catch (error) {
      // A package manager that fails is not fatal — fall through to the script.
      attempts.push(`${manager}: ${describeExecError(error)}`);
    }
  }

  if (!(await dependencies.consent(spec))) {
    const why = dependencies.isInteractive()
      ? `Declined running the ${spec.tool} installer from ${spec.remote.url}.`
      : `Refusing to run the ${spec.tool} installer from ${spec.remote.url} in a non-interactive shell.`;
    throw new Error(
      `${why}\nInstall ${spec.tool} yourself:\n${spec.manualInstructions}\n`
      + `Or, to allow the download for automated runs, set ${REMOTE_INSTALL_OPT_IN}=1.\n`
      + 'Then re-run `npx claude-mem install`.'
      + (attempts.length ? `\nEarlier attempts: ${attempts.join('; ')}` : ''),
    );
  }

  try {
    dependencies.run(spec.remote.command, spec.remote.shell);
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    throw new Error(
      `Failed to install ${spec.tool}. Please install manually:\n${spec.manualInstructions}\n`
      + `Then restart your terminal and try again.\nUnderlying error: ${describeExecError(err)}`,
    );
  }

  if (!spec.isInstalled()) {
    throw new Error(
      `${spec.tool} installation completed but binary not found. Please restart your terminal and try again.`,
    );
  }
}

function installBun(): Promise<void> {
  return installRuntime(bunSpec());
}

function installUv(): Promise<void> {
  return installRuntime(uvSpec());
}

/**
 * Subpath imports the bundled worker requires transitively (via
 * @modelcontextprotocol/sdk / @anthropic-ai/claude-agent-sdk). A stale/partial
 * install can leave the `zod` directory present while these subpath exports fail
 * to resolve — surfacing later as a runtime `Cannot find module 'zod/v3'`. We
 * assert them at install time so a broken closure fails LOUD here. Version-agnostic:
 * we resolve subpaths, never a pinned version.
 */
const ZOD_REQUIRED_SUBPATHS = ['zod/v3', 'zod/v4', 'zod/v4-mini'] as const;

export function verifyCriticalModules(targetDir: string): void {
  const pkg = JSON.parse(readFileSync(join(targetDir, 'package.json'), 'utf-8'));
  const dependencies = Object.keys(pkg.dependencies || {});

  const nodeModulesPath = join(targetDir, 'node_modules');
  // A require anchored inside the install tree so require.resolve honors the
  // installed package.json `exports` map for subpath resolution.
  const requireFromTarget = createRequire(join(nodeModulesPath, 'noop.js'));
  const resolvePaths = [nodeModulesPath];

  const unresolvable: string[] = [];

  // Each declared dependency must be installed, not merely a directory on disk.
  for (const dep of dependencies) {
    try {
      requireFromTarget.resolve(dep, { paths: resolvePaths });
    } catch {
      // [ANTI-PATTERN IGNORED]: bare-name resolve failure is the probed signal here
      // (expected for bin-only packages); genuinely missing deps are collected in
      // `unresolvable` and surfaced as a loud install failure after the loop.
      // Bare-name resolution can fail for a perfectly-installed package that has
      // no importable entry point — e.g. bin-only packages like `tree-sitter-cli`
      // (package.json has `bin` but no `main`/`module`/`exports`/`index.js`).
      // Fall back to resolving its package.json to distinguish "installed but
      // bin-only" from "genuinely missing": a truly absent package fails both.
      // This preserves the original "is it installed" guarantee while still
      // upgrading from directory-existence to real module resolution (#2730).
      try {
        requireFromTarget.resolve(`${dep}/package.json`, { paths: resolvePaths });
      } catch {
        unresolvable.push(dep);
      }
    }
  }

  // zod ships its public API behind subpath exports the worker bundle requires.
  // The package dir existing does NOT imply these subpaths resolve (#2730).
  if (dependencies.includes('zod')) {
    for (const subpath of ZOD_REQUIRED_SUBPATHS) {
      try {
        requireFromTarget.resolve(subpath, { paths: resolvePaths });
      } catch {
        // [ANTI-PATTERN IGNORED]: subpath resolve failure is the condition being
        // probed; it is collected in `unresolvable` and surfaced as a loud
        // install failure below.
        unresolvable.push(subpath);
      }
    }
  }

  if (unresolvable.length > 0) {
    throw new Error(
      `Post-install check failed: unresolvable modules: ${unresolvable.join(', ')}`,
    );
  }
}

/** Build an ephemeral summary so callers (e.g. repair) may omit it. */
function summaryOrEphemeral(summary?: InstallSummary): InstallSummary {
  return summary ?? { warnings: [], failedIDEs: [] };
}

export async function ensureBun(summary?: InstallSummary): Promise<{ bunPath: string; version: string }> {
  const sum = summaryOrEphemeral(summary);
  if (!isBunInstalled()) {
    // installBun throws a platform-specific Error on failure; route it through
    // the central decision point so it becomes a loud ABORT (bun is mandatory
    // for hooks — there is no opt-out).
    try {
      await installBun();
    } catch (error: unknown) {
      const err = error instanceof Error ? error : new Error(String(error));
      // installerError(ABORT) reports the cause loudly and always throws.
      installerError(ErrorSeverity.ABORT, {
        component: 'bun-install',
        phase: 'setup-runtime',
        cause: err,
        remediation: platformBunRemediation(),
      }, sum);
    }
  }

  let bunPath = getBunPath();
  if (!bunPath) {
    bunPath = BUN_COMMON_PATHS.find(existsSync) ?? null;
  }
  if (!bunPath) {
    installerError(ErrorSeverity.ABORT, {
      component: 'bun-install',
      phase: 'setup-runtime',
      cause: new Error('Bun executable not found after auto-install attempt'),
      remediation: platformBunRemediation(),
    }, sum);
    throw new Error('unreachable'); // installerError(ABORT) always throws
  }

  let version = getBunVersion();
  if (!version) {
    // A fresh binary sometimes needs a moment before --version responds.
    await new Promise((r) => setTimeout(r, 1000));
    version = getBunVersion();
  }
  if (!version) {
    installerError(ErrorSeverity.WARN_CONTINUE, {
      component: 'bun-version-probe',
      phase: 'setup-runtime',
      cause: new Error(`Bun at ${bunPath} did not respond to --version after retry`),
    }, sum);
    return { bunPath, version: 'unknown' };
  }
  return { bunPath, version };
}

export async function ensureUv(
  summary?: InstallSummary,
  options: { allowVectorSearchOptOut?: boolean } = {},
): Promise<{ uvPath: string; version: string }> {
  const sum = summaryOrEphemeral(summary);
  if (!isUvInstalled()) {
    try {
      await installUv();
    } catch (error: unknown) {
      const err = error instanceof Error ? error : new Error(String(error));
      if (options.allowVectorSearchOptOut && userHasOptedOutOfVectorSearch()) {
        installerError(ErrorSeverity.WARN_CONTINUE, {
          component: 'uv-install',
          phase: 'setup-runtime',
          cause: err,
        }, sum);
        return { uvPath: '', version: 'unknown' };
      }
      // installerError(ABORT) reports the cause loudly and always throws.
      installerError(ErrorSeverity.ABORT, {
        component: 'uv-install',
        phase: 'setup-runtime',
        cause: err,
        remediation: platformUvRemediation(),
      }, sum);
    }
  }

  let uvPath = getUvPath();
  if (!uvPath) {
    // Re-probe UV_COMMON_PATHS directly — PATH may not yet include ~/.local/bin
    // in the current shell even though the install just wrote the binary there.
    uvPath = UV_COMMON_PATHS.find(existsSync) ?? null;
  }
  if (!uvPath) {
    if (options.allowVectorSearchOptOut && userHasOptedOutOfVectorSearch()) {
      installerError(ErrorSeverity.WARN_CONTINUE, {
        component: 'uv-install',
        phase: 'setup-runtime',
        cause: new Error('uv binary not found after install; vector search disabled — continuing.'),
      }, sum);
      return { uvPath: '', version: 'unknown' };
    }
    installerError(ErrorSeverity.ABORT, {
      component: 'uv-install',
      phase: 'setup-runtime',
      cause: new Error('uv binary not found after auto-install attempt'),
      remediation: platformUvRemediation(),
    }, sum);
    throw new Error('unreachable'); // installerError(ABORT) always throws
  }

  let version = getUvVersion();
  if (!version) {
    await new Promise((r) => setTimeout(r, 1000));
    version = getUvVersion();
  }
  if (!version) {
    installerError(ErrorSeverity.WARN_CONTINUE, {
      component: 'uv-version-probe',
      phase: 'setup-runtime',
      cause: new Error(`uv at ${uvPath} did not respond to --version after retry`),
    }, sum);
    return { uvPath, version: 'unknown' };
  }
  return { uvPath, version };
}

export async function installPluginDependencies(targetDir: string, bunPath: string): Promise<void> {
  if (!existsSync(join(targetDir, 'package.json'))) {
    throw new Error(`installPluginDependencies: no package.json at ${targetDir}`);
  }

  const bunCmd = IS_WINDOWS && bunPath.includes(' ') ? `"${bunPath}"` : bunPath;

  // Per CHANGELOG v12.6.1 -> v12.6.2: tree-sitter-swift's nested
  // tree-sitter-cli postinstall downloads a Rust binary and can hang the
  // install. Bun honors trustedDependencies; npm does not. We additionally
  // pass --ignore-scripts as belt-and-suspenders and bound it with a timeout.
  // Async exec (not execSync): a blocked event loop freezes the installer's
  // clack spinner for the duration of the install, which reads as a stall.
  const runBunInstall = (): Promise<void> =>
    new Promise<void>((resolve, reject) => {
      exec(`${bunCmd} install --frozen-lockfile --ignore-scripts`, {
        cwd: targetDir,
        timeout: INSTALL_TIMEOUT_MS,
        maxBuffer: 16 * 1024 * 1024,
        ...(IS_WINDOWS ? { shell: process.env.ComSpec ?? 'cmd.exe' } : {}),
      }, (error, stdout, stderr) =>
        // exec errors don't carry stdio; attach so describeExecError can report it.
        error ? reject(Object.assign(error, { stdout, stderr })) : resolve());
    });

  try {
    await runBunInstall();
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    throw new Error(`bun install failed in ${targetDir}\n${describeExecError(err)}`);
  }

  verifyCriticalModules(targetDir);
}

export function readInstallMarker(targetDir: string): MarkerSchema | null {
  const path = markerPath(targetDir);
  if (!existsSync(path)) return null;
  const content = readFileSync(path, 'utf-8');
  try {
    const marker = JSON.parse(content);
    if (marker && typeof marker === 'object' && typeof marker.version === 'string') {
      return marker as MarkerSchema;
    }
  } catch {
    // Legacy installs wrote only the version string as plain text.
  }

  const legacyVersion = content.trim();
  if (LEGACY_VERSION_MARKER_RE.test(legacyVersion)) {
    return { version: legacyVersion.replace(/^v/i, '') };
  }

  return null;
}

export function writeInstallMarker(
  targetDir: string,
  version: string,
  bunVersion: string,
  uvVersion: string,
): void {
  const payload: MarkerSchema = {
    version,
    bun: bunVersion,
    uv: uvVersion,
    installedAt: new Date().toISOString(),
  };
  writeFileSync(markerPath(targetDir), JSON.stringify(payload));
}

export function isInstallCurrent(targetDir: string, expectedVersion: string): boolean {
  if (!existsSync(join(targetDir, 'node_modules'))) return false;
  const marker = readInstallMarker(targetDir);
  if (!marker) return false;
  if (marker.version !== expectedVersion) return false;
  const currentBun = getBunVersion();
  if (currentBun && !marker.bun) return false;
  if (!currentBun && marker.bun) return false;
  if (currentBun && marker.bun && currentBun !== marker.bun) return false;
  return true;
}
