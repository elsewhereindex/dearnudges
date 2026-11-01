// Scan counter for printed QR codes (2026-10-10).
// Runs in front of dearnudges.com/go/* and onewhim.app/go/*. Adds 1 to a per-day, per-path count in
// KV, then passes the request through to the site unchanged. Stores no cookie,
// IP, user agent or anything else about the person: just "c03 was opened once
// on 2026-10-14".
// FAIL OPEN: if counting breaks, the page must still load. A printed code
// that stops working because of analytics would be the worst trade here.
export default {
  async fetch(request, env, ctx) {
    try {
      // Count only the final page, /go/c03/. A code that encodes /go/c03 gets a
      // 301 to the slash form first, so counting both would double every scan.
      // The daily link check (tools/link-check.mjs) marks itself and is skipped.
      const raw = new URL(request.url).pathname;
      const path = raw.replace(/\/+$/, '');
      if (raw.endsWith('/') && /^\/go\/[a-z0-9-]+$/.test(path) && request.method === 'GET'
          && !request.headers.get('X-Link-Check')) {
        // onewhim.app/go/* shares this counter (2026-11-01); its slugs are
        // stored as whim-<slug> so they never mix with Dear's /go/ig and /go/tt.
        const host = new URL(request.url).hostname;
        const kpath = host.endsWith('onewhim.app') ? path.replace('/go/', '/go/whim-') : path;
        const key = new Date().toISOString().slice(0, 10) + ':' + kpath;
        ctx.waitUntil((async () => {
          const n = parseInt((await env.SCANS.get(key)) || '0', 10);
          await env.SCANS.put(key, String(n + 1));
        })().catch(() => {}));
      }
    } catch (_) {}
    return fetch(request);
  }
};
