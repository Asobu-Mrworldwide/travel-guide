/* 診断：ゴールデンレトリバー(FCSR)のコマ送りアニメ（types.html / result.html で共用）
   素材/タイプイラスト/FCSR_anim/0〜8.webp を順に差し替えて再生し、終わったら0コマ目(静止画)に戻る。
   - dogWatch(img)  : 画面に入るたびに再生（タイプ一覧用）
   - dogOnOpen(img) : 開いた直後に再生＋タップでも再生（診断結果用）
   動きを減らす設定(prefers-reduced-motion)のときは、一覧のスクロール再生だけ止める（結果ページを開いた直後とタップは再生する）。 */
(function(){
  const BASE = '素材/タイプイラスト/FCSR_anim/', N = 9, STEP = 110, LOOPS = 2;
  const frames = [];
  let loaded = false;
  function preload(){
    if (loaded) return; loaded = true;
    for (let i = 0; i < N; i++) { const im = new Image(); im.src = BASE + i + '.webp'; frames.push(im); }
  }
  const reduce = () => window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  function play(img){
    if (!img || img._dogPlaying) return;
    preload();
    img._dogPlaying = true;
    const rest = BASE + '0.webp';
    let k = 0; const total = N * LOOPS;
    (function tick(){
      if (k >= total) { img.src = rest; img._dogPlaying = false; return; }
      img.src = BASE + (k % N) + '.webp';
      k++; setTimeout(tick, STEP);
    })();
  }

  function isDog(img){ return /FCSR_/.test(img.getAttribute('src') || ''); }

  window.dogWatch = function(root){
    const imgs = [...(root || document).querySelectorAll('img')].filter(isDog);
    if (!imgs.length) return;
    preload();
    if (!('IntersectionObserver' in window)) return;
    const io = new IntersectionObserver(es => es.forEach(e => {
      if (e.isIntersecting) { if (!reduce()) play(e.target); }
    }), { threshold: .6 });
    imgs.forEach(i => io.observe(i));
  };

  window.dogOnOpen = function(img){
    if (!img || !isDog(img)) return;
    preload();
    img.style.cursor = 'pointer';
    img.style.webkitTapHighlightColor = 'transparent';
    if (!img._dogBound) { img._dogBound = true; img.addEventListener('click', () => play(img)); }
    const go = () => setTimeout(() => play(img), 300); // 開いた直後の1回は、動きを減らす設定でも再生する
    img.complete && img.naturalWidth ? go() : img.addEventListener('load', go, { once: true });
  };
})();
