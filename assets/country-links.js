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
  const isDiagPage = parentDir === "diagnosis";
  const isCommonPage = parentDir === "common";
  const base = (isCountryPage || isDiagPage || isCommonPage) ? "../" : "";

  const currentCountry = currentSlug ? available.find(c => c.path.split("/")[0] === currentSlug) : null;

  // 近隣の国もチェック: 同エリアの公開済み国を優先し、5ヶ国に満たなければ他エリアで穴埋め
  let thirdColLabel = "エリアで探す";
  let thirdColHtml = "";
  if (currentCountry) {
    thirdColLabel = "近隣の国もチェック";
    const sameRegion = available.filter(c => c.region === currentCountry.region && c !== currentCountry);
    const nearby = sameRegion.slice(0, 5);
    if (nearby.length < 5) {
      const others = available.filter(c => c.region !== currentCountry.region);
      for (const c of others) {
        if (nearby.length >= 5) break;
        nearby.push(c);
      }
    }
    thirdColHtml = nearby.map(c => `<a href="${base}${c.path}">${c.name}</a>`).join("");
  } else {
    const regionOrder = [];
    COUNTRIES.forEach(c => { if (!regionOrder.includes(c.region)) regionOrder.push(c.region); });
    thirdColHtml = '<div class="sf-area-grid">' + regionOrder.map(region =>
      `<a href="${base}index.html?region=${encodeURIComponent(region)}">${region}</a>`
    ).join("") + '</div>';
  }

  const html = `
    <footer class="site-footer-main">
      <div class="sf-grid">
        <div class="sf-brand">
          <div class="sf-brand-logo">
            <img src="${base}assets/site-logo.png" width="26" height="26" alt="World Mappy">
            <span><span class="gold">World</span> Mappy</span>
          </div>
          <p>情報が溢れるこの時代に、本当に必要な旅行情報だけをまとめました。気候・飛行時間・予算の三つから、次の旅先を。</p>
          <div class="sf-social">
            <a href="#" target="_blank" rel="noopener" aria-label="X"><svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg></a>
            <a href="#" target="_blank" rel="noopener" aria-label="Instagram"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/></svg></a>
          </div>
        </div>
        <div class="sf-col">
          <span class="sf-label">GUIDE</span>
          <a href="${base}common/checklist.html">持ち物チェックリスト</a>
          <!-- 診断ページ未公開のため無効化: <a href="${base}diagnosis/index.html">旅行タイプ診断</a> -->
          <!-- 診断ページ未公開のため無効化: <a href="${base}diagnosis/types.html">旅行タイプ一覧</a> -->
          <a href="${base}common/faq.html">よくある質問</a>
        </div>
        <div class="sf-col${currentCountry ? '' : ' sf-col-area'}">
          <span class="sf-label">${thirdColLabel}</span>
          ${thirdColHtml}
          ${currentCountry ? `<a href="${base}index.html" class="sf-gold-link">すべての旅先を見る →</a>` : ''}
        </div>
        <div class="sf-col sf-share">
          <span class="sf-label">SHARE</span>
          <p>このページが役に立ったら、旅の相談相手に送ってあげてください。</p>
          <button type="button" id="cl-share-copy" class="sf-copy-btn"><span>このページのリンクをコピー</span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 14a3.5 3.5 0 0 0 5 0l4-4a3.5 3.5 0 0 0-5-5l-1 1"/><path d="M14 10a3.5 3.5 0 0 0-5 0l-4 4a3.5 3.5 0 0 0 5 5l1-1"/></svg></button>
          <div class="sf-share-links">
            <a href="#" target="_blank" rel="noopener">X で共有</a>
            <a href="#" target="_blank" rel="noopener">LINE で送る</a>
          </div>
        </div>
      </div>
      <div class="sf-bottom">
        <div class="sf-legal">
          <a href="${base}common/privacy.html">プライバシーポリシー</a>
          <a href="${base}common/disclaimer.html">免責事項</a>
          <a href="${base}common/about.html">運営者情報</a>
          <a href="${base}common/contact.html">お問い合わせ</a>
        </div>
        <span class="sf-copyright">© 2026 World Mappy　<span class="gold">楽しい旅を！</span></span>
      </div>
    </footer>`;
  document.currentScript.insertAdjacentHTML("beforebegin", html);

  // ハンバーガードロワーの「近隣の国」欄にも同じリストを流用する
  const hbNearby = document.getElementById("hb-nearby");
  if (hbNearby) hbNearby.innerHTML = thirdColHtml + `<a href="${base}index.html" class="active">すべての旅先を見る →</a>`;

  const shareCopyBtn = document.getElementById("cl-share-copy");
  if (shareCopyBtn) shareCopyBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(location.href).then(() => {
      const original = shareCopyBtn.innerHTML;
      // ボタン内のテキストが短くなって幅が縮み、レイアウトが崩れるのを防ぐため、
      // 切り替え前の幅を固定してから文言を変える
      shareCopyBtn.style.width = shareCopyBtn.offsetWidth + "px";
      shareCopyBtn.innerHTML = "<span>コピーしました！</span>";
      setTimeout(() => {
        shareCopyBtn.innerHTML = original;
        shareCopyBtn.style.width = "";
      }, 2000);
    });
  });
})();
