// SPDX-License-Identifier: Apache-2.0
//
// `npx claude-mem install` used to run `curl -fsSL https://bun.sh/install | bash`
// (and the astral.sh equivalent) unattended: no prompt, no checksum, no
// signature, no version pin. The user asked for claude-mem and got two pieces
// of remote code executed as a side effect.
//
// These tests pin the two properties that replaced it: a verifying package
// manager is preferred when present, and the vendor script never runs without
// consent.

import { describe, expect, it } from 'bun:test';
import {
  REMOTE_INSTALL_OPT_IN,
  bunSpec,
  installRuntime,
  uvSpec,
  type RuntimeInstallDependencies,
  type RuntimeInstallSpec,
} from '../src/npx-cli/install/setup-runtime.js';

interface Harness {
  deps: RuntimeInstallDependencies;
  ran: string[];
  consentAsked: number;
}

function harness(options: {
  managers?: string[];
  consent?: boolean;
  interactive?: boolean;
  failCommands?: string[];
  installedAfter?: 'package-manager' | 'remote' | 'never';
  spec: RuntimeInstallSpec;
}): Harness {
  const ran: string[] = [];
  let consentAsked = 0;
  const installedAfter = options.installedAfter ?? 'package-manager';

  const succeeded: string[] = [];

  // The spec's own isInstalled is replaced so the harness decides when the
  // runtime "appears", without touching the machine. It keys off commands that
  // SUCCEEDED — a failed brew must not look like a completed install.
  options.spec.isInstalled = () => {
    if (installedAfter === 'never') return false;
    if (installedAfter === 'remote') return succeeded.includes(options.spec.remote.command);
    return succeeded.length > 0;
  };

  return {
    ran,
    get consentAsked() { return consentAsked; },
    deps: {
      hasPackageManager: (manager) => (options.managers ?? []).includes(manager),
      run: (command) => {
        ran.push(command);
        if ((options.failCommands ?? []).some(f => command.includes(f))) {
          throw new Error(`simulated failure: ${command}`);
        }
        succeeded.push(command);
      },
      consent: async () => {
        consentAsked++;
        return options.consent ?? false;
      },
      isInteractive: () => options.interactive ?? false,
    },
  };
}

describe('runtime install prefers a verifying package manager', () => {
  it('uses the package manager and never reaches the vendor script', async () => {
    const spec = bunSpec();
    const h = harness({ spec, managers: ['brew', 'winget'] });

    await installRuntime(spec, h.deps);

    expect(h.ran).toHaveLength(1);
    expect(h.ran[0]).toMatch(/^(brew|winget) install/);
    // The point of preferring a manager: no unverified download, and the user
    // is never asked, because nothing needed consent.
    expect(h.ran[0]).not.toContain('curl');
    expect(h.ran[0]).not.toContain('irm');
    expect(h.consentAsked).toBe(0);
  });

  it('falls through to the vendor script when the manager fails', async () => {
    const spec = bunSpec();
    const h = harness({
      spec,
      managers: ['brew', 'winget'],
      failCommands: ['brew', 'winget'],
      consent: true,
      installedAfter: 'remote',
    });

    await installRuntime(spec, h.deps);

    expect(h.ran).toHaveLength(2);
    expect(h.ran[1]).toBe(spec.remote.command);
    expect(h.consentAsked).toBe(1);
  });
});

describe('the vendor script never runs without consent', () => {
  it('refuses in a non-interactive shell and names the opt-in', async () => {
    const spec = bunSpec();
    const h = harness({ spec, consent: false, interactive: false });

    await expect(installRuntime(spec, h.deps)).rejects.toThrow(/non-interactive shell/);
    // Nothing was executed at all — that is the whole point.
    expect(h.ran).toEqual([]);

    // The refusal has to be actionable, or it just moves the problem.
    const error = await installRuntime(spec, h.deps).catch((e: Error) => e);
    expect(error.message).toContain(REMOTE_INSTALL_OPT_IN);
    expect(error.message).toContain('brew install oven-sh/bun/bun');
    expect(error.message).toContain(spec.remote.url);
  });

  it('reports a declined prompt differently from a non-interactive refusal', async () => {
    const spec = uvSpec();
    const h = harness({ spec, consent: false, interactive: true });

    const error = await installRuntime(spec, h.deps).catch((e: Error) => e);
    expect(error.message).toMatch(/Declined running the uv installer/);
    expect(h.ran).toEqual([]);
  });

  it('runs the script once consent is given', async () => {
    const spec = uvSpec();
    const h = harness({ spec, consent: true, installedAfter: 'remote' });

    await installRuntime(spec, h.deps);

    expect(h.ran).toEqual([spec.remote.command]);
  });
});

describe('post-install verification', () => {
  it('fails when the installer exits cleanly but leaves nothing usable', async () => {
    const spec = bunSpec();
    const h = harness({ spec, consent: true, installedAfter: 'never' });

    await expect(installRuntime(spec, h.deps)).rejects.toThrow(/binary not found/);
  });
});

describe('both runtimes are covered', () => {
  it('never points at a plain http vendor URL', () => {
    for (const spec of [bunSpec(), uvSpec()]) {
      expect(spec.remote.url.startsWith('https://')).toBe(true);
      expect(spec.packageManagers.length).toBeGreaterThan(0);
      expect(spec.manualInstructions.length).toBeGreaterThan(0);
    }
  });
});
