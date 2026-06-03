(() => {
  const COUNTRIES = [
    { name: "マレーシア",           region: "東南アジア",  path: "malaysia/index.html",     available: true },
    { name: "タイ",                 region: "東南アジア",  path: "thailand/index.html",     available: true },
    { name: "シンガポール",          region: "東南アジア",  path: null,                      available: false },
    { name: "ベトナム",              region: "東南アジア",  path: null,                      available: false },
    { name: "バリ島（インドネシア）", region: "東南アジア",  path: null,                      available: false },
    { name: "台湾",                 region: "東アジア",    path: null,                      available: false },
    { name: "韓国",                 region: "東アジア",    path: null,                      available: false },
    { name: "ウズベキスタン",        region: "中央アジア",  path: "uzbekistan/index.html",   available: true },
    { name: "モルディブ",            region: "南アジア",    path: null,                      available: false },
    { name: "南アフリカ共和国",      region: "アフリカ",    path: "south_africa/index.html", available: true },
    { name: "イタリア",              region: "ヨーロッパ",  path: null,                      available: false },
    { name: "フランス",              region: "ヨーロッパ",  path: null,                      available: false },
    { name: "オーストラリア",        region: "オセアニア",  path: null,                      available: false },
    { name: "ハワイ（アメリカ）",    region: "北アメリカ",  path: null,                      available: false },
  ];

  const isCountryPage = location.pathname.split("/").filter(Boolean).length >= 2;
  const base = isCountryPage ? "../" : "";
  const indexPage = `${base}index.html`;

  // エリア別にグループ化
  const regions = {};
  COUNTRIES.forEach(c => {
    if (!regions[c.region]) regions[c.region] = [];
    regions[c.region].push(c);
  });

  // PC: エリア×国名グリッド
  const colsHtml = Object.entries(regions).map(([region, countries]) => {
    const items = countries.map(c =>
      c.available && c.path
        ? `<li><a href="${base}${c.path}">・${c.name}</a></li>`
        : `<li class="cl-unavailable">・${c.name}</li>`
    ).join("");
    return `<div class="cl-col"><p class="cl-region">${region}</p><ul>${items}</ul></div>`;
  }).join("");

  // スマホ: エリア名リンクのみ（国一覧ページへ飛ぶ）
  const mobileHtml = Object.keys(regions).map(region =>
    `<a href="${indexPage}?region=${encodeURIComponent(region)}" class="cl-region-link">・${region}</a>`
  ).join("");

  const html = `
    <div class="country-links">
      <div class="country-links-inner">
        <div class="cl-grid">${colsHtml}</div>
        <div class="cl-mobile">${mobileHtml}</div>
      </div>
    </div>`;
  document.currentScript.insertAdjacentHTML("beforebegin", html);
})();
