/**
 * affiliates.js — アフィリエイトリンク一元管理
 *
 * 【案A 現在】PCホバー→ツールチップ表示、モバイル→直接リンク
 * 【案B 将来】url を内部紹介ページ（services/xxx.html）に変えるだけで移行完了
 *
 * HTML側の使い方：
 *   <span data-affiliate="skyscanner"></span>
 *   クラスを上書きしたい場合：
 *   <span data-affiliate="wise" data-affiliate-class="wise-inline"></span>
 */

const AFFILIATES = {

  // ── 航空券 ──────────────────────────────
  skyscanner: {
    name:  'Skyscanner',
    label: 'Skyscannerで比較 →',
    desc:  '200以上の航空会社を一括比較・最安値検索。日付や区間を変えながら最安値を探せる。',
    url:   'https://www.skyscanner.jp/'
  },

  // ── ホテル ──────────────────────────────
  booking: {
    name:  'Booking.com',
    label: 'Booking.comで検索 →',
    desc:  '世界最大級のホテル予約サイト。無料キャンセル対応プランが多く直前変更にも対応しやすい。',
    url:   'https://www.booking.com/'
  },

  // ── 交通 ────────────────────────────────
  grab: {
    name:  'Grab',
    label: 'Grabアプリを見る →',
    desc:  '東南アジアNo.1配車アプリ。乗車前に料金が確定するため、ぼったくりの心配がない。',
    url:   'https://www.grab.com/'
  },

  // ── 観光（国別に追加していく） ────────────
  tripadvisor_malaysia: {
    name:  'TripAdvisor',
    label: 'TripAdvisorで探す →',
    desc:  '旅行者の口コミ・評判をチェックしてから観光スポットやレストランを選べる。',
    url:   'https://www.tripadvisor.jp/Tourism-g293951-Malaysia-Vacations.html'
  },

  // ── SIM ─────────────────────────────────
  trifa: {
    name:  'trifa',
    label: 'trifaで見る →',
    desc:  '海外用SIMを手軽に購入できるサービス。出発前にオンラインで申し込んで現地ですぐ使える。',
    url:   'https://torifaa.com/'
  },

  // ── 両替・送金 ────────────────────────────
  wise: {
    name:  'Wise',
    label: 'Wiseの詳細を見る →',
    desc:  '実勢レートに近いレートで両替・送金できるサービス。現地ATMからの現金引き出しにも対応。',
    url:   'https://wise.com/jp/'
  },

};

/* =====================================================
   ツールチップCSS（PCのみ表示・モバイルは非表示）
   ===================================================== */
const TOOLTIP_CSS = `
.aff-wrap{position:relative;display:block;width:100%}
.aff-wrap.inline{display:inline;width:auto}
.aff-tooltip{
  position:absolute;
  bottom:calc(100% + 10px);
  right:0;
  left:auto;
  transform:none;
  width:240px;
  background:#fff;
  border:1px solid #dde2e8;
  border-radius:12px;
  padding:14px;
  box-shadow:0 6px 20px rgba(0,0,0,0.13);
  z-index:1000;
  opacity:0;
  pointer-events:none;
  transition:opacity 0.15s ease;
  text-align:left;
  white-space:normal;
  line-height:1.5;
}
.aff-tooltip::before{
  content:'';
  position:absolute;
  top:100%;left:0;right:0;
  height:14px;
}
.aff-tooltip::after{
  content:'';
  position:absolute;
  top:100%;right:20px;
  left:auto;
  transform:none;
  border:7px solid transparent;
  border-top-color:#fff;
  filter:drop-shadow(0 2px 0 #dde2e8);
}
.aff-wrap:hover .aff-tooltip{opacity:1;pointer-events:auto}
.aff-tooltip-name{font-size:0.78em;font-weight:900;color:#1a3a5c;margin-bottom:5px}
.aff-tooltip-desc{font-size:0.73em;color:#555;line-height:1.65;margin-bottom:10px}
.aff-tooltip-btn{
  display:block;text-align:center;
  background:#006847;color:#fff;
  font-size:0.73em;font-weight:700;
  padding:6px 12px;border-radius:20px;
  text-decoration:none;
  transition:background 0.15s;
}
.aff-tooltip-btn:hover{background:#004d33}
@media(hover:none){.aff-tooltip{display:none}}
`;

/* =====================================================
   初期化
   ===================================================== */
function initAffiliates() {
  // CSSを動的に挿入
  const style = document.createElement('style');
  style.textContent = TOOLTIP_CSS;
  document.head.appendChild(style);

  document.querySelectorAll('[data-affiliate]').forEach(el => {
    const key = el.dataset.affiliate;
    const aff = AFFILIATES[key];
    if (!aff) { console.warn('affiliates.js: unknown key →', key); return; }

    const linkClass   = el.dataset.affiliateClass || 'budget-link';
    const isInline    = el.dataset.affiliateClass === 'wise-inline';
    const descSnippet = aff.desc
      ? `<span style="font-weight:400;opacity:0.75">${aff.desc.split('。')[0]}。</span>　`
      : '';

    // ── リンク本体 ──
    const a = document.createElement('a');
    a.href    = aff.url;
    a.target  = '_blank';
    a.rel     = 'noopener';
    a.className = linkClass;
    a.innerHTML = descSnippet + aff.label;

    // ── ツールチップ（PCのみ有効） ──
    const tooltip = document.createElement('div');
    tooltip.className = 'aff-tooltip';
    tooltip.innerHTML = `
      <div class="aff-tooltip-name">${aff.name}</div>
      <div class="aff-tooltip-desc">${aff.desc || ''}</div>
      <a href="${aff.url}" target="_blank" rel="noopener" class="aff-tooltip-btn">公式サイトを見る →</a>
    `;

    // ── ラッパーに包む ──
    const wrap = document.createElement('div');
    wrap.className = 'aff-wrap' + (isInline ? ' inline' : '');
    wrap.appendChild(a);
    wrap.appendChild(tooltip);

    el.replaceWith(wrap);
  });
}

document.addEventListener('DOMContentLoaded', initAffiliates);
