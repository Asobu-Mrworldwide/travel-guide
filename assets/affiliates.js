/**
 * affiliates.js — 描画ロジック
 *
 * データは affiliates-data.js で管理。
 * このファイルは基本的に編集不要。
 *
 * テキストリンクはホバーツールチップなしのシンプルな直接リンク。
 * 【将来】affiliates-data.js の url を内部紹介ページに変えるだけで移行完了
 */

/* =====================================================
   CSS
   ===================================================== */
const AFFILIATES_CSS = `

/* ── 説明カード ── */
.aff-card{
  background:#fff;
  border-radius:6px;
  border:1px solid #ccc;
  box-shadow:none;
  overflow:hidden;
  margin-top:12px;
  display:flex;
  flex-direction:column;
}
.aff-card-header{
  display:flex;align-items:center;gap:12px;
  padding:14px 16px 12px;
  border-bottom:1px solid #f0f0f0;
}
.aff-card-icon{font-size:1.6em;line-height:1}
.aff-card-name{font-size:0.95em;font-weight:900;color:#111}
.aff-card-tagline{font-size:0.75em;color:#666;margin-top:2px}
.aff-card-body{padding:12px 16px 14px;display:flex;flex-direction:column;flex:1}
.aff-card-points{
  list-style:none;margin:0 0 10px;padding:0;
  display:flex;flex-direction:column;gap:6px;
}
.aff-card-points li{
  font-size:0.8em;color:#333;line-height:1.5;
  padding-left:18px;position:relative;
}
.aff-card-points li::before{
  content:'✓';
  position:absolute;left:0;
  font-weight:700;
}
.aff-card-note{
  font-size:0.72em;color:#999;
  margin-bottom:12px;line-height:1.5;
}
.aff-card-btn{
  display:block;text-align:center;
  color:#fff;font-size:0.8em;font-weight:700;
  padding:9px 16px;border-radius:20px;
  text-decoration:none;transition:opacity 0.15s;
  margin-top:auto;
}
.aff-card-btn:hover{opacity:0.85}

/* ── 予約ボタンボックス ── */
.booking-box{
  margin:20px 0;
  padding:16px;
  background-color:#f8f9fa;
  border-radius:8px;
  border:1px solid #e9ecef;
}
.booking-title{
  margin-top:0;
  margin-bottom:12px;
  font-size:14px;
  font-weight:bold;
  color:#495057;
  text-align:center;
}
.booking-buttons{
  display:flex;
  flex-direction:column;
  gap:14px;
}
.booking-btn-group{
  display:flex;
  flex-direction:column;
  gap:6px;
  width:100%;
}
.booking-btn-desc{
  margin:0;
  font-size:12px;
  line-height:1.5;
  color:#6c757d;
  text-align:center;
}
.btn-booking{
  display:flex;
  align-items:center;
  justify-content:center;
  height:44px;
  border-radius:6px;
  border:none;
  text-decoration:none;
  font-size:14px;
  font-family:inherit;
  font-weight:600;
  color:#ffffff;
  cursor:pointer;
  transition:opacity 0.2s ease, transform 0.1s ease;
  width:100%;
}
.btn-booking:hover, .btn-booking:active{
  opacity:0.85;
  transform:translateY(-1px);
}
.flight-choice-wrap{position:relative}
.flight-choice{
  display:none;
  flex-direction:column;
  gap:6px;
  position:absolute;
  top:calc(100% + 6px);
  left:0;
  right:0;
  background:#fff;
  border:1px solid #e9ecef;
  border-radius:6px;
  padding:8px;
  box-shadow:0 4px 16px rgba(0,0,0,0.15);
  z-index:10;
}
.flight-choice.open{display:flex}
.flight-choice a{
  display:block;
  padding:9px;
  text-align:center;
  background:#eef5fd;
  border-radius:5px;
  color:#0770e3;
  font-weight:600;
  font-size:13px;
  text-decoration:none;
}
.flight-choice a:hover{background:#dcecfb}
.btn-agoda{background-color:#202636;border-bottom:3px solid #111520}
.btn-bookingcom{background-color:#003580;border-bottom:3px solid #002254}
.btn-expedia{background-color:#1f4985;border-bottom:3px solid #122f59}
.btn-skyscanner{background-color:#0770e3;border-bottom:3px solid #054f9e}
.btn-googleflights{background-color:#4285f4;border-bottom:3px solid #2f5fb8}
.btn-trifa{background-color:#3d5afe;border-bottom:3px solid #2a3ecc}
.btn-airalo{background-color:#6c4ff6;border-bottom:3px solid #4c34c2}
.btn-holafly{background-color:#ff5a36;border-bottom:3px solid #cc3e1f}
@media(min-width:576px){
  .booking-buttons{flex-direction:row}
  .booking-btn-group{flex:1}
  .booking-title{text-align:left}
}

/* ── 固定バナー広告（タブごとに商材を出し分け・閉じたら同セッション中は再表示しない） ── */
.sticky-ad-banner{
  position:fixed;left:0;right:0;bottom:0;z-index:900;
  background:rgba(255,255,255,0.92);border-top:1px solid #ddd;
  box-shadow:0 -2px 10px rgba(0,0,0,0.08);
  padding:9px 12px;
  display:flex;align-items:center;gap:10px;
  max-width:520px;margin:0 auto;
}
.sab-link{display:flex;align-items:center;gap:10px;flex:1;min-width:0;text-decoration:none;color:inherit}
.sab-icon{
  flex-shrink:0;width:34px;height:34px;border-radius:0;overflow:hidden;
  display:flex;align-items:center;justify-content:center;font-size:1.15em;
}
.sab-body{flex:1;min-width:0}
.sab-name{font-size:0.76em;font-weight:700;color:#111;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sab-tagline{font-size:0.68em;color:#777;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sab-btn{flex-shrink:0;color:#fff;font-size:0.72em;font-weight:700;padding:7px 13px;border-radius:16px;text-decoration:none;white-space:nowrap}
.sab-close{flex-shrink:0;background:none;border:none;color:#aaa;font-size:1em;padding:2px 4px;cursor:pointer;line-height:1;z-index:1}
.sab-close:hover{color:#666}
.sab-logo-img{width:34px;height:34px;object-fit:cover;flex-shrink:0;border-radius:0;display:none}
.sab-logo-img-mobile{display:block}
.sab-logo-img-desktop{display:none}
@media(min-width:1020px){
  .sticky-ad-banner{
    left:auto;right:24px;bottom:24px;top:auto;
    max-width:340px;margin:0;
    flex-wrap:wrap;position:fixed;
    border:1px solid #ddd;border-radius:0;
    box-shadow:0 6px 28px rgba(0,0,0,0.14);
    padding:20px 22px 18px;
  }
  .sab-link{width:100%;flex-wrap:wrap}
  .sab-icon{order:1;width:48px;height:48px;font-size:1.6em;border-radius:0}
  .sab-body{order:2;flex:1 1 auto}
  .sab-name{font-size:1.05em}
  .sab-tagline{font-size:0.88em}
  .sab-close{position:absolute;top:10px;right:10px;background:#f2f2f2;border-radius:50%;width:18px;height:18px;display:flex;align-items:center;justify-content:center;font-size:0.62em;padding:0}
  .sab-btn{order:4;flex:1 0 100%;text-align:center;margin-top:14px;font-size:0.78em;padding:8px 14px;border-radius:18px}

  .sab-link-logo{flex-direction:column;align-items:stretch}
  .sab-logo-img{width:100%;height:auto;order:0}
  .sab-logo-img-mobile{display:none}
  .sab-logo-img-desktop{display:block}
  .sticky-ad-banner-logo{padding:0}
  .sticky-ad-banner-logo .sab-name{display:none}
  .sticky-ad-banner-logo .sab-body{order:2;flex:0 0 auto;padding:0 20px}
  .sticky-ad-banner-logo .sab-tagline{white-space:normal;text-align:center;font-size:0.85em;margin-top:8px}
  .sticky-ad-banner-logo .sab-btn{order:3;margin:8px 20px 12px}
}
.sticky-ad-banner-img{
  padding:0;position:relative;max-width:none;width:fit-content;
  border:none;box-shadow:0 -2px 10px rgba(0,0,0,0.15);border-radius:0;
  overflow:visible;
}
.sticky-ad-banner-img a{display:block;line-height:0}
.sticky-ad-banner-img .sab-close{
  position:absolute;top:-9px;right:-9px;background:#fff;border:1px solid #ddd;
  border-radius:50%;width:20px;height:20px;display:flex;align-items:center;
  justify-content:center;font-size:0.7em;box-shadow:0 1px 4px rgba(0,0,0,0.15);
}
@media(min-width:1020px){
  .sticky-ad-banner-img{
    top:auto;bottom:24px;right:24px;left:auto;
    box-shadow:0 4px 20px rgba(0,0,0,0.12);border-radius:0;
  }
}
`;

/* =====================================================
   初期化
   ===================================================== */
function initAffiliates() {
  // CSS注入
  const style = document.createElement('style');
  style.textContent = AFFILIATES_CSS;
  document.head.appendChild(style);

  // ── テキストリンク ──
  document.querySelectorAll('[data-affiliate]').forEach(el => {
    const key = el.dataset.affiliate;
    const aff = AFFILIATES[key];
    if (!aff) { console.warn('affiliates.js: unknown key →', key); return; }

    const linkClass = el.dataset.affiliateClass || 'budget-link';

    const a = document.createElement('a');
    a.href = aff.url; a.target = '_blank'; a.rel = 'noopener';
    a.className = linkClass;
    a.textContent = el.dataset.affiliateLabel || aff.label;

    el.replaceWith(a);
  });

  // ── 説明カード ──
  document.querySelectorAll('[data-affiliate-card]').forEach(el => {
    const key = el.dataset.affiliateCard;
    const c = AFFILIATE_CARDS[key];
    if (!c) { console.warn('affiliates.js: unknown card key →', key); return; }

    const card = document.createElement('div');
    card.className = 'aff-card';
    card.innerHTML = `
      <div class="aff-card-header" style="display:flex;align-items:center;justify-content:space-between">
        ${c.logo ? `
        <div style="line-height:1">${c.logo}</div>` : c.name_large ? `
        <div>
          <div style="display:flex;align-items:center;gap:10px">
            <span class="aff-card-icon">${c.icon}</span>
            <div class="aff-card-name" style="font-size:1.5em;line-height:1">${c.name}</div>
          </div>
          <div class="aff-card-tagline" style="margin-top:4px">${c.tagline}</div>
        </div>` : `
        <div style="display:flex;align-items:center;gap:10px">
          <span class="aff-card-icon">${c.icon}</span>
          <div>
            <div class="aff-card-name">${c.name}</div>
            <div class="aff-card-tagline">${c.tagline}</div>
          </div>
        </div>`}
      </div>
      <div class="aff-card-body">
        ${c.desc ? `<p style="font-size:0.82em;color:var(--sub);line-height:1.7;margin:0 0 12px">${c.desc}</p>` : ''}
        <ul class="aff-card-points">
          ${c.points.map(p => `<li>${p}</li>`).join('')}
        </ul>
        ${c.note ? `<div class="aff-card-note">${c.note}</div>` : ''}
        <a href="${c.url}" target="_blank" rel="noopener"
           class="aff-card-btn" style="background:${c.color}">
          ${c.btn}
        </a>
      </div>`;

    el.replaceWith(card);
  });

  // ── 統合カード用：外枠なし・中身だけ描画 ──
  // 使い方: <div data-affiliate-card-inner="grab"></div>
  // 親要素の .card の中に埋め込んで使う（区切り線は親側で用意）
  document.querySelectorAll('[data-affiliate-card-inner]').forEach(el => {
    const key = el.dataset.affiliateCardInner;
    const c = AFFILIATE_CARDS[key];
    if (!c) { console.warn('affiliates.js: unknown card key →', key); return; }

    const inner = document.createElement('div');
    inner.className = 'aff-card-inner';
    inner.innerHTML = `
      <div class="aff-card-header" style="padding:0 0 10px;border-bottom:none;display:flex;align-items:center;justify-content:space-between">
        ${c.logo ? `
        <div style="line-height:1">${c.logo}</div>` : c.name_large ? `
        <div>
          <div style="display:flex;align-items:center;gap:10px">
            <span class="aff-card-icon">${c.icon}</span>
            <div class="aff-card-name" style="font-size:1.5em;line-height:1">${c.name}</div>
          </div>
          <div class="aff-card-tagline" style="margin-top:4px">${c.tagline}</div>
        </div>` : `
        <div style="display:flex;align-items:center;gap:10px">
          <span class="aff-card-icon">${c.icon}</span>
          <div>
            <div class="aff-card-name">${c.name}</div>
            <div class="aff-card-tagline">${c.tagline}</div>
          </div>
        </div>`}
      </div>
      <ul class="aff-card-points">
        ${c.points.map(p => `<li>${p}</li>`).join('')}
      </ul>
      ${c.note ? `<div class="aff-card-note">${c.note}</div>` : ''}
      <a href="${c.url}" target="_blank" rel="noopener"
         class="aff-card-btn" style="background:${c.color}">
        ${c.btn}
      </a>`;

    el.replaceWith(inner);
  });

  // ── 予約ボタンボックス ──
  document.querySelectorAll('[data-affiliate-box]').forEach(el => {
    const key = el.dataset.affiliateBox;
    const box = BOOKING_BOXES[key];
    if (!box) { console.warn('affiliates.js: unknown booking box key →', key); return; }

    const dest = el.dataset.dest;
    const wrap = document.createElement('div');
    wrap.className = 'booking-box';

    if (key === 'flights' && dest) {
      const skyscannerBtn = box.buttons.find(b => b.className === 'btn-skyscanner');
      wrap.innerHTML = `
        <p class="booking-title">${box.title}</p>
        <div class="booking-buttons">
          <div class="booking-btn-group">
            <a href="${skyscannerBtn.url}" target="_blank" rel="noopener" class="btn-booking btn-skyscanner">Skyscannerで見る →</a>
          </div>
          <div class="booking-btn-group flight-choice-wrap">
            <button type="button" class="btn-booking btn-googleflights" onclick="this.nextElementSibling.classList.toggle('open')">Google Flightsで見る →</button>
            <div class="flight-choice">
              <a href="https://www.google.com/travel/flights?q=Flights%20from%20NRT%20to%20${dest.toUpperCase()}" target="_blank" rel="noopener">東京発 →</a>
              <a href="https://www.google.com/travel/flights?q=Flights%20from%20KIX%20to%20${dest.toUpperCase()}" target="_blank" rel="noopener">大阪発 →</a>
            </div>
          </div>
        </div>`;
      el.replaceWith(wrap);
      return;
    }

    wrap.innerHTML = `
      <p class="booking-title">${box.title}</p>
      <div class="booking-buttons">
        ${box.buttons.map(b => `
        <div class="booking-btn-group">
          ${b.desc ? `<p class="booking-btn-desc">${b.desc}</p>` : ''}
          <a href="${b.url}" target="_blank" rel="noopener" class="btn-booking ${b.className}">${b.label}</a>
        </div>`).join('')}
      </div>`;

    el.replaceWith(wrap);
  });

  // ── 固定バナー広告（タブごとに商材を出し分け） ──
  document.querySelectorAll('[data-sticky-banner]').forEach(el => {
    const key = el.dataset.stickyBanner;
    const c = AFFILIATE_CARDS[key];
    if (!c) { el.remove(); return; }

    const storageKey = 'sticky-ad-closed:' + location.pathname;
    if (sessionStorage.getItem(storageKey)) { el.remove(); return; }

    const banner = document.createElement('div');
    banner.className = 'sticky-ad-banner';

    if (c.rawAdWidget) {
      const rw = c.rawAdWidget;
      banner.classList.add('sticky-ad-banner-img');

      const slot = document.createElement('div');
      slot.id = rw.divId;
      banner.appendChild(slot);

      const s1 = document.createElement('script');
      s1.src = rw.scriptSrc;
      s1.onload = () => {
        const s2 = document.createElement('script');
        s2.textContent = `brandsafe_js_async(${rw.params});`;
        document.body.appendChild(s2);
      };
      document.body.appendChild(s1);

      if (rw.pixel) {
        const pixel = document.createElement('img');
        pixel.src = rw.pixel; pixel.width = 1; pixel.height = 1; pixel.alt = '';
        pixel.style.position = 'absolute'; pixel.style.left = '-9999px';
        banner.appendChild(pixel);
      }

      const closeBtn = document.createElement('button');
      closeBtn.type = 'button';
      closeBtn.className = 'sab-close';
      closeBtn.setAttribute('aria-label', '閉じる');
      closeBtn.textContent = '✕';
      banner.appendChild(closeBtn);
    } else if (c.bannerImg) {
      const bi = c.bannerImg;
      banner.classList.add('sticky-ad-banner-img');
      banner.innerHTML = `
        <a href="${bi.url}" target="_blank" rel="noopener">
          <img src="${bi.imgSrc}" width="${bi.w}" height="${bi.h}" alt="${c.name}">
        </a>
        ${bi.pixel ? `<img src="${bi.pixel}" width="1" height="1" alt="" style="position:absolute;left:-9999px">` : ''}
        <button type="button" class="sab-close" aria-label="閉じる">✕</button>`;
    } else if (c.logoImg) {
      banner.classList.add('sticky-ad-banner-logo');
      banner.innerHTML = `
        <a href="${c.url}" target="_blank" rel="noopener" class="sab-link sab-link-logo">
          ${c.mobileIconImg ? `<img src="${c.mobileIconImg}" alt="${c.name}" class="sab-logo-img sab-logo-img-mobile">` : ''}
          <img src="${c.logoImg}" alt="${c.name}" class="sab-logo-img sab-logo-img-desktop">
          <div class="sab-body">
            <div class="sab-name">${c.name}</div>
            <div class="sab-tagline">${c.tagline}</div>
          </div>
          <span class="sab-btn" style="background:${c.color}">見る →</span>
        </a>
        <button type="button" class="sab-close" aria-label="閉じる">✕</button>`;
    } else {
      const isImgIcon = c.icon.trim().startsWith('<img');
      const iconBg = isImgIcon ? 'transparent' : `${c.color}1a`;
      banner.innerHTML = `
        <a href="${c.url}" target="_blank" rel="noopener" class="sab-link">
          <span class="sab-icon" style="background:${iconBg}">${c.icon}</span>
          <div class="sab-body">
            <div class="sab-name">${c.name}</div>
            <div class="sab-tagline">${c.tagline}</div>
          </div>
          <span class="sab-btn" style="background:${c.color}">見る →</span>
        </a>
        <button type="button" class="sab-close" aria-label="閉じる">✕</button>`;
    }

    banner.querySelector('.sab-close').addEventListener('click', () => {
      sessionStorage.setItem(storageKey, '1');
      banner.remove();
    });

    el.replaceWith(banner);
  });
}

document.addEventListener('DOMContentLoaded', initAffiliates);

document.addEventListener('click', e => {
  document.querySelectorAll('.flight-choice.open').forEach(el => {
    if (!el.parentElement.contains(e.target)) el.classList.remove('open');
  });
});
