// Coffee shop print pilot (2026-10-10). Every /go/cNN page loads this file, so
// one edit here re-points all ten printed pieces. Never delete it: printed QR
// codes depend on it (go/PROTECTED.txt).
(function () {
  var piece = (location.pathname.match(/\/go\/(c\d+)/) || [])[1] || 'c00';
  // App Store custom product page for this campaign. Until cpp-cafe is
  // approved, this is cpp-site's ppid. PT is the provider token from App
  // Store Connect's campaign link generator; without it Apple ignores ct.
  var PPID = 'e70049f8-5df6-40f0-bfa9-3d224d4d5444';
  var PT = '';
  var ua = navigator.userAgent || '';
  var ios = /iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1);
  var android = /Android/.test(ua);
  var url;
  if (ios) {
    url = 'https://apps.apple.com/app/id6760280035?ppid=' + PPID + '&ct=cafe-' + piece + (PT ? '&pt=' + PT : '') + '&mt=8';
  } else if (android) {
    url = 'https://play.google.com/store/apps/details?id=com.elsewhere.dear&referrer=' +
      encodeURIComponent('utm_source=cafe&utm_medium=qr&utm_campaign=cafe_pilot&utm_content=' + piece);
  } else {
    url = 'https://dearnudges.com/?utm_source=cafe&utm_medium=qr&utm_campaign=cafe_pilot&utm_content=' + piece;
  }
  location.replace(url);
})();
