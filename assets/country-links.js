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
    thirdColHtml = '<div class="wm-area-grid">' + regionOrder.map(region =>
      `<a href="${base}index.html?region=${encodeURIComponent(region)}">${region}</a>`
    ).join("") + '</div>';
  }
  const thirdColClass = "ja";

  const html = `
    <footer class="wm-footer">
      <img class="bg-globe" src="${base}assets/top/footer-globe-plane.png" alt="" aria-hidden="true">
      <div class="wm-footer-inner">
        <div class="wm-col brand-col">
          <span class="wm-brand">
            <img class="mark" src="${base}assets/site-logo.png" alt="" aria-hidden="true">
            <span class="name"><b>World</b> Mappy</span>
          </span>
          <p class="wm-tagline">情報が溢れるこの時代に、本当に必要な旅行情報だけをまとめました。フィルター機能で行きたい国を絞れます。</p>
          <div class="wm-sns-block">
            <span class="wm-sns-cap">公式SNSで最新情報をチェック</span>
            <div class="wm-sns">
              <a href="#" target="_blank" rel="noopener" aria-label="X"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231 5.45-6.231Zm-1.161 17.52h1.833L7.084 4.126H5.117L17.083 19.77Z"/></svg></a>
              <a href="#" target="_blank" rel="noopener" aria-label="Instagram"><svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5.2"/><circle cx="12" cy="12" r="4.1"/><circle cx="17.2" cy="6.8" r="1.15" fill="currentColor" stroke="none"/></svg></a>
            </div>
          </div>
        </div>
        <div class="wm-col wm-col-hide-sp">
          <span class="wm-col-h en">GUIDE</span>
          <a href="${base}common/checklist.html">持ち物チェックリスト</a>
          <!-- 診断ページ未公開のため無効化: <a href="${base}diagnosis/index.html">旅行タイプ診断</a> -->
          <!-- 診断ページ未公開のため無効化: <a href="${base}diagnosis/types.html">旅行タイプ一覧</a> -->
          <a href="${base}common/faq.html">よくある質問</a>
          <a href="${base}common/contact.html">お問い合わせ</a>
        </div>
        <div class="wm-col">
          <span class="wm-col-h ${thirdColClass}">${thirdColLabel}</span>
          ${thirdColHtml}
          ${currentCountry ? `<a href="${base}index.html" class="more">すべての旅先を見る →</a>` : ''}
        </div>
        <div class="wm-col wm-share-col">
          <span class="wm-col-h en wm-col-hide-sp">SHARE</span>
          <p class="wm-col-hide-sp">このページが役に立ったら、一緒に行く人に送ってあげてください。</p>
          <div class="wm-pills">
            <button type="button" id="cl-share-copy" class="wm-pill">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M10 13.5a4 4 0 0 0 5.66 0l3-3a4 4 0 1 0-5.66-5.66l-1.3 1.3"/><path d="M14 10.5a4 4 0 0 0-5.66 0l-3 3a4 4 0 1 0 5.66 5.66l1.3-1.3"/></svg>
              <span id="cl-share-copy-label">リンクをコピー</span>
            </button>
            <button type="button" id="cl-share-btn" class="wm-pill">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="18" cy="5" r="2.6"/><circle cx="6" cy="12" r="2.6"/><circle cx="18" cy="19" r="2.6"/><path d="M8.3 10.8 15.7 6.3M8.3 13.2l7.4 4.5"/></svg>
              共有する
            </button>
          </div>
        </div>
      </div>
      <div class="wm-legal">
        <div class="links">
          <a href="${base}common/privacy.html">プライバシーポリシー</a><span class="sep" aria-hidden="true"></span>
          <a href="${base}common/disclaimer.html">免責事項</a><span class="sep" aria-hidden="true"></span>
          <a href="${base}common/about.html">運営者情報</a><span class="sep" aria-hidden="true"></span>
          <a href="${base}common/contact.html">お問い合わせ</a>
        </div>
        <span>© 2026 World Mappy</span>
      </div>
    </footer>`;
  document.currentScript.insertAdjacentHTML("beforebegin", html);

  // ハンバーガードロワーの「近隣の国」欄にも同じリストを流用する
  const hbNearby = document.getElementById("hb-nearby");
  if (hbNearby) hbNearby.innerHTML = thirdColHtml + `<a href="${base}index.html" class="active">すべての旅先を見る →</a>`;

  const shareBtn = document.getElementById("cl-share-btn");
  if (shareBtn) {
    shareBtn.addEventListener("click", () => {
      if (navigator.share) {
        navigator.share({ title: document.title, url: location.href }).catch(() => {});
      } else {
        navigator.clipboard.writeText(location.href);
      }
    });
  }

  // 共通ページ・診断ページのヘッダーを、国ページと同じ「スクロール量に連動して隠れる／現れる」挙動に統一する。
  // 国ページ(#site-top-bar)とトップページ(index.html)はそれぞれ独自スクリプトで制御しているため対象外。
  if (isCommonPage || isDiagPage) {
    const hdr = document.querySelector("header.wm-header, header.site-header");
    if (hdr && !document.getElementById("site-top-bar")) {
      hdr.style.position = "sticky";
      hdr.style.top = "0";
      hdr.style.zIndex = "1000";
      hdr.style.transition = "transform .3s ease";
      let hdrH = hdr.offsetHeight;
      let hideOffset = 0;
      let lastY = window.scrollY;
      let ticking = false;
      const applyHdr = () => { hdr.style.transform = "translateY(-" + hideOffset + "px)"; ticking = false; };
      window.addEventListener("scroll", () => {
        const y = window.scrollY;
        hideOffset = Math.max(0, Math.min(hdrH, hideOffset + (y - lastY)));
        lastY = y;
        if (y <= 0) hideOffset = 0;
        if (!ticking) { ticking = true; requestAnimationFrame(applyHdr); }
      }, { passive: true });
      window.addEventListener("resize", () => { hdrH = hdr.offsetHeight; hideOffset = Math.min(hideOffset, hdrH); applyHdr(); });
    }
  }

  const shareCopyBtn = document.getElementById("cl-share-copy");
  if (shareCopyBtn) shareCopyBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(location.href).then(() => {
      const label = document.getElementById("cl-share-copy-label");
      if (!label) return;
      label.textContent = "コピーしました";
      setTimeout(() => { label.textContent = "リンクをコピー"; }, 1800);
    });
  });
})();
