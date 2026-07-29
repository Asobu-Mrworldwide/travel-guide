(() => {
  const COUNTRIES = [
    { name: "マレーシア",               region: "東南アジア", path: "malaysia/index.html",     available: true },
    { name: "タイ",                     region: "東南アジア", path: "thailand/index.html",     available: true },
    { name: "ウズベキスタン",            region: "中央アジア", path: "uzbekistan/index.html",   available: true },
    { name: "南アフリカ共和国",          region: "アフリカ",   path: "south_africa/index.html", available: true },
    { name: "台湾",                     region: "東アジア",   path: "taiwan/index.html",       available: true },
    { name: "シンガポール",              region: "東南アジア", path: "singapore/index.html",    available: true },
    { name: "スリランカ民主社会主義共和国", region: "南アジア",   path: "srilanka/index.html",     available: true },
    { name: "韓国",                     region: "東アジア",   path: "korea/index.html",        available: true },
    { name: "ラオス人民民主共和国",       region: "東南アジア", path: "laos/index.html",         available: true },
    { name: "ベトナム",                  region: "東南アジア", path: "vietnam/index.html",      available: true },
    { name: "フィリピン",                region: "東南アジア", path: "philippines/index.html",  available: true },
    { name: "スペイン",                  region: "ヨーロッパ", path: "spain/index.html",        available: true },
    { name: "イタリア",                  region: "ヨーロッパ", path: "italy/index.html",        available: true },
    { name: "北朝鮮",                    region: "東アジア",   path: "north_korea/index.html",  available: true },
    { name: "ドイツ",                    region: "ヨーロッパ", path: "germany/index.html",      available: true },
    { name: "ニュージーランド",           region: "オセアニア", path: "newzealand/index.html",   available: true },
    { name: "カナダ",                    region: "北アメリカ", path: "canada/index.html",       available: true },
    { name: "バリ島（インドネシア）",      region: "東南アジア", path: null,                      available: false },
    { name: "フランス",                  region: "ヨーロッパ", path: null,                      available: false },
    { name: "モルディブ",                region: "南アジア",   path: null,                      available: false },
    { name: "オーストラリア",            region: "オセアニア", path: null,                      available: false },
    { name: "ハワイ（アメリカ）",         region: "北アメリカ", path: null,                      available: false },
    { name: "カンボジア",                region: "東南アジア", path: null,                      available: false },
    { name: "ミャンマー",                region: "東南アジア", path: null,                      available: false },
    { name: "スイス",                    region: "ヨーロッパ", path: null,                      available: false },
    { name: "チェコ",                    region: "ヨーロッパ", path: null,                      available: false },
  ];

  const available = COUNTRIES.filter(c => c.available && c.path);
  const knownSlugs = available.map(c => c.path.split("/")[0]);

  // 現在のページの直上フォルダ名が既知の国スラッグと一致するかで判定する
  // （サイトのホスティング階層の深さやfile://での直接閲覧に影響されないようにするため）
  const pathParts = location.pathname.split("/").filter(Boolean);
  const parentDir = pathParts.length >= 2 ? pathParts[pathParts.length - 2] : null;
  const currentSlug = parentDir && knownSlugs.includes(parentDir) ? parentDir : null;
  const isCountryPage = currentSlug !== null;
  const base = isCountryPage ? "../" : "";

  const currentCountry = currentSlug ? available.find(c => c.path.split("/")[0] === currentSlug) : null;

  // 周辺国: 同エリアの公開済み国を優先し、5ヶ国に満たなければ他エリアで穴埋め
  let nearbyHtml = "";
  if (currentCountry) {
    const sameRegion = available.filter(c => c.region === currentCountry.region && c !== currentCountry);
    const nearby = sameRegion.slice(0, 5);
    if (nearby.length < 5) {
      const others = available.filter(c => c.region !== currentCountry.region);
      for (const c of others) {
        if (nearby.length >= 5) break;
        nearby.push(c);
      }
    }
    nearbyHtml = nearby.map(c => `<a href="${base}${c.path}" class="cl-chip">${c.name}</a>`).join("");
  }

  // エリアで探す: 全エリアへのボタン（index.html の ?region= フィルターに接続）
  const regionOrder = [];
  COUNTRIES.forEach(c => { if (!regionOrder.includes(c.region)) regionOrder.push(c.region); });
  const areaHtml = regionOrder.map(region =>
    `<a href="${base}index.html?region=${encodeURIComponent(region)}" class="cl-chip">${region}</a>`
  ).join("");

  const html = `
    <div class="country-links">
      <div class="country-links-inner">
        ${nearbyHtml ? `
        <div class="cl-section">
          <p class="cl-section-title">周辺国から探す</p>
          <div class="cl-chip-row">${nearbyHtml}</div>
        </div>` : ""}
        <div class="cl-section">
          <p class="cl-section-title">エリアで探す</p>
          <div class="cl-chip-row">${areaHtml}</div>
        </div>
        <div class="cl-social">
          <p class="cl-social-title">公式アカウントをフォロー</p>
          <div class="cl-social-icons">
            <a href="#" target="_blank" rel="noopener" class="cl-social-icon" aria-label="X"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg></a>
            <a href="#" target="_blank" rel="noopener" class="cl-social-icon" aria-label="Instagram"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/></svg></a>
          </div>
        </div>
        <div class="cl-share">
          <p class="cl-share-title">この記事をシェアする</p>
          <div class="cl-share-buttons">
            <a href="#" id="cl-share-x" target="_blank" rel="noopener" class="cl-share-btn cl-share-btn-x"><svg width="15" height="15" viewBox="0 0 24 24" fill="#fff"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>シェア</a>
            <button type="button" id="cl-share-copy" class="cl-share-btn cl-share-btn-copy"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 14a3.5 3.5 0 0 0 5 0l4-4a3.5 3.5 0 0 0-5-5l-1 1"/><path d="M14 10a3.5 3.5 0 0 0-5 0l-4 4a3.5 3.5 0 0 0 5 5l1-1"/></svg>リンクをコピー</button>
          </div>
        </div>
      </div>
    </div>`;
  document.currentScript.insertAdjacentHTML("beforebegin", html);

  const shareXBtn = document.getElementById("cl-share-x");
  if (shareXBtn) shareXBtn.href = "https://twitter.com/intent/tweet?text=" + encodeURIComponent(document.title) + "&url=" + encodeURIComponent(location.href);
  const shareCopyBtn = document.getElementById("cl-share-copy");
  if (shareCopyBtn) shareCopyBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(location.href).then(() => {
      const original = shareCopyBtn.innerHTML;
      shareCopyBtn.innerHTML = "コピーしました！";
      setTimeout(() => { shareCopyBtn.innerHTML = original; }, 2000);
    });
  });
})();
