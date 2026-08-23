// SPDX-License-Identifier: Apache-2.0
//
// Single source of truth for the security headers on the Viewer UI.
//
// WHY
// ---
// The viewer renders observation content that originated as untrusted tool
// output (files read, HTTP responses, command stdout). Today the only raw-HTML
// sink — TerminalPreview — is doubly sanitized: ansi-to-html escapes entities
// with `escapeXML: true`, then DOMPurify runs with a span/div/br allowlist.
// That chain holds; these headers are the layer BEHIND it, for the day a
// DOMPurify bypass lands, the allowlist is loosened, or a new sink appears.
//
// The viewer is served from two runtimes — the in-plugin worker (ViewerRoutes)
// and the server-beta runtime (ServerViewerRoutes). Both must send the same
// headers, so the policy lives here rather than being duplicated at each call
// site where it could drift.
//
// POLICY NOTES
// ------------
// Every directive below was derived from what the viewer actually loads;
// tightening one further breaks a real feature:
//
//   script-src 'self'   The bundle is a same-origin <script src>. The esbuild
//                       config is minify + iife + sourcemap:false, so there is
//                       no eval and no 'unsafe-eval' needed.
//   style-src           viewer-template.html carries one inline <style> block
//     'unsafe-inline'   and the React components set style={{...}} props, both
//                       of which need it. This is the one concession in the
//                       policy: CSS-only injection is a far narrower problem
//                       than script execution, which stays locked to 'self'.
//   img-src data:       One inline SVG chevron is a data: URI in the template.
//   connect-src         Same-origin /api/* + the SSE stream, plus api.github.com
//                       for GitHubStarsButton's star count. Dropping the latter
//                       breaks that button.
//   font-src 'self'     Monaspace woff2/woff ship under ui/assets/fonts/.
//   default-src 'none'  Everything not named above is denied outright.
//
export const VIEWER_CONTENT_SECURITY_POLICY = [
  "default-src 'none'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self'",
  "connect-src 'self' https://api.github.com",
  "base-uri 'none'",
  "form-action 'none'",
  "frame-ancestors 'none'",
  "object-src 'none'",
].join('; ');

/**
 * Headers applied to every viewer response (the HTML document and its static
 * assets alike).
 *
 * `frame-ancestors` above already blocks framing in modern browsers;
 * X-Frame-Options is kept for older ones. Referrer-Policy keeps the local
 * viewer URL out of the Referer header on the api.github.com request.
 */
export const VIEWER_SECURITY_HEADERS: Readonly<Record<string, string>> = Object.freeze({
  'Content-Security-Policy': VIEWER_CONTENT_SECURITY_POLICY,
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'no-referrer',
});

/** Minimal shape of the response object both runtimes hand us. */
interface HeaderSink {
  setHeader(name: string, value: string): unknown;
}

/** Apply the shared viewer security headers to a response. */
export function applyViewerSecurityHeaders(res: HeaderSink): void {
  for (const [name, value] of Object.entries(VIEWER_SECURITY_HEADERS)) {
    res.setHeader(name, value);
  }
}
