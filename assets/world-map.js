/* <world-map> — MapLibre GL による本物の地図（パン／ズーム／横方向は無限ループ）。
   タイル: MapLibre demotiles（APIキー不要）。World Mappy 配色に再着色して使う。
   属性: selected(id) / active(id) / visible(カンマ区切りid。未指定=おすすめのみ) / focus-area(エリア名)
   イベント: pointselect (detail = id) */
(function () {
  const CSS = 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css';
  const JS = 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js';
  // 外部デモタイルは本番でCORS拒否されることがあるため、自前のGeoJSONで描画する
  const GEOJSON = new URL('top/world-countries.geojson', document.currentScript ? document.currentScript.src : location.href).href;
  const STYLE = {
    version: 8,
    sources: { countries: { type: 'geojson', data: GEOJSON } },
    layers: [
      { id: 'background', type: 'background', paint: { 'background-color': '#D6E5DE' } },
      { id: 'countries-fill', type: 'fill', source: 'countries', paint: { 'fill-color': '#FDFCF6', 'fill-outline-color': '#D9E2D3' } },
    ],
  };
  const GREEN = '#168B78', DARK = '#15735b', YELLOW = '#ffc200';

  let libP = null;
  const lib = () => (libP = libP || new Promise((res, rej) => {
    if (!document.querySelector('link[data-wm-mlcss]')) {
      const l = document.createElement('link');
      l.rel = 'stylesheet'; l.href = CSS; l.dataset.wmMlcss = '1';
      document.head.appendChild(l);
    }
    if (window.maplibregl) return res(window.maplibregl);
    let s = document.querySelector('script[data-wm-ml]');
    if (!s) {
      s = document.createElement('script');
      s.src = JS; s.dataset.wmMl = '1';
      document.head.appendChild(s);
    }
    s.addEventListener('load', () => res(window.maplibregl));
    s.addEventListener('error', rej);
  }));

  const REVEAL_ZOOM = 2.6; // これ以上に拡大すると、おすすめ以外のピンも現れる

  class WorldMap extends HTMLElement {
    static get observedAttributes() { return ['selected', 'active', 'visible', 'focus-area', 'label-zoom']; }
    connectedCallback() {
      if (this._init) return;
      this._init = true;
      this.style.display = 'block';
      this.style.position = 'relative';
      this._host = document.createElement('div');
      this._host.style.cssText = 'position:relative;width:100%;height:100%;background:transparent;';
      this.appendChild(this._host);
      this._hint = document.createElement('div');
      this._hint.style.cssText = 'position:absolute;left:12px;bottom:12px;z-index:2;pointer-events:none;font:400 11px/1.5 "Zen Kaku Gothic New",sans-serif;color:#15735b;background:rgba(255,255,255,.86);border:1px solid #dde8e2;border-radius:999px;padding:5px 11px;transition:opacity .3s ease;';
      this._hint.textContent = '';
      this._hint.style.display = 'none';
      this.appendChild(this._hint);
      this.boot();
      if (window.ResizeObserver) {
        this._ro = new ResizeObserver(() => { if (this._map) this._map.resize(); });
        this._ro.observe(this);
      }
    }
    disconnectedCallback() { if (this._ro) this._ro.disconnect(); }
    attributeChangedCallback(n) {
      if (!this._map) return;
      if (n === 'focus-area') this.focus();
      else {
        if (n === 'selected') this.zoomToSelected();
        this.paint();
      }
    }
    get points() { const d = window.WM_DESTINATIONS; return d && d.length ? d : []; }

    async boot() {
      const gl = await lib();
      const map = new gl.Map({
        container: this._host,
        style: STYLE,
        center: (this.getAttribute('center') || '40,20').split(',').map(Number),
        zoom: parseFloat(this.getAttribute('zoom')) || 1.15,
        minZoom: 0.6,
        maxZoom: 7,
        renderWorldCopies: true,
        attributionControl: { compact: true },
        dragRotate: false,
        pitchWithRotate: false,
      });
      map.touchZoomRotate.disableRotation();
      map.addControl(new gl.NavigationControl({ showCompass: false }), 'top-right');
      this._map = map;
      const ready = () => {
        if (this._ready) return;
        this._ready = true;
        this._map.resize();
        this.restyle();
        this.makeMarkers(gl);
        this.paint();
        if (this.getAttribute('selected')) this.zoomToSelected();
        else if (this.getAttribute('focus-area')) this.focus();
        this.dispatchEvent(new CustomEvent('mapready', { bubbles: true, composed: true }));
      };
      map.on('load', ready);
      map.on('load', () => this.initHL());
      map.once('idle', ready);
      map.on('data', () => { if (map.areTilesLoaded && map.areTilesLoaded()) ready(); });
      // 初回 restyle がスタイル未ロードで空振りするケースがあるため、idle のたびに再適用（冪等）
      map.on('idle', () => this.restyle());
      map.on('styledata', () => this.restyle());
      map.on('zoom', () => {
        this.paint();
        this._hint.style.opacity = map.getZoom() > 2 ? '0' : '1';
      });
    }

    restyle() {
      const map = this._map;
      const WATER = '#D6E5DE', LAND = '#FDFCF6', LINE = '#D9E2D3', GRID = '#ECE7D8';
      const set = (id, prop, val) => {
        try { map.setPaintProperty(id, prop, val); }
        catch (e) { console.warn('[world-map] restyle skipped', id, prop, e.message); }
      };
      map.getStyle().layers.forEach((l) => {
        const id = l.id, water = /water|ocean|sea|lake|bathymetry/i.test(id);
        if (id.indexOf('hl-') === 0) return;  // 強調用レイヤーは再着色しない
        if (l.type === 'background') set(id, 'background-color', WATER);
        else if (l.type === 'fill') {
          set(id, 'fill-color', water ? WATER : LAND);
          set(id, 'fill-opacity', 1);
          set(id, 'fill-outline-color', LINE);
        } else if (l.type === 'line') {
          const grid = /geoline|graticule|grid|lat|lon/i.test(id);
          set(id, 'line-color', grid ? GRID : LINE);
          set(id, 'line-width', 0.7);
        } else if (l.type === 'symbol') {
          set(id, 'text-color', '#7d8f88');
          set(id, 'text-halo-color', '#ffffff');
          set(id, 'text-halo-width', 1.2);
        }
      });
      // demotiles の陸レイヤーを id 直指定で確実に上書き
      set('countries-fill', 'fill-color', LAND);
    }

    makeMarkers(gl) {
      this._markers = this.points.map((p) => {
        const el = document.createElement('div');
        // クリック判定が小さくてシビアだったので、透明な余白でタップ範囲を広げる
        // （見た目の位置は下の Marker offset で相殺）
        el.style.cssText = 'cursor:pointer;padding:12px 10px;';
        const inner = document.createElement('span');
        inner.style.cssText = 'display:flex;align-items:center;gap:6px;transform-origin:left center;transition:transform .3s cubic-bezier(.2,.7,.2,1),opacity .3s ease;';
        const dot = document.createElement('span');
        dot.style.cssText = 'width:12px;height:12px;border-radius:999px;flex:none;background:' + GREEN + ';box-shadow:0 0 0 3px rgba(255,255,255,.95),0 1px 4px rgba(0,0,0,.22);transition:all .3s cubic-bezier(.2,.7,.2,1);';
        const lb = document.createElement('span');
        lb.textContent = p.country || p.name || p.city;
        lb.style.cssText = 'font:500 11.5px/1 "Zen Kaku Gothic New",sans-serif;color:#15735b;background:rgba(255,255,255,.92);border:1px solid #dde8e2;border-radius:3px;padding:3px 6px;white-space:nowrap;transition:all .3s ease;';
        inner.appendChild(dot); inner.appendChild(lb);
        el.appendChild(inner);
        // 広げた透明余白どうしが重なる密集地域で、ポインタが乗っている方を最前面にして取りこぼしを防ぐ
        el.addEventListener('pointerenter', () => { el.style.zIndex = 9; this.setAttribute('active', p.id); });
        el.addEventListener('pointerleave', () => { el.style.zIndex = ''; this.removeAttribute('active'); });
        el.addEventListener('click', (e) => {
          e.stopPropagation();
          this.dispatchEvent(new CustomEvent('pointselect', { detail: p.id, bubbles: true, composed: true }));
        });
        // el に padding:12px 10px を足したぶん、ドット中心が右へずれるので offset で戻す
        // （padding-left 10 + ドット半径 6 = 16 を左へ／anchor:left は縦中心なので y は 0）
        const marker = new gl.Marker({ element: el, anchor: 'left', offset: [-16, 0] })
          .setLngLat([p.lon, p.lat]).addTo(this._map);
        return { p, el, inner, dot, lb, marker };
      });
    }

    // 絞り込み中の国を地図上で色付けする（国ポリゴンは destinations の緯度経度から自動で特定）。
    // 香港・マカオ・ハワイのように国のポリゴンが別の国全体になってしまう地域は、destinations-data.js で noHL: true を付ける。
    initHL() {
      if (this._hlInit) return;
      this._hlInit = true;
      const map = this._map, none = ['==', ['get', 'wm'], '__none__'];
      map.addSource('hl', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
      map.addLayer({ id: 'hl-fill', type: 'fill', source: 'hl', filter: none, paint: { 'fill-color': ['coalesce', ['get', 'c'], GREEN], 'fill-opacity': 0.6 } });
      map.addLayer({ id: 'hl-sel', type: 'fill', source: 'hl', filter: none, paint: { 'fill-color': YELLOW, 'fill-opacity': 0.55 } });
      fetch(GEOJSON).then((r) => r.json()).then((g) => {
        map.getSource('hl').setData({ type: 'FeatureCollection', features: this.matchCountries(g) });
        this.paintHL();
      }).catch((e) => console.warn('[world-map] highlight skipped', e.message));
    }

    matchCountries(g) {
      const feats = g.features;
      const inRing = (x, y, r) => {
        let c = false;
        for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
          const xi = r[i][0], yi = r[i][1], xj = r[j][0], yj = r[j][1];
          if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c;
        }
        return c;
      };
      const inPoly = (x, y, p) => inRing(x, y, p[0]) && !p.slice(1).some((h) => inRing(x, y, h));
      const polysOf = (f) => (f.geometry.type === 'MultiPolygon' ? f.geometry.coordinates : [f.geometry.coordinates]);
      const near = (x, y, f) => {
        let m = 1e9;
        polysOf(f).forEach((p) => p[0].forEach((pt) => { const d = Math.hypot(pt[0] - x, pt[1] - y); if (d < m) m = d; }));
        return m;
      };
      const out = [];
      // エリア（destinations の area）ごとの色。選択中の国は hl-sel の黄色が上に重なる
      const AREA_COLORS = {
        '東南アジア': '#F2994A', '東アジア': '#EE7B7B', '南アジア': '#A66BBE', '中央アジア': '#7C8CA3',
        '中東': '#B07A52', 'ヨーロッパ': '#3C6FB5', 'アフリカ': '#7A9E3C', '北アメリカ': '#4DA6A0',
        'オセアニア': '#5BB5E0', '南米': '#58B368',
      };
      this.points.forEach((p) => {
        if (p.noHL || p.lat == null || p.lon == null) return;
        let hit = feats.filter((f) => polysOf(f).some((poly) => inPoly(p.lon, p.lat, poly)))[0];
        if (!hit) {  // ピンが海岸の外にずれている場合は、4度以内の最寄りのポリゴンを使う
          let bd = 4;
          feats.forEach((f) => { const d = near(p.lon, p.lat, f); if (d < bd) { bd = d; hit = f; } });
        }
        if (hit) {
          // ピンを含む（無ければ最寄りの）ポリゴンの範囲を記録。ズーム量の自動決定に使う（飛び地・遠い島は無視）
          const polys = polysOf(hit);
          const main = polys.filter((poly) => inPoly(p.lon, p.lat, poly))[0]
            || polys.slice().sort((x, y) => near(p.lon, p.lat, { geometry: { type: 'Polygon', coordinates: x } }) - near(p.lon, p.lat, { geometry: { type: 'Polygon', coordinates: y } }))[0];
          let w = 180, e = -180, so = 90, n = -90;
          main[0].forEach((pt) => { w = Math.min(w, pt[0]); e = Math.max(e, pt[0]); so = Math.min(so, pt[1]); n = Math.max(n, pt[1]); });
          (this._bbox = this._bbox || {})[p.id] = [[w, so], [e, n]];
        }
        if (hit) out.push({ type: 'Feature', properties: { wm: p.id, c: AREA_COLORS[p.area] || GREEN }, geometry: hit.geometry });
      });
      return out;
    }

    paintHL() {
      const map = this._map;
      if (!map || !map.getLayer || !map.getLayer('hl-fill')) return;
      const vis = this.getAttribute('visible');
      const ids = vis != null && vis !== '__all__' && vis !== '' ? vis.split(',') : [];
      const f = ids.length ? ['in', ['get', 'wm'], ['literal', ids]] : ['==', ['get', 'wm'], '__none__'];
      map.setFilter('hl-fill', f);
      const sel = this.getAttribute('selected');
      map.setFilter('hl-sel', sel ? ['==', ['get', 'wm'], sel] : ['==', ['get', 'wm'], '__none__']);
    }

    paint() {
      this.paintHL();
      if (!this._markers) return;
      const vis = this.getAttribute('visible');
      const filtered = vis != null && vis !== '__all__';
      const set = filtered ? (vis === '' ? [] : vis.split(',')) : null;
      const z = this._map.getZoom();
      const act = this.getAttribute('active'), sel = this.getAttribute('selected');
      this._markers.forEach(({ p, el, inner, dot, lb }) => {
        const allowed = set ? set.indexOf(p.id) >= 0 : (p.rec || z >= REVEAL_ZOOM);
        const on = act === p.id, isSel = sel === p.id;
        const lzA = parseFloat(this.getAttribute('label-zoom'));
        const gated = !isNaN(lzA) && z < lzA && !isSel;
        const shown = allowed && !gated;
        inner.style.opacity = shown ? '1' : '0';
        inner.style.visibility = shown ? 'visible' : 'hidden';
        el.style.pointerEvents = shown ? 'auto' : 'none';
        inner.style.transform = on || isSel ? 'scale(1.12)' : 'scale(1)';
        el.classList.toggle('is-sel', isSel);
        el.style.zIndex = on ? 6 : isSel ? 5 : 1;
        dot.style.background = isSel ? YELLOW : GREEN;
        dot.style.width = dot.style.height = isSel ? '16px' : on ? '14px' : '12px';
        const lzAttr = parseFloat(this.getAttribute('label-zoom'));
        const hasLz = !isNaN(lzAttr);
        const lz = hasLz ? lzAttr : 2.2;
        const showLb = allowed && (on || isSel || z >= lz || (!hasLz && p.rec));
        lb.style.opacity = showLb ? '1' : '0';
        lb.style.visibility = showLb ? 'visible' : 'hidden';
        lb.style.borderColor = isSel ? YELLOW : '#dde8e2';
        lb.style.color = isSel ? '#8a6400' : DARK;
        lb.style.fontWeight = on || isSel ? 700 : 500;
      });
    }

    // 選んだ国をヒーロー右下（テキストと重ならない位置）に寄せて固定
    zoomToSelected() {
      if (!this._map) return;
      const id = this.getAttribute('selected');
      if (!id) { this.focus(); return; }
      const p = this.points.filter((x) => x.id === id)[0];
      if (!p) return;
      // 国土が広い国は points の selZoom（任意）で寄りの強さを弱める
      // 国土が広い国ほど寄りを弱める：国の範囲が収まるズームを上限 3.8・下限 2.2 で採用（selZoom があれば優先）
      let z = p.selZoom || 3.8;
      const bb = this._bbox && this._bbox[id];
      if (!p.selZoom && bb) {
        const cam = this._map.cameraForBounds(bb, { padding: 40 });
        if (cam && isFinite(cam.zoom)) z = Math.min(3.8, Math.max(2.2, cam.zoom - 0.3));
      }
      // select-offset="x,y"（px）指定があればそれを優先。無ければコンテナ比率で右下に配置
      const raw = this.getAttribute('select-offset');
      let off;
      if (raw) {
        const a = raw.split(',').map(Number);
        off = [a[0] || 0, a[1] || 0];
      } else {
        const c = this._map.getContainer();
        off = [c.clientWidth * 0.19, c.clientHeight * 0.20];
      }
      this._map.easeTo({ center: [p.lon, p.lat], zoom: z, offset: off, duration: 1000, easing: (t) => 1 - Math.pow(1 - t, 3) });
    }

    focus() {
      const name = this.getAttribute('focus-area');
      const b = name && (window.WM_AREA_BOUNDS || {})[name];
      if (b) this._map.fitBounds(b, { padding: 56, duration: 1100, maxZoom: 5 });
      else this._map.easeTo({ center: (this.getAttribute('center') || '40,20').split(',').map(Number), zoom: parseFloat(this.getAttribute('zoom')) || 1.15, duration: 900 });
    }

    flyTo(id) {
      const p = this.points.filter((x) => x.id === id)[0];
      if (p && this._map) this._map.flyTo({ center: [p.lon, p.lat], zoom: Math.max(this._map.getZoom(), 3.4), duration: 1100 });
    }
  }
  if (!customElements.get('world-map')) customElements.define('world-map', WorldMap);
})();
