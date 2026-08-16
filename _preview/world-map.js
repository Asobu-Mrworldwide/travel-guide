/* <world-map> — World Mappy destination atlas (preview build, real country data).
   Real geometry: Natural Earth via world-atlas TopoJSON + d3-geo.
   Attributes: theme ("dark"|"light"), projection ("naturalEarth"|"mercator"),
               accent, active (id), selected (id), visible (comma-separated ids)
   Events: pointenter, pointselect (detail = destination id)
   Zoom: mouse wheel / pinch to zoom, drag to pan (d3-zoom, scaleExtent 1–8).
         Selecting a point (via `selected` attribute) smoothly auto-focuses it.
         Double-click resets to the default view. */
(function () {
  const LIBS = [
    { src: 'https://unpkg.com/d3@7.9.0/dist/d3.min.js', integrity: 'sha384-CjloA8y00+1SDAUkjs099PVfnY2KmDC2BZnws9kh8D/lX1s46w6EPhpXdqMfjK6i', check: () => window.d3 },
    { src: 'https://unpkg.com/topojson-client@3.1.0/dist/topojson-client.min.js', integrity: 'sha384-Ukv1p/xTma6P4/2bY5KzWBw+ydSpXmhCMtyciIQVDJ1RmOxtCYNMF1uXT9T63H67', check: () => window.topojson },
  ];
  const load = (l) => new Promise((res, rej) => {
    if (l.check()) return res();
    let s = document.querySelector('script[data-wm="' + l.src + '"]');
    if (s) return s.addEventListener('load', res), s.addEventListener('error', rej);
    s = document.createElement('script');
    s.src = l.src; s.integrity = l.integrity; s.crossOrigin = 'anonymous';
    s.dataset.wm = l.src; s.onload = res; s.onerror = rej;
    document.head.appendChild(s);
  });
  let worldP = null;
  const world = () => (worldP = worldP || load(LIBS[0]).then(() => load(LIBS[1]))
    .then(() => fetch('https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json'))
    .then((r) => r.json())
    .then((t) => window.topojson.feature(t, t.objects.countries)));

  // World Mappy 掲載国（実データ、代表都市の緯度経度）
  const PTS = [
    { id: 'malaysia', name: 'マレーシア', lat: 3.14, lon: 101.69 },
    { id: 'thailand', name: 'タイ', lat: 13.75, lon: 100.5 },
    { id: 'uzbekistan', name: 'ウズベキスタン', lat: 41.3, lon: 69.24 },
    { id: 'south_africa', name: '南アフリカ', lat: -33.92, lon: 18.42 },
    { id: 'taiwan', name: '台湾', lat: 25.03, lon: 121.56 },
    { id: 'singapore', name: 'シンガポール', lat: 1.35, lon: 103.82 },
    { id: 'srilanka', name: 'スリランカ', lat: 6.93, lon: 79.85 },
    { id: 'korea', name: '韓国', lat: 37.57, lon: 126.98 },
    { id: 'laos', name: 'ラオス', lat: 17.97, lon: 102.6 },
    { id: 'vietnam', name: 'ベトナム', lat: 21.03, lon: 105.85 },
    { id: 'philippines', name: 'フィリピン', lat: 14.6, lon: 120.98 },
    { id: 'spain', name: 'スペイン', lat: 40.42, lon: -3.7 },
    { id: 'italy', name: 'イタリア', lat: 41.9, lon: 12.5 },
    { id: 'north_korea', name: '北朝鮮', lat: 39.02, lon: 125.75 },
    { id: 'germany', name: 'ドイツ', lat: 52.52, lon: 13.4 },
    { id: 'newzealand', name: 'ニュージーランド', lat: -41.29, lon: 174.78 },
    { id: 'canada', name: 'カナダ', lat: 45.42, lon: -75.7 },
    { id: 'turkey', name: 'トルコ', lat: 41.01, lon: 28.98 },
    { id: 'mexico', name: 'メキシコ', lat: 19.43, lon: -99.13 },
    { id: 'brazil', name: 'ブラジル', lat: -22.91, lon: -43.17 },
    { id: 'indonesia', name: 'インドネシア', lat: -8.65, lon: 115.22 },
    { id: 'france', name: 'フランス', lat: 48.85, lon: 2.35 },
    { id: 'maldives', name: 'モルディブ', lat: 4.17, lon: 73.51 },
    { id: 'australia', name: 'オーストラリア', lat: -33.87, lon: 151.21 },
    { id: 'hawaii', name: 'ハワイ', lat: 21.31, lon: -157.86 },
    { id: 'cambodia', name: 'カンボジア', lat: 13.36, lon: 103.86 },
    { id: 'myanmar', name: 'ミャンマー', lat: 16.87, lon: 96.2 },
    { id: 'switzerland', name: 'スイス', lat: 47.37, lon: 8.55 },
    { id: 'czech', name: 'チェコ', lat: 50.08, lon: 14.44 },
  ];

  const THEMES = {
    dark: { sphere: 'rgba(255,255,255,0.022)', grid: 'rgba(255,255,255,0.07)', land: 'rgba(232,228,218,0.10)', coast: 'rgba(232,228,218,0.30)', label: 'rgba(232,228,218,0.85)', accent: '#C8A96A', ring: '#C8A96A' },
    light: { sphere: '#f4fbf8', grid: 'rgba(29,144,116,0.13)', land: '#E5EDE9', coast: '#c8d0e0', label: '#3a3a3a', accent: '#1d9074', ring: '#ffc200' },
  };

  const W = 960, H = 470, FOCUS_K = 3.2;

  class WorldMap extends HTMLElement {
    static get observedAttributes() { return ['theme', 'projection', 'accent', 'active', 'selected', 'visible']; }
    connectedCallback() {
      if (this._init) return;
      this._init = true;
      this._k = 1;
      this.attachShadow({ mode: 'open' });
      this.shadowRoot.innerHTML = '<style>:host{display:block}svg{width:100%;height:auto;display:block;overflow:visible;touch-action:none}' +
        '.pt{cursor:pointer;transition:opacity .35s ease,fill .3s ease}' +
        '.rg{pointer-events:none;transition:opacity .35s ease}' +
        '.lb{font:500 11px/1 "Zen Kaku Gothic New",sans-serif;pointer-events:none;transition:opacity .35s ease,fill .3s ease}' +
        '.landpath,.gridpath,.spherepath{vector-effect:non-scaling-stroke}' +
        '@keyframes pulse{0%{opacity:.5}70%{opacity:0}100%{opacity:0}}</style><div part="wrap"></div>';
      this.render();
    }
    attributeChangedCallback(n) {
      if (!this._init) return;
      if (n === 'theme' || n === 'projection') { this.render(); return; }
      this.paint();
      if (n === 'selected') this.focusSelected();
    }
    get t() { return THEMES[this.getAttribute('theme') === 'light' ? 'light' : 'dark']; }
    get accent() { return this.getAttribute('accent') || this.t.accent; }
    async render() {
      const land = await world();
      const d3 = window.d3, t = this.t;
      const proj = (this.getAttribute('projection') === 'mercator'
        ? d3.geoMercator().center([40, 20]).scale(150).translate([W / 2, H / 2])
        : d3.geoNaturalEarth1().fitExtent([[8, 8], [W - 8, H - 8]], { type: 'Sphere' }));
      const path = d3.geoPath(proj);
      const svg = d3.create('svg').attr('viewBox', '0 0 ' + W + ' ' + H);
      const zoomLayer = svg.append('g').attr('class', 'zoom-layer');
      zoomLayer.append('path').attr('class', 'spherepath').attr('d', path({ type: 'Sphere' })).attr('fill', t.sphere);
      zoomLayer.append('path').attr('class', 'gridpath').attr('d', path(d3.geoGraticule10())).attr('fill', 'none').attr('stroke', t.grid).attr('stroke-width', 0.5);
      zoomLayer.append('g').selectAll('path').data(land.features).join('path')
        .attr('class', 'landpath').attr('d', path).attr('fill', t.land).attr('stroke', t.coast).attr('stroke-width', 0.55);
      this._nodes = PTS.map((p) => {
        const xy = proj([p.lon, p.lat]);
        const gg = zoomLayer.append('g').attr('transform', 'translate(' + xy[0] + ',' + xy[1] + ')');
        const halo = gg.append('circle').attr('fill', this.accent).attr('opacity', 0)
          .style('animation', 'pulse 2.8s ease-out infinite').style('animation-delay', (Math.random() * 2.4).toFixed(2) + 's');
        const ring = gg.append('circle').attr('class', 'rg').attr('fill', 'none')
          .attr('stroke', t.ring).attr('stroke-width', 1.5).attr('opacity', 0);
        const dot = gg.append('circle').attr('class', 'pt').attr('fill', this.accent)
          .on('mouseenter', () => { this.setAttribute('active', p.id); this.dispatchEvent(new CustomEvent('pointenter', { detail: p.id, bubbles: true, composed: true })); })
          .on('mouseleave', () => this.removeAttribute('active'))
          .on('click', (event) => { event.stopPropagation(); this.dispatchEvent(new CustomEvent('pointselect', { detail: p.id, bubbles: true, composed: true })); });
        const lb = gg.append('text').attr('class', 'lb').attr('fill', t.label).attr('opacity', 0.45).text(p.name);
        return { p, x: xy[0], y: xy[1], dot, lb, halo, ring };
      });

      // ズーム（ホイール／ピンチ／ドラッグ）。ダブルクリックはズームせずリセットに割り当て。
      this._zoom = d3.zoom().scaleExtent([1, 8]).on('zoom', (event) => {
        zoomLayer.attr('transform', event.transform);
        this._k = event.transform.k;
        this.rescale();
      });
      svg.call(this._zoom).on('dblclick.zoom', null)
        .on('dblclick', () => svg.transition().duration(500).call(this._zoom.transform, d3.zoomIdentity));

      const wrap = this.shadowRoot.querySelector('div');
      wrap.innerHTML = '';
      wrap.appendChild(svg.node());
      this._svg = svg;
      this.paint();
    }
    // ズーム倍率が上がっても点・ラベルの見た目の大きさを一定に保つ（ストロークは vector-effect で対応済み）
    rescale() {
      if (!this._nodes) return;
      const k = this._k || 1;
      this._nodes.forEach(({ dot, lb, halo, ring }) => {
        const baseDot = +dot.attr('data-r') || 3;
        const baseHalo = +halo.attr('data-r') || 4;
        const baseRing = +ring.attr('data-r') || 6;
        dot.attr('r', baseDot / k);
        halo.attr('r', baseHalo / k);
        ring.attr('r', baseRing / k);
        lb.attr('x', 10 / k).attr('y', 3.5 / k).style('font-size', (11 / k) + 'px');
      });
    }
    paint() {
      if (!this._nodes) return;
      const t = this.t, a = this.getAttribute('active'), sel = this.getAttribute('selected');
      const vis = this.getAttribute('visible');
      const set = vis == null || vis === '' ? null : vis.split(',');
      this._nodes.forEach(({ p, dot, lb, halo, ring }) => {
        const shown = !set || set.indexOf(p.id) >= 0;
        const on = a === p.id, isSel = sel === p.id;
        if (!shown) {
          dot.attr('data-r', 2).attr('opacity', 0.13).attr('fill', t.label);
          halo.attr('data-r', 0).attr('opacity', 0).style('animation', 'none');
          ring.attr('data-r', 6).attr('opacity', 0);
          lb.attr('opacity', 0);
          this.rescale();
          return;
        }
        dot.attr('fill', isSel ? t.ring : this.accent)
          .attr('data-r', isSel ? 6 : on ? 5.5 : 3)
          .attr('opacity', a && !on && !isSel ? 0.45 : 1);
        halo.attr('data-r', 4).attr('opacity', a && !on ? 0 : null);
        ring.attr('data-r', isSel ? 12 : 6).attr('opacity', isSel ? 1 : 0);
        lb.attr('opacity', on || isSel ? 1 : a || sel ? 0.28 : 0.45)
          .attr('font-weight', on || isSel ? 700 : 500)
          .attr('fill', isSel ? t.ring : on ? this.accent : t.label);
      });
      this.rescale();
    }
    // selected 属性が変わったら、その地点を画面中央へスムーズにズーム＆パン
    focusSelected() {
      const d3 = window.d3;
      if (!d3 || !this._svg || !this._zoom || !this._nodes) return;
      const sel = this.getAttribute('selected');
      const node = this._nodes.find((n) => n.p.id === sel);
      if (!node) return;
      const tx = W / 2 - node.x * FOCUS_K;
      const ty = H / 2 - node.y * FOCUS_K;
      this._svg.transition().duration(700).ease(d3.easeCubicOut)
        .call(this._zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(FOCUS_K));
    }
  }
  if (!customElements.get('world-map')) customElements.define('world-map', WorldMap);
})();
