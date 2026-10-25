/* 診断ページ共通のアクセス解析ヘルパー。
   gtag本体（測定ID G-ZNX5SY0GSK）は各ページの<head>で読み込む（サイトの他ページと同じプロパティ）。
   ここでは、診断固有のイベント送信 wmTrack() と、クリック計測の委譲だけを持つ。 */
window.wmTrack = function (name, params) {
  try { if (typeof gtag === 'function') gtag('event', name, params || {}); } catch (e) {}
};

// クリック計測：[セレクタ, イベント名, パラメータを作る関数]
(function () {
  const text = (el) => (el.textContent || '').replace(/\s+/g, ' ').replace(/[→›]\s*$/, '').trim().slice(0, 30);
  const RULES = [
    ['#spec-country-grid a',       'country_click',        (el) => ({ country: text(el) })],
    ['#spec-country-cta',          'more_countries_click', () => ({})],
    ['#spec-incl-open',            'manual_open',          () => ({})],
    ['#share-block a, #share-block button', 'share_click', (el) => ({ label: text(el) })],
    ['.cmp-row',                   'compat_click',         (el) => ({ to_type: (el.getAttribute('href') || '').replace('?type=', '') })],
    ['.cmp-all',                   'compat_all_click',     () => ({})],
    ['.lp-hero-copy .lp-btn-yellow', 'start_click',        () => ({ location: 'hero' })],
    ['.lp-cta-in .lp-btn-yellow',  'start_click',          () => ({ location: 'bottom' })],
    ['.lp-preview-more',           'types_click',          () => ({})],
  ];
  document.addEventListener('click', function (e) {
    for (const [sel, name, params] of RULES) {
      const el = e.target.closest && e.target.closest(sel);
      if (el) { window.wmTrack(name, params(el)); return; }
    }
  });
})();
