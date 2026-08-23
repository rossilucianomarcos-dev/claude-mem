// SPDX-License-Identifier: Apache-2.0
//
// #2552 — the Viewer UI + API compat layer must be reachable on the server
// runtime. We register ServerViewerRoutes alongside a stub API route on the
// SAME Express app (as ServerService does) and assert:
//   - the viewer root `/` responds (HTML when built, 503 when not),
//   - the static handler does NOT shadow a co-mounted API route.

import { afterEach, describe, expect, it, spyOn } from 'bun:test';
import { logger } from '../../src/utils/logger.js';
import { Server, type ServerOptions } from '../../src/services/server/Server.js';
import { ServerViewerRoutes } from '../../src/server/runtime/ServerViewerRoutes.js';
import { VIEWER_CONTENT_SECURITY_POLICY } from '../../src/shared/viewer-security-headers.js';

function baseOptions(): ServerOptions {
  return {
    getInitializationComplete: () => true,
    getMcpReady: () => true,
    onShutdown: () => Promise.resolve(),
    onRestart: () => Promise.resolve(),
    workerPath: '',
    getAiStatus: () => ({ provider: 'disabled', authMethod: 'api-key', lastInteraction: null }),
  };
}

describe('ServerViewerRoutes on the server runtime (#2552)', () => {
  let server: Server | null = null;
  let spies: ReturnType<typeof spyOn>[] = [];

  afterEach(async () => {
    spies.forEach(s => s.mockRestore());
    spies = [];
    if (server?.getHttpServer()) {
      try { await server.close(); } catch { /* ignore */ }
    }
    server = null;
  });

  it('serves the viewer root and does not shadow a co-mounted API route', async () => {
    spies = [
      spyOn(logger, 'info').mockImplementation(() => {}),
      spyOn(logger, 'warn').mockImplementation(() => {}),
    ];
    server = new Server(baseOptions());

    // Mirror ServerService: register an API route BEFORE the viewer's
    // static handler so we can prove the static handler does not swallow it.
    server.registerRoutes({
      setupRoutes(app) {
        app.get('/v1/info', (_req, res) => {
          res.json({ name: 'claude-mem-server', runtime: 'server-beta' });
        });
      },
    });
    server.registerRoutes(new ServerViewerRoutes());
    server.finalizeRoutes();

    const port = 42000 + Math.floor(Math.random() * 9000);
    await server.listen(port, '127.0.0.1');

    // The co-mounted API route still resolves (compat/v1 layer reachable).
    const apiRes = await fetch(`http://127.0.0.1:${port}/v1/info`);
    expect(apiRes.status).toBe(200);
    const apiBody = await apiRes.json();
    expect(apiBody.runtime).toBe('server-beta');

    // The viewer root route is registered and responds. When the build shipped
    // a viewer.html it is 200 text/html; otherwise it is a clean 503 (not a
    // 404/crash), proving the handler is mounted.
    const rootRes = await fetch(`http://127.0.0.1:${port}/`);
    if (ServerViewerRoutes.hasViewerHtml()) {
      expect(rootRes.status).toBe(200);
      expect(rootRes.headers.get('content-type')).toContain('text/html');
    } else {
      expect(rootRes.status).toBe(503);
      const body = await rootRes.json();
      expect(body.error).toBe('ViewerUnavailable');
    }
  });

  // The viewer renders observation text that began life as untrusted tool
  // output. Its raw-HTML sink is sanitized twice over (ansi-to-html escapeXML
  // + a DOMPurify span/div/br allowlist); these headers are the layer behind
  // that, so a future sanitizer bypass or a new sink is not immediately fatal.
  it('sends the viewer security headers on the document and on static assets', async () => {
    spies = [
      spyOn(logger, 'info').mockImplementation(() => {}),
      spyOn(logger, 'warn').mockImplementation(() => {}),
    ];
    server = new Server(baseOptions());
    server.registerRoutes(new ServerViewerRoutes());
    server.finalizeRoutes();

    const port = 42000 + Math.floor(Math.random() * 9000);
    await server.listen(port, '127.0.0.1');

    const expectHeaders = (res: Response) => {
      expect(res.headers.get('content-security-policy')).toBe(VIEWER_CONTENT_SECURITY_POLICY);
      expect(res.headers.get('x-content-type-options')).toBe('nosniff');
      expect(res.headers.get('x-frame-options')).toBe('DENY');
      expect(res.headers.get('referrer-policy')).toBe('no-referrer');
    };

    expectHeaders(await fetch(`http://127.0.0.1:${port}/`));

    // Static assets get them too: without nosniff a browser may content-sniff
    // the bundle or an SVG into something else.
    const asset = await fetch(`http://127.0.0.1:${port}/viewer-bundle.js`);
    if (asset.status === 200) expectHeaders(asset);
  });

  // Each directive below is load-bearing for something the viewer actually
  // loads. Asserting them individually makes an accidental loosening — most of
  // all script-src — fail here rather than silently ship.
  it('locks scripts to the origin and denies everything not explicitly needed', () => {
    const directives = new Map(
      VIEWER_CONTENT_SECURITY_POLICY.split('; ').map(d => {
        const [name, ...rest] = d.split(' ');
        return [name, rest.join(' ')];
      }),
    );

    expect(directives.get('default-src')).toBe("'none'");
    // No 'unsafe-inline' and no 'unsafe-eval' here: the bundle is a same-origin
    // <script src> built with minify + iife + sourcemap:false, so it needs neither.
    expect(directives.get('script-src')).toBe("'self'");
    expect(directives.get('object-src')).toBe("'none'");
    expect(directives.get('base-uri')).toBe("'none'");
    expect(directives.get('frame-ancestors')).toBe("'none'");
    // GitHubStarsButton fetches the star count; dropping this breaks it.
    expect(directives.get('connect-src')).toContain('https://api.github.com');
    // The template carries one inline <style> block and the components set
    // style={{...}} props, so style-src needs 'unsafe-inline'. That is the one
    // concession in the policy and it is deliberate — CSS-only injection is a
    // far narrower problem than script execution.
    expect(directives.get('style-src')).toContain("'unsafe-inline'");
    expect(directives.get('font-src')).toBe("'self'");
    expect(directives.get('img-src')).toBe("'self' data:");
  });
});
