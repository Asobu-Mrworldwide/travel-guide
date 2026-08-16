/* <world-map> — MapLibre GL による本物の地図（パン／ズーム／横方向は無限ループ）。
   タイル: MapLibre demotiles（APIキー不要）。World Mappy 配色に再着色して使う。
   属性: selected(id) / active(id) / visible(カンマ区切りid。未指定=おすすめのみ) / focus-area(エリア名)
   イベント: pointselect (detail = id)
   ※ Claude Design プロジェクト内の world-map.js をそのまま流用（ロジック変更なし）。 */
(function () {
  const CSS = 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css';
  const JS = 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js';
  const STYLE = 'https://demotiles.maplibre.org/style.json';
  const GREEN = '#1d9074', DARK = '#15735b', YELLOW = '#ffc200';

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
    static get observedAttributes() { return ['selected', 'active', 'visible', 'focus-area']; }
    connectedCallback() {
      if (this._init) return;
      this._init = true;
      this.style.display = 'block';
      this.style.position = 'relative';
      this._host = document.createElement('div');
      this._host.style.cssText = 'position:relative;width:100%;height:100%;background:#f4fbf8;';
      this.appendChild(this._host);
      this._hint = document.createElement('div');
      this._hint.style.cssText = 'position:absolute;left:12px;bottom:12px;z-index:2;pointer-events:none;font:400 11px/1.5 "Zen Kaku Gothic New",sans-serif;color:#15735b;background:rgba(255,255,255,.86);border:1px solid #dde8e2;border-radius:999px;padding:5px 11px;transition:opacity .3s ease;';
      this._hint.textContent = 'ドラッグで移動 ／ スクロールで拡大すると掲載国が増えます';
      this.appendChild(this._hint);
      this.boot();
    }
    attributeChangedCallback(n) {
      if (!this._map) return;
      if (n === 'focus-area') this.focus();
      else this.paint();
    }
    get points() { return window.WM_DESTINATIONS || []; }

    async boot() {
      const gl = await lib();
      const map = new gl.Map({
        container: this._host,
        style: STYLE,
        center: [40, 20],
        zoom: 1.15,
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
      map.on('load', () => {
        this.restyle();
        this.makeMarkers(gl);
        this.paint();
        if (this.getAttribute('focus-area')) this.focus();
      });
      map.on('zoom', () => {
        this.paint();
        this._hint.style.opacity = map.getZoom() > 2 ? '0' : '1';
      });
    }

    restyle() {
      const map = this._map;
      const WATER = '#dceeea', LAND = '#ffffff', LINE = '#c2d8d0';
      const set = (id, prop, val) => {
        try { map.setPaintProperty(id, prop, val); }
        catch (e) { console.warn('[world-map] restyle skipped', id, prop, e.message); }
      };
      map.getStyle().layers.forEach((l) => {
        const id = l.id, water = /water|ocean|sea|lake|bathymetry/i.test(id);
        if (l.type === 'background') set(id, 'background-color', WATER);
        else if (l.type === 'fill') {
          set(id, 'fill-color', water ? WATER : LAND);
          set(id, 'fill-opacity', 1);
          set(id, 'fill-outline-color', LINE);
        } else if (l.type === 'line') {
          set(id, 'line-color', LINE);
          set(id, 'line-width', 0.7);
        } else if (l.type === 'symbol') {
          set(id, 'text-color', '#7d8f88');
          set(id, 'text-halo-color', '#ffffff');
          set(id, 'text-halo-width', 1.2);
        }
      });
    }

    makeMarkers(gl) {
      this._markers = this.points.map((p) => {
        const el = document.createElement('div');
        el.style.cssText = 'cursor:pointer;';
        const inner = document.createElement('span');
        inner.style.cssText = 'display:flex;align-items:center;gap:6px;transform-origin:left center;transition:transform .3s cubic-bezier(.2,.7,.2,1),opacity .3s ease;';
        const dot = document.createElement('span');
        dot.style.cssText = 'width:12px;height:12px;border-radius:999px;flex:none;background:' + GREEN + ';box-shadow:0 0 0 3px rgba(255,255,255,.95),0 1px 4px rgba(0,0,0,.22);transition:all .3s cubic-bezier(.2,.7,.2,1);';
        const lb = document.createElement('span');
        lb.textContent = p.city;
        lb.style.cssText = 'font:500 11.5px/1 "Zen Kaku Gothic New",sans-serif;color:#15735b;background:rgba(255,255,255,.92);border:1px solid #dde8e2;border-radius:3px;padding:3px 6px;white-space:nowrap;transition:all .3s ease;';
        inner.appendChild(dot); inner.appendChild(lb);
        el.appendChild(inner);
        el.addEventListener('mouseenter', () => this.setAttribute('active', p.id));
        el.addEventListener('mouseleave', () => this.removeAttribute('active'));
        el.addEventListener('click', (e) => {
          e.stopPropagation();
          this.dispatchEvent(new CustomEvent('pointselect', { detail: p.id, bubbles: true, composed: true }));
        });
        const marker = new gl.Marker({ element: el, anchor: 'left', offset: [-6, 0] })
          .setLngLat([p.lon, p.lat]).addTo(this._map);
        return { p, el, inner, dot, lb, marker };
      });
    }

    paint() {
      if (!this._markers) return;
      const vis = this.getAttribute('visible');
      const filtered = vis != null && vis !== '__all__';
      const set = filtered ? (vis === '' ? [] : vis.split(',')) : null;
      const z = this._map.getZoom();
      const act = this.getAttribute('active'), sel = this.getAttribute('selected');
      this._markers.forEach(({ p, el, inner, dot, lb }) => {
        const allowed = set ? set.indexOf(p.id) >= 0 : (p.rec || z >= REVEAL_ZOOM);
        const on = act === p.id, isSel = sel === p.id;
        inner.style.opacity = allowed ? '1' : '0';
        inner.style.visibility = allowed ? 'visible' : 'hidden';
        el.style.pointerEvents = allowed ? 'auto' : 'none';
        inner.style.transform = on || isSel ? 'scale(1.12)' : 'scale(1)';
        el.style.zIndex = isSel ? 5 : on ? 4 : 1;
        dot.style.background = isSel ? YELLOW : GREEN;
        dot.style.width = dot.style.height = isSel ? '16px' : on ? '14px' : '12px';
        lb.style.opacity = allowed && (p.rec || z >= 2.2 || on || isSel) ? '1' : '0';
        lb.style.borderColor = isSel ? YELLOW : '#dde8e2';
        lb.style.color = isSel ? '#8a6400' : DARK;
        lb.style.fontWeight = on || isSel ? 700 : 500;
      });
    }

    focus() {
      const name = this.getAttribute('focus-area');
      const b = name && (window.WM_AREA_BOUNDS || {})[name];
      if (b) this._map.fitBounds(b, { padding: 56, duration: 1100, maxZoom: 5 });
      else this._map.easeTo({ center: [40, 20], zoom: 1.15, duration: 900 });
    }

    flyTo(id) {
      const p = this.points.filter((x) => x.id === id)[0];
      if (p && this._map) this._map.flyTo({ center: [p.lon, p.lat], zoom: Math.max(this._map.getZoom(), 3.4), duration: 1100 });
    }
  }
  if (!customElements.get('world-map')) customElements.define('world-map', WorldMap);
})();
