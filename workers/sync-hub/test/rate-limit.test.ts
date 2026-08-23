// SPDX-License-Identifier: Apache-2.0
//
// Pre-auth request ceiling (src/index.ts enforceIpRateLimit).
//
// The finding it closes: verdict caching is positive-only — deliberately, so a
// freshly issued token is never wrongly rejected — which means every request
// carrying a BAD token misses the cache and reaches TOKEN_VERIFY_URL. Without a
// ceiling, someone holding no valid credential at all turns each of their
// requests into one request against cmem.ai.
//
// Crossing the ceiling costs 121 real requests, so the whole behaviour is
// asserted from ONE exhaustion rather than one per property: a slower file
// makes the projection tests, which run a 100ms fetch timeout, flake.

import { SELF } from "cloudflare:test";
import { describe, expect, it } from "vitest";

const BASE = "https://sync-hub.test";
const LIMIT = 120; // wrangler.jsonc ratelimits[0].simple.limit

function get(headers: Record<string, string>): Promise<Response> {
  return SELF.fetch(`${BASE}/v1/sync/status`, { headers });
}

describe("pre-auth IP rate limit", () => {
  it("admits traffic under the ceiling, letting auth answer", async () => {
    // 401, not 429: the limiter passed it on and auth rejected it for carrying
    // no credentials. That ordering is the point.
    expect((await get({ "CF-Connecting-IP": "203.0.113.10" })).status).toBe(401);
  });

  it(
    "refuses a bad token pre-auth once its IP crosses the ceiling",
    async () => {
      const ip = "203.0.113.11";
      // A bad token exercises the exact amplification path: below the ceiling
      // each of these costs one upstream verification.
      const attacker = {
        "CF-Connecting-IP": ip,
        Authorization: "Bearer not-a-real-token",
        "X-User-Id": "victim",
      };

      let verified = 0;
      let refusal: Response | null = null;
      for (let i = 0; i < LIMIT + 5 && !refusal; i++) {
        const response = await get(attacker);
        if (response.status === 401) verified++;
        else if (response.status === 429) refusal = response;
        else throw new Error(`unexpected status ${response.status}`);
      }

      // Below the ceiling the token reached the verifier and was rejected...
      expect(verified).toBe(LIMIT);
      // ...above it, refused before any verification happened.
      expect(refusal).not.toBeNull();
      expect(refusal!.headers.get("Retry-After")).toBe("60");
      expect(await refusal!.json()).toEqual({ error: "too many requests" });

      // The bucket is per IP: another client is unaffected by this one.
      expect((await get({ "CF-Connecting-IP": "203.0.113.12" })).status).toBe(401);

      // And a request with no client IP is not swept into the exhausted bucket
      // — local dev and this test runner have no CF-Connecting-IP, so the
      // ceiling must not become an accidental gate there.
      expect((await get({})).status).toBe(401);
    },
    20_000,
  );
});
