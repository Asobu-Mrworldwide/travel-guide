/**
 * affiliates.js — 描画ロジック
 *
 * データは affiliates-data.js で管理。
 * このファイルは基本的に編集不要。
 *
 * 【案A 現在】テキストリンクはPCホバーでツールチップ表示
 * 【案B 将来】affiliates-data.js の url を内部紹介ページに変えるだけで移行完了
 */

/* =====================================================
   CSS
   ===================================================== */
const AFFILIATES_CSS = `

/* ── テキストリンク ツールチップ ── */
.aff-wrap{position:relative;display:block;width:100%}
.aff-wrap.inline{display:inline;width:auto}
.aff-tooltip{
  position:absolute;
  bottom:calc(100% + 10px);
  right:0;left:auto;
  width:240px;
  background:#fff;
  border:1px solid #dde2e8;
  border-radius:12px;
  padding:14px;
  box-shadow:0 6px 20px rgba(0,0,0,0.13);
  z-index:1000;
  opacity:0;pointer-events:none;
  transition:opacity 0.15s ease;
  text-align:left;white-space:normal;line-height:1.5;
}
.aff-tooltip::after{
  content:'';position:absolute;
  top:100%;right:20px;left:auto;
  border:7px solid transparent;
  border-top-color:#fff;
  filter:drop-shadow(0 2px 0 #dde2e8);
}
.aff-tooltip.visible{opacity:1;pointer-events:auto}
.aff-tooltip-name{font-size:0.78em;font-weight:900;color:#1a3a5c;margin-bottom:5px}
.aff-tooltip-desc{font-size:0.73em;color:#555;line-height:1.65;margin-bottom:10px}
.aff-tooltip-btn{
  display:block;text-align:center;
  background:#006847;color:#fff;
  font-size:0.73em;font-weight:700;
  padding:6px 12px;border-radius:20px;
  text-decoration:none;transition:background 0.15s;
}
.aff-tooltip-btn:hover{background:#004d33}
@media(hover:none){.aff-tooltip{display:none}}

/* ── 説明カード ── */
.aff-card{
  background:#fff;
  border-radius:8px;
  border:1px solid #ccc;
  box-shadow:none;
  overflow:hidden;
  margin-top:12px;
}
.aff-card-header{
  display:flex;align-items:center;gap:12px;
  padding:14px 16px 12px;
  border-bottom:1px solid #f0f0f0;
}
.aff-card-icon{font-size:1.6em;line-height:1}
.aff-card-name{font-size:0.95em;font-weight:900;color:#111}
.aff-card-tagline{font-size:0.75em;color:#666;margin-top:2px}
.aff-card-body{padding:12px 16px 14px}
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
}
.aff-card-btn:hover{opacity:0.85}
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
    const isInline  = !!el.dataset.affiliateClass;

    const a = document.createElement('a');
    a.href = aff.url; a.target = '_blank'; a.rel = 'noopener';
    a.className = linkClass;
    a.textContent = aff.label;

    const tooltip = document.createElement('div');
    tooltip.className = 'aff-tooltip';
    tooltip.innerHTML = `
      <div class="aff-tooltip-name">${aff.name}</div>
      <div class="aff-tooltip-desc">${aff.desc || ''}</div>
      <a href="${aff.url}" target="_blank" rel="noopener" class="aff-tooltip-btn">${aff.btn || '詳しく見る →'}</a>`;

    const wrap = document.createElement('div');
    wrap.className = 'aff-wrap' + (isInline ? ' inline' : '');
    wrap.appendChild(a);
    wrap.appendChild(tooltip);

    let hideTimer;
    const show = () => { clearTimeout(hideTimer); tooltip.classList.add('visible'); };
    const hide = () => { hideTimer = setTimeout(() => tooltip.classList.remove('visible'), 120); };
    wrap.addEventListener('mouseenter', show);
    wrap.addEventListener('mouseleave', hide);
    tooltip.addEventListener('mouseenter', show);
    tooltip.addEventListener('mouseleave', hide);

    el.replaceWith(wrap);
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
        <div style="display:flex;align-items:center;gap:10px">
          <span class="aff-card-icon">${c.icon}</span>
          <div>
            <div class="aff-card-name">${c.name}</div>
            <div class="aff-card-tagline">${c.tagline}</div>
          </div>
        </div>
        ${c.logo ? `<div style="flex-shrink:0;line-height:1">${c.logo}</div>` : ''}
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
        <div style="display:flex;align-items:center;gap:10px">
          <span class="aff-card-icon">${c.icon}</span>
          <div>
            <div class="aff-card-name">${c.name}</div>
            <div class="aff-card-tagline">${c.tagline}</div>
          </div>
        </div>
        ${c.logo ? `<div style="flex-shrink:0;line-height:1">${c.logo}</div>` : ''}
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
}

document.addEventListener('DOMContentLoaded', initAffiliates);
