// Scan counter for printed QR codes (2026-10-10).
// Runs in front of dearnudges.com/go/*. Adds 1 to a per-day, per-path count in
// KV, then passes the request through to the site unchanged. Stores no cookie,
// IP, user agent or anything else about the person: just "c03 was opened once
// on 2026-10-14".
// FAIL OPEN: if counting breaks, the page must still load. A printed code
// that stops working because of analytics would be the worst trade here.
export default {
  async fetch(request, env, ctx) {
    try {
      const path = new URL(request.url).pathname.replace(/\/+$/, '');
      if (/^\/go\/[a-z0-9-]+$/.test(path) && request.method === 'GET') {
        const key = new Date().toISOString().slice(0, 10) + ':' + path;
        ctx.waitUntil((async () => {
          const n = parseInt((await env.SCANS.get(key)) || '0', 10);
          await env.SCANS.put(key, String(n + 1));
        })().catch(() => {}));
      }
    } catch (_) {}
    return fetch(request);
  }
};
