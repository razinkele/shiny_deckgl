(function () {
  // Store map instances by ID
  // Exposed on window for standalone HTML exports
  const mapInstances = window.__deckgl_instances = {};

  // -----------------------------------------------------------------------
  // Tooltip helper
  // -----------------------------------------------------------------------
  function getOrCreateTooltipEl(mapId) {
    let el = document.getElementById(mapId + '__tooltip');
    if (!el) {
      el = document.createElement('div');
      el.id = mapId + '__tooltip';
      el.className = 'deckgl-tooltip';
      const container = document.getElementById(mapId);
      if (container) {
        container.style.position = 'relative';
        container.appendChild(el);
      }
    }
    return el;
  }

  function interpolateTemplate(template, obj) {
    if (!template || !obj) return '';
    return template.replace(/\{(\w+(?:\.\w+)*)\}/g, function (_match, path) {
      let val = obj;
      for (const key of path.split('.')) {
        if (val == null) return '';
        val = val[key];
      }
      return val != null ? val : '';
    });
  }

  // -----------------------------------------------------------------------
  // DeckLegendControl — custom legend for deck.gl overlay layers
  //
  // Implements the MapLibre IControl interface (onAdd / onRemove).
  // Reads entries from the user-provided config, supports colour swatches,
  // visibility checkboxes, and a collapsible panel.
  // -----------------------------------------------------------------------
  class DeckLegendControl {
    constructor(options) {
      this._options = Object.assign({
        entries: [],
        showCheckbox: true,
        collapsed: false,
        title: null,
      }, options);
      this._container = null;
      this._map = null;
      this._mapId = null;
    }

    onAdd(map) {
      this._map = map;
      // Resolve the mapInstances key for this map
      for (const id of Object.keys(mapInstances)) {
        if (mapInstances[id].map === map) {
          this._mapId = id;
          break;
        }
      }

      this._container = document.createElement('div');
      this._container.className = 'maplibregl-ctrl deck-legend-ctrl';
      this._render();
      return this._container;
    }

    onRemove() {
      if (this._container && this._container.parentNode) {
        this._container.parentNode.removeChild(this._container);
      }
      this._map = null;
      this._mapId = null;
    }

    /* ---- private rendering ---- */

    _render() {
      const opts = this._options;
      const container = this._container;
      container.innerHTML = '';

      // Header (click to collapse / expand)
      if (opts.title) {
        const header = document.createElement('button');
        header.className = 'deck-legend-header';
        header.setAttribute('aria-label', 'Toggle legend');
        header.innerHTML = '<span class="deck-legend-title">' +
          this._esc(opts.title) + '</span><span class="deck-legend-arrow">' +
          (opts.collapsed ? '\u25B6' : '\u25BC') + '</span>';
        header.addEventListener('click', () => {
          const body = container.querySelector('.deck-legend-body');
          const arrow = header.querySelector('.deck-legend-arrow');
          if (!body) return;
          const hidden = body.style.display === 'none';
          body.style.display = hidden ? '' : 'none';
          if (arrow) arrow.textContent = hidden ? '\u25BC' : '\u25B6';
        });
        container.appendChild(header);
      }

      const body = document.createElement('div');
      body.className = 'deck-legend-body';
      if (opts.collapsed) body.style.display = 'none';

      const entries = opts.entries || [];
      for (const entry of entries) {
        const row = document.createElement('label');
        row.className = 'deck-legend-row';

        // Checkbox for visibility toggle
        if (opts.showCheckbox && entry.layer_id) {
          const cb = document.createElement('input');
          cb.type = 'checkbox';
          cb.checked = this._isLayerVisible(entry.layer_id);
          cb.className = 'deck-legend-cb';
          const self = this;
          cb.addEventListener('change', function () {
            self._toggleLayer(entry.layer_id, this.checked);
          });
          row.appendChild(cb);
        }

        // Swatch
        row.appendChild(this._createSwatch(entry));

        // Label text
        const lbl = document.createElement('span');
        lbl.className = 'deck-legend-label';
        lbl.textContent = entry.label || entry.layer_id || '';
        row.appendChild(lbl);

        body.appendChild(row);
      }

      container.appendChild(body);
    }

    /* ---- swatch factory ---- */

    _toCSS(c) {
      if (!c) return '#666';
      if (typeof c === 'string') return c;
      if (Array.isArray(c)) {
        if (c.length >= 4) return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + (c[3] / 255) + ')';
        return 'rgb(' + c[0] + ',' + c[1] + ',' + c[2] + ')';
      }
      return '#666';
    }

    _createSwatch(entry) {
      const shape = entry.shape || 'circle';
      const el = document.createElement('span');
      el.className = 'deck-legend-swatch deck-legend-sh-' + shape;

      if (shape === 'arc' && entry.color2) {
        el.style.background = 'linear-gradient(90deg,' + this._toCSS(entry.color) + ',' + this._toCSS(entry.color2) + ')';
      } else if (shape === 'gradient' && Array.isArray(entry.colors)) {
        el.style.background = 'linear-gradient(90deg,' + entry.colors.map(c => this._toCSS(c)).join(',') + ')';
      } else {
        el.style.backgroundColor = this._toCSS(entry.color);
      }

      return el;
    }

    /* ---- visibility helpers ---- */

    _isLayerVisible(layerId) {
      if (!this._mapId) return true;
      const inst = mapInstances[this._mapId];
      if (!inst) return true;
      const lp = inst.lastLayers.find(l => l.id === layerId);
      return lp ? lp.visible !== false : true;
    }

    _toggleLayer(layerId, visible) {
      if (!this._mapId) return;
      const inst = mapInstances[this._mapId];
      if (!inst) return;

      inst.lastLayers = inst.lastLayers.map(lp => {
        if (lp.id !== layerId) return lp;
        return Object.assign({}, lp, { visible: visible });
      });

      const deckLayers = buildDeckLayers(
        inst.lastLayers.map(lp => Object.assign({}, lp)),
        this._mapId,
        inst.tooltipConfig
      );
      inst.overlay.setProps({ layers: deckLayers });
      inst.map.triggerRepaint();
    }

    /* ---- utility ---- */
    _esc(s) {
      const d = document.createElement('span');
      d.textContent = s;
      return d.innerHTML;
    }
  }

  // -----------------------------------------------------------------------
  // Helper: create MapLibre control by type name
  // -----------------------------------------------------------------------
  function createControl(type, opts) {
    opts = opts || {};
    switch (type) {
      case 'navigation':
        return new maplibregl.NavigationControl(opts);
      case 'scale':
        return new maplibregl.ScaleControl(opts);
      case 'fullscreen':
        return new maplibregl.FullscreenControl(opts);
      case 'geolocate':
        return new maplibregl.GeolocateControl(Object.assign({
          positionOptions: { enableHighAccuracy: true },
          trackUserLocation: false
        }, opts));
      case 'globe':
        if (maplibregl.GlobeControl) {
          return new maplibregl.GlobeControl(opts);
        }
        console.warn('[shiny_deckgl] GlobeControl requires MapLibre v5+');
        return null;
      case 'terrain':
        if (maplibregl.TerrainControl) {
          return new maplibregl.TerrainControl(opts);
        }
        console.warn('[shiny_deckgl] TerrainControl requires MapLibre v5+');
        return null;
      case 'attribution':
        return new maplibregl.AttributionControl(opts);
      case 'legend':
        if (typeof MaplibreLegendControl !== 'undefined' &&
            MaplibreLegendControl.MaplibreLegendControl) {
          var targets = opts.targets || {};
          delete opts.targets;
          return new MaplibreLegendControl.MaplibreLegendControl(targets, opts);
        }
        console.warn('[shiny_deckgl] MaplibreLegendControl not loaded. Include the @watergis/maplibre-gl-legend CDN script.');
        return null;
      case 'opacity':
        if (typeof OpacityControl !== 'undefined') {
          return new OpacityControl(opts);
        }
        console.warn('[shiny_deckgl] OpacityControl not loaded. Include the maplibre-gl-opacity CDN script.');
        return null;
      case 'deck_legend':
        return new DeckLegendControl(opts);
      default:
        console.warn('[shiny_deckgl] Unknown control type: ' + type);
        return null;
    }
  }

  // -----------------------------------------------------------------------
  // Style-readiness guard — defers callback until map style is loaded.
  // Also respects _deckStyleChanging flag set by deck_set_style to avoid
  // a race where isStyleLoaded() briefly returns true during a style swap.
  // -----------------------------------------------------------------------
  function whenStyleReady(map, fn) {
    if (map.isStyleLoaded() && !map._deckStyleChanging) {
      fn();
    } else {
      map.once('style.load', fn);
    }
  }

  // -----------------------------------------------------------------------
  // Map initialisation
  // -----------------------------------------------------------------------
  function initMap(el) {
    const mapId = el.id;
    if (!mapId) return;

    // Read initial view state from data attributes (set by MapWidget)
    const initLon = parseFloat(el.dataset.initialLongitude) || 0;
    const initLat = parseFloat(el.dataset.initialLatitude) || 0;
    const initZoom = parseFloat(el.dataset.initialZoom) || 1;
    const initPitch = parseFloat(el.dataset.initialPitch) || 0;
    const initBearing = parseFloat(el.dataset.initialBearing) || 0;
    const initMinZoom = parseFloat(el.dataset.initialMinZoom) || 0;
    const initMaxZoom = parseFloat(el.dataset.initialMaxZoom) || 24;
    const mapStyle = el.dataset.style ||
      'https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json';

    // Optional Mapbox API key — enables mapbox:// style URLs
    const mapboxApiKey = el.dataset.mapboxApiKey || null;

    // Parse tooltip config from data-tooltip (JSON)
    let tooltipConfig = null;
    if (el.dataset.tooltip) {
      try { tooltipConfig = JSON.parse(el.dataset.tooltip); } catch (_) {}
    }

    const mapOpts = {
      container: mapId,
      style: mapStyle,
      center: [initLon, initLat],
      zoom: initZoom,
      pitch: initPitch,
      bearing: initBearing,
      minZoom: initMinZoom,
      maxZoom: initMaxZoom,
      preserveDrawingBuffer: true
    };

    // Cooperative gestures: require Ctrl+scroll to zoom, two-finger drag on mobile
    if (el.dataset.cooperativeGestures === 'true') {
      mapOpts.cooperativeGestures = true;
    }

    // Mapbox API key: inject into tile requests if a mapbox:// style is used
    if (mapboxApiKey) {
      mapOpts.transformRequest = function(url, resourceType) {
        if (url.indexOf('mapbox') !== -1 && url.indexOf('access_token') === -1) {
          var sep = url.indexOf('?') === -1 ? '?' : '&';
          return { url: url + sep + 'access_token=' + mapboxApiKey };
        }
      };
    }
    const map = new maplibregl.Map(mapOpts);

    // Apply initial controller setting from data attribute
    if (el.dataset.controller !== undefined) {
      try {
        var ctrlVal = JSON.parse(el.dataset.controller);
        if (ctrlVal === false) {
          map.dragPan.disable();
          map.scrollZoom.disable();
          map.boxZoom.disable();
          map.dragRotate.disable();
          map.keyboard.disable();
          map.doubleClickZoom.disable();
          map.touchZoomRotate.disable();
        }
      } catch (_) {}
    }

    // ---- Configurable initial controls ------------------------------------
    // Parse controls config from data-controls attribute (JSON array).
    // When the attribute is present (even as "[]") honour it exactly;
    // only fall back to a default NavigationControl when the attribute
    // is absent (i.e. the widget was constructed with controls=None).
    var controlsConfig = [];
    if (el.dataset.controls !== undefined) {
      try { controlsConfig = JSON.parse(el.dataset.controls); } catch (_) {}
    } else {
      controlsConfig = [{ type: 'navigation', position: 'top-right' }];
    }

    var initialControls = {};
    controlsConfig.forEach(function (cfg) {
      var ctrl = createControl(cfg.type, cfg.options || {});
      if (ctrl) {
        var pos = cfg.position || 'top-right';
        map.addControl(ctrl, pos);
        initialControls[cfg.type] = { control: ctrl, position: pos };
      }
    });

    // Send view state back to Shiny on every meaningful camera move
    map.on('moveend', function () {
      var center = map.getCenter();
      var bounds = map.getBounds();
      Shiny.setInputValue(mapId + '_view_state', {
        longitude: center.lng,
        latitude: center.lat,
        zoom: map.getZoom(),
        pitch: map.getPitch(),
        bearing: map.getBearing(),
        bounds: {
          sw: [bounds.getSouthWest().lng, bounds.getSouthWest().lat],
          ne: [bounds.getNorthEast().lng, bounds.getNorthEast().lat]
        }
      });
    });

    // Send map-level click coordinates to Shiny (fires even on empty areas)
    map.on('click', function (e) {
      Shiny.setInputValue(mapId + '_map_click', {
        longitude: e.lngLat.lng,
        latitude: e.lngLat.lat,
        point: { x: e.point.x, y: e.point.y }
      }, { priority: "event" });
    });

    // Context menu (right-click) for secondary actions
    map.on('contextmenu', function (e) {
      Shiny.setInputValue(mapId + '_map_contextmenu', {
        longitude: e.lngLat.lng,
        latitude: e.lngLat.lat,
        point: { x: e.point.x, y: e.point.y }
      }, { priority: "event" });
    });

    var interleavedMode = el.dataset.interleaved === 'true';
    const overlay = new deck.MapboxOverlay({
      interleaved: interleavedMode,
      layers: [],
      // Forward widget-initiated view state changes (e.g. CompassWidget
      // bearing reset, ZoomWidget zoom) back to the MapLibre map.
      // Without this, the overlay silently consumes the change and MapLibre
      // overwrites it on the next render frame.
      onViewStateChange: function (params) {
        var vs = params.viewState;
        if (!vs) return;
        var opts = {
          center: [vs.longitude, vs.latitude],
          zoom: vs.zoom,
          bearing: vs.bearing || 0,
          pitch: vs.pitch || 0,
        };
        if (vs.transitionDuration > 0) {
          opts.duration = vs.transitionDuration;
          map.easeTo(opts);
        } else {
          map.jumpTo(opts);
        }
      }
    });

    // Apply initial deck-level props from data attributes
    var initialDeckProps = {};
    if (el.dataset.pickingRadius) {
      initialDeckProps.pickingRadius = parseInt(el.dataset.pickingRadius, 10) || 0;
    }
    if (el.dataset.useDevicePixels !== undefined) {
      try { initialDeckProps.useDevicePixels = JSON.parse(el.dataset.useDevicePixels); } catch (_) {}
    }
    if (el.dataset.animate === 'true') {
      initialDeckProps._animate = true;
    }
    if (el.dataset.parameters) {
      try { initialDeckProps.parameters = JSON.parse(el.dataset.parameters); } catch (_) {}
    }
    if (Object.keys(initialDeckProps).length) {
      overlay.setProps(initialDeckProps);
    }

    map.addControl(overlay);

    mapInstances[mapId] = {
      map: map,
      overlay: overlay,
      tooltipConfig: tooltipConfig,
      dragMarker: null,
      lastLayers: [],          // cache for visibility toggling
      controls: initialControls,
      nativeLayers: {},        // tracks native MapLibre layers added via add_maplibre_layer
      // TripsLayer animation state (v0.9.0)
      tripsAnimation: null     // {rafId, loopLength, speed, startedAt}
    };
  }

  // Initialize all deckgl-map divs on page load inside shiny
  document.addEventListener('shiny:connected', function() {
    document.querySelectorAll('.deckgl-map').forEach(initMap);
  });

  // -----------------------------------------------------------------------
  // Helper: resolve @@ accessors
  // -----------------------------------------------------------------------
  function resolveAccessors(layerProps) {
    for (const key of Object.keys(layerProps)) {
      const val = layerProps[key];
      if (typeof val !== 'string' || !val.startsWith('@@')) continue;
      const raw = val.slice(2);

      // @@d — identity accessor (return datum as-is)
      if (raw === 'd') {
        layerProps[key] = d => d;
        continue;
      }

      // @@=expr — expression accessor (safe subset)
      // Supports:  d.prop, d.a.b, d[0], d[2], d["key"]
      if (raw.startsWith('=')) {
        const expr = raw.slice(1).trim();
        try {
          // eslint-disable-next-line no-new-func
          layerProps[key] = new Function('d', 'return ' + expr);
        } catch (e) {
          console.warn('[shiny_deckgl] Bad accessor "' + val + '":', e.message);
        }
        continue;
      }

      // @@d.prop — simple property shorthand (legacy)
      if (raw.startsWith('d.')) {
        const prop = raw.slice(2);
        layerProps[key] = d => d[prop];
      }
    }
  }

  // -----------------------------------------------------------------------
  // Helper: resolve @@extensions → deck.gl Extension instances
  // -----------------------------------------------------------------------
  function resolveExtensions(layerProps) {
    if (!Array.isArray(layerProps['@@extensions'])) return;
    layerProps.extensions = layerProps['@@extensions'].map(item => {
      // String form: instantiate with no arguments
      if (typeof item === 'string') {
        const Cls = deck[item];
        if (!Cls) {
          console.warn('[shiny_deckgl] Unknown extension: ' + item);
          return null;
        }
        return new Cls();
      }
      // Object form: { "@@extClass": "Name", "@@extOpts": {...} }
      if (item && item['@@extClass']) {
        const Cls = deck[item['@@extClass']];
        if (!Cls) {
          console.warn('[shiny_deckgl] Unknown extension: ' + item['@@extClass']);
          return null;
        }
        return new Cls(item['@@extOpts'] || {});
      }
      console.warn('[shiny_deckgl] Invalid extension spec:', item);
      return null;
    }).filter(e => e !== null);
    delete layerProps['@@extensions'];
  }

  // -----------------------------------------------------------------------
  // Helper: decode base64 binary attributes → TypedArrays
  // -----------------------------------------------------------------------
  const TYPED_ARRAY_MAP = {
    float32: Float32Array,
    float64: Float64Array,
    uint8: Uint8Array,
    int32: Int32Array
  };

  function resolveBinaryAttributes(layerProps) {
    var binaryAttrs = {};
    var hasBinary = false;
    for (const key of Object.keys(layerProps)) {
      const val = layerProps[key];
      if (val && typeof val === 'object' && val['@@binary']) {
        const ArrayCtor = TYPED_ARRAY_MAP[val.dtype] || Float32Array;
        const raw = atob(val.value);
        const bytes = new Uint8Array(raw.length);
        for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
        const typed = new ArrayCtor(bytes.buffer);
        binaryAttrs[key] = { value: typed, size: val.size || 1 };
        delete layerProps[key];
        hasBinary = true;
      }
    }
    // deck.gl v9 requires binary attributes in data.attributes
    if (hasBinary) {
      if (!layerProps.data || typeof layerProps.data !== 'object') {
        layerProps.data = {};
      }
      if (typeof layerProps.data.length === 'undefined') {
        // Infer length from first binary attribute
        var firstKey = Object.keys(binaryAttrs)[0];
        var attr = binaryAttrs[firstKey];
        layerProps.data.length = attr.value.length / (attr.size || 1);
      }
      layerProps.data.attributes = Object.assign(
        layerProps.data.attributes || {}, binaryAttrs
      );
    }
  }

  // -----------------------------------------------------------------------
  // Helper: resolve effects specs → deck.gl Effect instances
  // -----------------------------------------------------------------------
  function buildEffects(effectsData) {
    if (!effectsData || !effectsData.length) return undefined;
    return effectsData.map(spec => {
      if (spec.type === 'LightingEffect') {
        const lights = {};
        if (spec.ambientLight) {
          lights.ambient = new deck.AmbientLight(spec.ambientLight);
        }
        if (Array.isArray(spec.pointLights)) {
          spec.pointLights.forEach((pl, i) => { lights['point' + i] = new deck.PointLight(pl); });
        }
        if (Array.isArray(spec.directionalLights)) {
          spec.directionalLights.forEach((dl, i) => { lights['dir' + i] = new deck.DirectionalLight(dl); });
        }
        return new deck.LightingEffect(lights);
      }
      // PostProcessEffect
      if (spec.type === 'PostProcessEffect' && deck.PostProcessEffect) {
        return new deck.PostProcessEffect(spec);
      }
      console.warn('[shiny_deckgl] Unknown effect type: ' + spec.type);
      return null;
    }).filter(e => e !== null);
  }

  // -----------------------------------------------------------------------
  // Helper: resolve view specs → deck.gl View instances
  // -----------------------------------------------------------------------
  function buildViews(viewsData) {
    if (!viewsData || !viewsData.length) return undefined;
    return viewsData.map(spec => {
      const typeName = spec['@@type'] || 'MapView';
      const props = Object.assign({}, spec);
      delete props['@@type'];
      const ViewClass = deck[typeName];
      if (!ViewClass) {
        console.warn('[shiny_deckgl] Unknown view type: ' + typeName);
        return null;
      }
      return new ViewClass(props);
    }).filter(v => v !== null);
  }

  // -----------------------------------------------------------------------
  // Helper: resolve widget specs → deck.gl Widget instances (v0.8.0)
  // -----------------------------------------------------------------------
  function buildWidgets(widgetSpecs, targetId) {
    if (!widgetSpecs || !widgetSpecs.length) return undefined;
    // Resolve the map container element so FullscreenWidget can target it
    var containerEl = targetId ? document.getElementById(targetId) : null;
    return widgetSpecs.map(spec => {
      var className = spec['@@widgetClass'];
      if (!className) return null;
      var props = Object.assign({}, spec);
      delete props['@@widgetClass'];
      // FullscreenWidget must target the map container, not the deck canvas
      if (className === 'FullscreenWidget' && containerEl && !props.container) {
        props.container = containerEl;
      }
      var Cls = deck[className] || deck['_' + className];
      if (!Cls) {
        console.warn('[shiny_deckgl] Unknown widget: ' + className);
        return null;
      }
      return new Cls(props);
    }).filter(Boolean);
  }

  // -----------------------------------------------------------------------
  // Built-in easing functions for layer transitions (v0.8.0)
  // -----------------------------------------------------------------------
  var EASINGS = {
    'ease-in-cubic': function(t) { return t * t * t; },
    'ease-out-cubic': function(t) { return 1 - Math.pow(1 - t, 3); },
    'ease-in-out-cubic': function(t) { return t < 0.5 ? 4*t*t*t : 1 - Math.pow(-2*t+2, 3)/2; },
    'ease-in-out-sine': function(t) { return -(Math.cos(Math.PI * t) - 1) / 2; }
  };

  // -----------------------------------------------------------------------
  // Helper: lon/lat → EPSG:3857 (Web Mercator) projection
  // -----------------------------------------------------------------------
  const EARTH_HALF_CIRC = 20037508.342789244;   // π × 6378137

  function lonToMercX(lon) {
    return lon * EARTH_HALF_CIRC / 180;
  }

  function latToMercY(lat) {
    const rad = lat * Math.PI / 180;
    return Math.log(Math.tan(Math.PI / 4 + rad / 2)) * EARTH_HALF_CIRC / Math.PI;
  }

  // Regex to detect WMS-style bbox placeholders:  {bbox-epsg-NNNN}
  const WMS_BBOX_RE = /\{bbox-epsg-(\d+)\}/;

  // -----------------------------------------------------------------------
  // Helper: build deck.gl Layer instances from plain props
  // -----------------------------------------------------------------------
  const RASTER_TYPES = new Set(["TileLayer", "BitmapLayer"]);

  function buildDeckLayers(layersData, targetId, tooltipConfig) {
    return layersData.map(layerProps => {
      resolveAccessors(layerProps);
      resolveExtensions(layerProps);
      resolveBinaryAttributes(layerProps);

      // Resolve @@easing in transitions specs (v0.8.0)
      if (layerProps.transitions) {
        for (var prop in layerProps.transitions) {
          var tSpec = layerProps.transitions[prop];
          if (tSpec && tSpec['@@easing']) {
            tSpec.easing = EASINGS[tSpec['@@easing']] || function(t) { return t; };
            delete tSpec['@@easing'];
          }
        }
      }

      // Set up pick handling for non-raster layers
      if (!RASTER_TYPES.has(layerProps.type) && layerProps.pickable !== false) {
        layerProps.pickable = true;

        // Click → Shiny input
        if (!layerProps.onClick) {
          layerProps.onClick = function(info) {
            if (info.object) {
              Shiny.setInputValue(targetId + "_click", {
                mapId: targetId,
                layerId: layerProps.id,
                object: info.object,
                coordinate: info.coordinate
              }, {priority: "event"});
            }
          };
        }

        // Hover → Shiny input + tooltip
        if (!layerProps.onHover) {
          layerProps.onHover = function(info) {
            if (info.object) {
              Shiny.setInputValue(targetId + "_hover", {
                mapId: targetId,
                layerId: layerProps.id,
                object: info.object,
                coordinate: info.coordinate
              });
            } else {
              Shiny.setInputValue(targetId + "_hover", null);
            }

            if (tooltipConfig && tooltipConfig.html) {
              const tooltipEl = getOrCreateTooltipEl(targetId);
              if (info.object) {
                const src = info.object.properties || info.object;
                tooltipEl.innerHTML = interpolateTemplate(tooltipConfig.html, src);
                tooltipEl.style.display = 'block';
                tooltipEl.style.left = (info.x || 0) + 'px';
                tooltipEl.style.top = (info.y || 0) + 'px';
                if (tooltipConfig.style) {
                  Object.assign(tooltipEl.style, tooltipConfig.style);
                }
              } else {
                tooltipEl.style.display = 'none';
              }
            }
          };
        }
      }

      const LayerClass = deck[layerProps.type];
      if (!LayerClass) {
        console.warn('[shiny_deckgl] Unknown layer type: ' + layerProps.type + ' — skipped');
        return null;
      }

      // TileLayer: resolve @@BitmapLayer renderSubLayers shorthand
      if (layerProps.type === "TileLayer" && layerProps.renderSubLayers === "@@BitmapLayer") {
        layerProps.renderSubLayers = props => {
          const { bbox: {west, south, east, north} } = props.tile;
          return new deck.BitmapLayer(props, {
            data: null,
            image: props.data,
            bounds: [west, south, east, north]
          });
        };
      }

      // TileLayer: resolve WMS {bbox-epsg-NNNN} placeholders
      if (layerProps.type === "TileLayer" && typeof layerProps.data === 'string') {
        const bboxMatch = layerProps.data.match(WMS_BBOX_RE);
        if (bboxMatch) {
          const epsg = bboxMatch[1];   // e.g. "3857" or "4326"
          const urlTemplate = layerProps.data;
          layerProps.getTileData = function (tile) {
            const { west, south, east, north } = tile.bbox;
            var bboxStr;
            if (epsg === '3857') {
              bboxStr = [
                lonToMercX(west), latToMercY(south),
                lonToMercX(east), latToMercY(north)
              ].join(',');
            } else {
              // EPSG:4326 or other geographic CRS — use lon/lat directly
              bboxStr = [west, south, east, north].join(',');
            }
            var url = urlTemplate.replace(WMS_BBOX_RE, bboxStr);
            return fetch(url, { signal: tile.signal })
              .then(function (r) {
                if (!r.ok) return null;
                var ct = (r.headers.get('content-type') || '').toLowerCase();
                // WMS servers may return XML errors with 200 status
                if (ct.indexOf('xml') !== -1 || ct.indexOf('text') !== -1) return null;
                return r.blob();
              })
              .then(function (blob) {
                if (!blob || blob.size === 0) return null;
                return createImageBitmap(blob);
              })
              .catch(function () {
                // Silently ignore decode failures (empty/corrupt tiles)
                return null;
              });
          };
          // Remove the raw URL so TileLayer doesn't try its own fetch
          delete layerProps.data;
        }
      }

      return new LayerClass(layerProps);
    }).filter(l => l !== null);
  }

  // -----------------------------------------------------------------------
  // TripsLayer animation loop (v0.9.0)
  // -----------------------------------------------------------------------
  // Scans layers for any TripsLayer.  If found and the layer specifies
  // _tripsAnimation: {loopLength, speed}, starts a requestAnimationFrame
  // loop that increments currentTime and re-builds the layer each frame.
  // If _tripsHeadIcons is also present, a companion IconLayer renders a
  // sprite at the interpolated head of each trajectory.

  /**
   * Interpolate the current head position for every trip in *tripsData*
   * given the TripsLayer's *currentTime*.  Returns an array of objects
   * with { position, color, icon } for rendering as an IconLayer.
   */
  function interpolateTripHeads(tripsData, currentTime, iconField) {
    var heads = [];
    for (var i = 0; i < tripsData.length; i++) {
      var trip = tripsData[i];
      var path = trip.path;
      if (!path || path.length < 2) continue;

      var pos = null;
      var angle = 0; // degrees for deck.gl getAngle (billboard:false)
      for (var j = 0; j < path.length - 1; j++) {
        var t0 = path[j][2];
        var t1 = path[j + 1][2];
        if (currentTime >= t0 && currentTime <= t1) {
          var frac = (t1 !== t0) ? (currentTime - t0) / (t1 - t0) : 0;
          var dx = path[j + 1][0] - path[j][0];
          var dy = path[j + 1][1] - path[j][1];
          pos = [
            path[j][0] + dx * frac,
            path[j][1] + dy * frac,
          ];
          // The SVG seal faces RIGHT (east).  deck.gl getAngle with
          // billboard:false is degrees CW from north applied to the
          // icon's TOP.  We need the seal's body (right = head) to
          // align with the movement direction, so we compute:
          //   compass_bearing = 90 - atan2(dy,dx)*180/π
          // then subtract 90° because the seal's "forward" is RIGHT
          // (not TOP):  angle = bearing - 90 = -atan2(dy,dx)*180/π.
          // However, empirically this produces a 90° offset because
          // deck.gl applies the rotation to the atlas sprite directly,
          // so the correct formula is simply:
          angle = Math.atan2(dy, dx) * 180 / Math.PI;
          break;
        }
      }
      // Before first or past last timestamp — snap to endpoints
      if (!pos) {
        if (currentTime <= path[0][2]) {
          pos = [path[0][0], path[0][1]];
          if (path.length >= 2) {
            var dx0 = path[1][0] - path[0][0];
            var dy0 = path[1][1] - path[0][1];
            angle = Math.atan2(dy0, dx0) * 180 / Math.PI;
          }
        } else {
          var last = path[path.length - 1];
          pos = [last[0], last[1]];
          if (path.length >= 2) {
            var prev = path[path.length - 2];
            angle = Math.atan2(last[1] - prev[1], last[0] - prev[0]) * 180 / Math.PI;
          }
        }
      }

      heads.push({
        position: pos,
        color: trip.color || [255, 140, 0, 230],
        icon: trip[iconField || 'species'] || 'Grey seal',
        angle: angle,
      });
    }
    return heads;
  }

  function startTripsAnimation(instance, targetId) {
    // Stop any running animation first
    stopTripsAnimation(instance);

    var layersData = instance.lastLayers;
    var tripsConfigs = [];     // {index, loopLength, speed, headIcons?}
    for (var i = 0; i < layersData.length; i++) {
      var lp = layersData[i];
      if (lp.type === 'TripsLayer' && lp._tripsAnimation) {
        var cfg = {
          index: i,
          loopLength: lp._tripsAnimation.loopLength || 1800,
          speed: lp._tripsAnimation.speed || 1,
        };
        if (lp._tripsHeadIcons) {
          cfg.headIcons = lp._tripsHeadIcons;
        }
        tripsConfigs.push(cfg);
      }
    }
    if (tripsConfigs.length === 0) return;

    // Preserve accumulated time when resuming from a pause
    var timeOffset = (instance.tripsAnimation && instance.tripsAnimation.pausedAt != null)
                       ? instance.tripsAnimation.pausedAt : 0;
    var startedAt = performance.now();
    function tick() {
      var elapsed = (performance.now() - startedAt) / 1000 + timeOffset;
      // Update currentTime on each TripsLayer
      for (var c = 0; c < tripsConfigs.length; c++) {
        var cfg = tripsConfigs[c];
        var t = (elapsed * cfg.speed) % cfg.loopLength;
        layersData[cfg.index].currentTime = t;
      }

      // Re-build and push layers
      var deckLayers = buildDeckLayers(
        JSON.parse(JSON.stringify(layersData)),
        targetId,
        instance.tooltipConfig
      );

      // Append head-icon layers for TripsLayers with _tripsHeadIcons
      // Species-coloured SVG atlas — each silhouette has its own fill.
      for (var c = 0; c < tripsConfigs.length; c++) {
        var cfg = tripsConfigs[c];
        if (!cfg.headIcons) continue;
        var lp = layersData[cfg.index];
        var hi = cfg.headIcons;
        var heads = interpolateTripHeads(
          lp.data, lp.currentTime, hi.iconField || 'species'
        );
        if (heads.length > 0) {
          deckLayers.push(new deck.IconLayer({
            id: (lp.id || 'trips') + '_heads',
            data: heads,
            iconAtlas: hi.iconAtlas,
            iconMapping: hi.iconMapping,
            getPosition: function(d) { return d.position; },
            getIcon: function(d) { return d.icon; },
            getColor: function(d) { return d.color; },
            getAngle: function(d) { return d.angle || 0; },
            getSize: hi.getSize || 24,
            sizeScale: hi.sizeScale || 1,
            sizeMinPixels: hi.sizeMinPixels || 10,
            sizeMaxPixels: hi.sizeMaxPixels || 64,
            billboard: false,
            pickable: false,
          }));
        }
      }

      instance.overlay.setProps({ layers: deckLayers });

      instance.tripsAnimation = instance.tripsAnimation || {};
      instance.tripsAnimation.rafId = requestAnimationFrame(tick);
      instance.tripsAnimation.startedAt = startedAt;
      instance.tripsAnimation.timeOffset = timeOffset;
    }
    instance.tripsAnimation = { rafId: requestAnimationFrame(tick), startedAt: startedAt, timeOffset: timeOffset };
  }

  function pauseTripsAnimation(instance) {
    if (instance.tripsAnimation && instance.tripsAnimation.rafId) {
      cancelAnimationFrame(instance.tripsAnimation.rafId);
      // Compute accumulated elapsed time so we can resume from the same point
      var accumulated = (performance.now() - instance.tripsAnimation.startedAt) / 1000
                      + (instance.tripsAnimation.timeOffset || 0);
      instance.tripsAnimation.rafId = null;
      instance.tripsAnimation.pausedAt = accumulated;
    }
  }

  function stopTripsAnimation(instance) {
    if (instance.tripsAnimation && instance.tripsAnimation.rafId) {
      cancelAnimationFrame(instance.tripsAnimation.rafId);
    }
    // Full stop — clear pausedAt so next start begins from 0
    if (instance.tripsAnimation) {
      instance.tripsAnimation = null;
    }
  }

  // -----------------------------------------------------------------------
  // Ensure instance helper
  // -----------------------------------------------------------------------
  function ensureInstance(targetId) {
    let instance = mapInstances[targetId];
    if (!instance) {
      const el = document.getElementById(targetId);
      if (el) {
        initMap(el);
        instance = mapInstances[targetId];
      }
    }
    return instance || null;
  }

  // -----------------------------------------------------------------------
  // deck_update — main layer push
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_update", function (payload) {
    if (!payload || !payload.id) return;
    const targetId = payload.id;
    const instance = ensureInstance(targetId);
    if (!instance) return;

    const { map, overlay, tooltipConfig } = instance;

    // Handle view state updates (flyTo if duration > 0, else jumpTo)
    if (payload.viewState) {
      const vs = payload.viewState;
      const opts = {
        center: [vs.longitude || 0, vs.latitude || 0],
        zoom: vs.zoom || 1,
        pitch: vs.pitch || 0,
        bearing: vs.bearing || 0
      };
      if (payload.transitionDuration && payload.transitionDuration > 0) {
        opts.duration = payload.transitionDuration;
        map.flyTo(opts);
      } else {
        map.jumpTo(opts);
      }
    }

    // Build layers and cache raw props for visibility toggling
    const layersData = payload.layers || [];
    instance.lastLayers = layersData;
    const deckLayers = buildDeckLayers(
      JSON.parse(JSON.stringify(layersData)),   // deep-clone to avoid mutating cache
      targetId,
      tooltipConfig
    );
    const overlayProps = { layers: deckLayers };

    // Effects (lighting, post-processing)
    const effects = buildEffects(payload.effects);
    if (effects) overlayProps.effects = effects;

    // Views (MapView, OrthographicView, FirstPersonView)
    const views = buildViews(payload.views);
    if (views) overlayProps.views = views;

    // Deck-level props (v0.7.0)
    if (payload.pickingRadius !== undefined) overlayProps.pickingRadius = payload.pickingRadius;
    if (payload.useDevicePixels !== undefined) overlayProps.useDevicePixels = payload.useDevicePixels;
    if (payload._animate !== undefined) overlayProps._animate = payload._animate;

    // Widgets (v0.8.0)
    var widgets = buildWidgets(payload.widgets, targetId);
    if (widgets) overlayProps.widgets = widgets;

    overlay.setProps(overlayProps);
    map.triggerRepaint();

    // Start/stop TripsLayer animation if needed (v0.9.0)
    startTripsAnimation(instance, targetId);
  });

  // -----------------------------------------------------------------------
  // deck_trips_control — pause / resume / reset TripsLayer animation
  // -----------------------------------------------------------------------
  // payload: { id: "map_id", action: "pause" | "resume" | "reset" }
  Shiny.addCustomMessageHandler("deck_trips_control", function (payload) {
    if (!payload || !payload.id) return;
    var targetId = payload.id;
    var instance = mapInstances[targetId];
    if (!instance) return;
    var action = payload.action || 'pause';

    if (action === 'pause') {
      pauseTripsAnimation(instance);
    } else if (action === 'resume') {
      // Resume from where we paused
      startTripsAnimation(instance, targetId);
    } else if (action === 'reset') {
      // Full stop then restart from time 0
      stopTripsAnimation(instance);
      startTripsAnimation(instance, targetId);
    }
  });

  // -----------------------------------------------------------------------
  // deck_set_widgets — update widgets without resending layers (v0.8.0)
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_set_widgets", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;
    var widgets = buildWidgets(payload.widgets, payload.id);
    if (widgets) {
      instance.overlay.setProps({ widgets: widgets });
      instance.map.triggerRepaint();
    }
  });

  // -----------------------------------------------------------------------
  // deck_fly_to — smooth flyTo camera transition (v0.8.0)
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_fly_to", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;
    var vs = payload.viewState || {};
    var opts = {
      center: [vs.longitude || 0, vs.latitude || 0],
      speed: payload.speed || 1.2
    };
    if (vs.zoom != null) opts.zoom = vs.zoom;
    if (vs.pitch != null) opts.pitch = vs.pitch;
    if (vs.bearing != null) opts.bearing = vs.bearing;
    if (payload.duration !== "auto") opts.duration = payload.duration;
    instance.map.flyTo(opts);
  });

  // -----------------------------------------------------------------------
  // deck_ease_to — smooth easeTo camera transition (v0.8.0)
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_ease_to", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;
    var vs = payload.viewState || {};
    var opts = {
      center: [vs.longitude || 0, vs.latitude || 0],
      duration: payload.duration || 1000
    };
    if (vs.zoom != null) opts.zoom = vs.zoom;
    if (vs.pitch != null) opts.pitch = vs.pitch;
    if (vs.bearing != null) opts.bearing = vs.bearing;
    instance.map.easeTo(opts);
  });

  // -----------------------------------------------------------------------
  // deck_set_controller — configure map controller behaviour
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_set_controller", function (payload) {
    if (!payload || !payload.id) return;
    const instance = ensureInstance(payload.id);
    if (!instance) return;
    const ctrl = payload.controller;
    // MapboxOverlay exposes controller via setProps
    instance.overlay.setProps({ controller: ctrl });
    instance.map.triggerRepaint();
  });

  // -----------------------------------------------------------------------
  // deck_set_cooperative_gestures — toggle cooperative gestures
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_set_cooperative_gestures", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;
    var map = instance.map;
    if (payload.enabled) {
      if (map.cooperativeGestures) {
        map.cooperativeGestures.enable();
      }
    } else {
      if (map.cooperativeGestures) {
        map.cooperativeGestures.disable();
      }
    }
  });

  // -----------------------------------------------------------------------
  // deck_layer_visibility — toggle without resending data
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_layer_visibility", function (payload) {
    if (!payload || !payload.id) return;
    const targetId = payload.id;
    const instance = ensureInstance(targetId);
    if (!instance) return;

    const visMap = payload.visibility || {};
    const patched = instance.lastLayers.map(lp => {
      if (!(lp.id in visMap)) return lp;
      const copy = Object.assign({}, lp);
      copy.visible = visMap[copy.id];
      return copy;
    });
    instance.lastLayers = patched;

    const deckLayers = buildDeckLayers(
      patched.map(lp => Object.assign({}, lp)),
      targetId,
      instance.tooltipConfig
    );
    instance.overlay.setProps({ layers: deckLayers });
    instance.map.triggerRepaint();
  });

  // -----------------------------------------------------------------------
  // deck_add_drag_marker — draggable MapLibre marker → Shiny input
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_add_drag_marker", function (payload) {
    if (!payload || !payload.id) return;
    const targetId = payload.id;
    const instance = ensureInstance(targetId);
    if (!instance) return;

    const map = instance.map;

    // Remove existing drag marker if present
    if (instance.dragMarker) {
      instance.dragMarker.remove();
    }

    const center = map.getCenter();
    const lng = (payload.longitude != null) ? payload.longitude : center.lng;
    const lat = (payload.latitude != null) ? payload.latitude : center.lat;

    const marker = new maplibregl.Marker({ draggable: true })
      .setLngLat([lng, lat])
      .addTo(map);

    // Send initial position
    Shiny.setInputValue(targetId + '_drag', {
      longitude: lng,
      latitude: lat
    });

    // Update on drag end
    marker.on('dragend', function () {
      const lngLat = marker.getLngLat();
      Shiny.setInputValue(targetId + '_drag', {
        longitude: lngLat.lng,
        latitude: lngLat.lat
      }, {priority: "event"});
    });

    instance.dragMarker = marker;
  });

  // -----------------------------------------------------------------------
  // deck_set_style — change the basemap style dynamically
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_set_style", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;
    if (instance.nativeLayers && Object.keys(instance.nativeLayers).length > 0) {
      console.warn('[shiny_deckgl] set_style will remove all native sources/layers. '
        + 'Re-add them after the style loads.');
    }
    // Guard against whenStyleReady race: mark the map as style-changing so
    // that any Shiny messages arriving between setStyle() and the next
    // 'style.load' event correctly queue instead of running immediately.
    instance.map._deckStyleChanging = true;
    instance.map.once('style.load', function () {
      instance.map._deckStyleChanging = false;
    });
    var styleOpts = {};
    if (payload.diff) {
      styleOpts.diff = true;
    }
    instance.map.setStyle(payload.style, styleOpts);
    // Clear stale tracker — all native layers/sources are removed by setStyle
    // (unless diff mode preserves them)
    if (!payload.diff) {
      instance.nativeLayers = {};
    }
  });

  // -----------------------------------------------------------------------
  // deck_add_control — add a MapLibre control
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_add_control", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var type = payload.controlType;
    var position = payload.position || 'top-right';
    var opts = payload.options || {};

    // Remove existing control of same type first
    if (instance.controls[type]) {
      instance.map.removeControl(instance.controls[type].control);
      delete instance.controls[type];
    }

    var control = createControl(type, opts);
    if (!control) return;

    instance.map.addControl(control, position);
    instance.controls[type] = { control: control, position: position };
  });

  // -----------------------------------------------------------------------
  // deck_remove_control — remove a MapLibre control
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_remove_control", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var type = payload.controlType;
    if (instance.controls[type]) {
      instance.map.removeControl(instance.controls[type].control);
      delete instance.controls[type];
    }
  });

  // -----------------------------------------------------------------------
  // deck_set_controls — replace all MapLibre controls at once
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_set_controls", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    // Defer until style is loaded so that native sources/layers added
    // via deck_add_source / deck_add_maplibre_layer (which also use
    // whenStyleReady) are present before legend/opacity controls inspect
    // the map style.
    whenStyleReady(instance.map, function() {
      // Remove all existing controls
      var existing = Object.keys(instance.controls);
      for (var i = 0; i < existing.length; i++) {
        var key = existing[i];
        try {
          instance.map.removeControl(instance.controls[key].control);
        } catch (e) { /* ignore */ }
        delete instance.controls[key];
      }

      // Add new controls
      var newControls = payload.controls || [];
      for (var j = 0; j < newControls.length; j++) {
        var spec = newControls[j];
        var type = spec.type;
        var position = spec.position || 'top-right';
        var opts = spec.options || {};

        var control = createControl(type, opts);
        if (!control) continue;

        instance.map.addControl(control, position);
        instance.controls[type] = { control: control, position: position };
      }
    });
  });

  // -----------------------------------------------------------------------
  // deck_fit_bounds — fit map to geographic bounds
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_fit_bounds", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var bounds = payload.bounds;  // [[sw_lng, sw_lat], [ne_lng, ne_lat]]
    var opts = {};

    if (payload.padding != null) {
      opts.padding = payload.padding;
    }
    if (payload.maxZoom != null) {
      opts.maxZoom = payload.maxZoom;
    }
    if (payload.duration != null && payload.duration > 0) {
      opts.duration = payload.duration;
    } else {
      opts.duration = 0;  // instant
    }

    instance.map.fitBounds(bounds, opts);
  });

  // -----------------------------------------------------------------------
  // deck_add_source — add a native MapLibre source
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_add_source", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    whenStyleReady(instance.map, function() {
      var map = instance.map;
      var sourceId = payload.sourceId;
      var spec = payload.spec;

      // Remove existing source if present (along with its layers)
      if (map.getSource(sourceId)) {
        var style = map.getStyle();
        if (style && style.layers) {
          style.layers.forEach(function (l) {
            if (l.source === sourceId) {
              map.removeLayer(l.id);
            }
          });
        }
        map.removeSource(sourceId);
      }

      map.addSource(sourceId, spec);
    });
  });

  // -----------------------------------------------------------------------
  // deck_add_maplibre_layer — add a native MapLibre rendering layer
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_add_maplibre_layer", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    whenStyleReady(instance.map, function() {
      var map = instance.map;
      var layerSpec = payload.layerSpec;
      var beforeId = payload.beforeId || undefined;

      // Remove existing layer with same id
      if (map.getLayer(layerSpec.id)) {
        map.removeLayer(layerSpec.id);
      }

      map.addLayer(layerSpec, beforeId);
      instance.nativeLayers[layerSpec.id] = true;
    });
  });

  // -----------------------------------------------------------------------
  // deck_remove_maplibre_layer — remove a native MapLibre layer
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_remove_maplibre_layer", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    whenStyleReady(instance.map, function() {
      if (instance.map.getLayer(payload.layerId)) {
        instance.map.removeLayer(payload.layerId);
        delete instance.nativeLayers[payload.layerId];
      }
    });
  });

  // -----------------------------------------------------------------------
  // deck_remove_source — remove a native MapLibre source
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_remove_source", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    whenStyleReady(instance.map, function() {
      if (instance.map.getSource(payload.sourceId)) {
        instance.map.removeSource(payload.sourceId);
      }
    });
  });

  // -----------------------------------------------------------------------
  // deck_set_source_data — update GeoJSON source data
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_set_source_data", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    whenStyleReady(instance.map, function() {
      var source = instance.map.getSource(payload.sourceId);
      if (source && typeof source.setData === 'function') {
        source.setData(payload.data);
      }
    });
  });

  // -----------------------------------------------------------------------
  // deck_add_image — load a remote image into the map style for symbol layers
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_add_image", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;
    whenStyleReady(instance.map, function() {
      var map = instance.map;
      var imageId = payload.imageId;
      var url = payload.url;
      var options = {};
      if (payload.pixelRatio && payload.pixelRatio !== 1) {
        options.pixelRatio = payload.pixelRatio;
      }
      if (payload.sdf) {
        options.sdf = true;
      }

      // Remove existing image with same id to allow replacement
      if (map.hasImage(imageId)) {
        map.removeImage(imageId);
      }

      map.loadImage(url).then(function (result) {
        // MapLibre v5 loadImage returns { data: ImageBitmap | HTMLImageElement }
        var imgData = result && result.data ? result.data : result;
        if (!map.hasImage(imageId)) {
          map.addImage(imageId, imgData, options);
        }
      }).catch(function (err) {
        console.warn('[shiny_deckgl] Failed to load image "' + imageId + '":', err);
      });
    });
  });

  // -----------------------------------------------------------------------
  // deck_remove_image — remove a named image from the map style
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_remove_image", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;
    whenStyleReady(instance.map, function() {
      if (instance.map.hasImage(payload.imageId)) {
        instance.map.removeImage(payload.imageId);
      }
    });
  });

  // -----------------------------------------------------------------------
  // deck_has_image — check if image is loaded, report back via Shiny input
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_has_image", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;
    whenStyleReady(instance.map, function() {
      var exists = instance.map.hasImage(payload.imageId);
      Shiny.setInputValue(payload.id + '_has_image', {
        imageId: payload.imageId,
        exists: exists
      });
    });
  });

  // -----------------------------------------------------------------------
  // deck_set_paint_property — set paint property on a MapLibre layer
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_set_paint_property", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;
    whenStyleReady(instance.map, function() {
      instance.map.setPaintProperty(payload.layerId, payload.name, payload.value);
    });
  });

  // -----------------------------------------------------------------------
  // deck_set_layout_property — set layout property on a MapLibre layer
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_set_layout_property", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;
    whenStyleReady(instance.map, function() {
      instance.map.setLayoutProperty(payload.layerId, payload.name, payload.value);
    });
  });

  // -----------------------------------------------------------------------
  // deck_set_filter — set data-driven filter on a MapLibre layer
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_set_filter", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;
    whenStyleReady(instance.map, function() {
      instance.map.setFilter(payload.layerId, payload.filter || null);
    });
  });

  // -----------------------------------------------------------------------
  // deck_set_projection — switch between mercator and globe
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_set_projection", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    if (typeof instance.map.setProjection === 'function') {
      whenStyleReady(instance.map, function() {
        instance.map.setProjection({ type: payload.projection || 'mercator' });
      });
    } else {
      console.warn('[shiny_deckgl] setProjection requires MapLibre v4+');
    }
  });

  // -----------------------------------------------------------------------
  // deck_set_terrain — enable/disable 3D terrain
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_set_terrain", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    if (typeof instance.map.setTerrain === 'function') {
      whenStyleReady(instance.map, function() {
        instance.map.setTerrain(payload.terrain);
      });
    } else {
      console.warn('[shiny_deckgl] setTerrain requires MapLibre v4+');
    }
  });

  // -----------------------------------------------------------------------
  // deck_set_sky — atmosphere/sky properties
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_set_sky", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    if (typeof instance.map.setSky === 'function') {
      whenStyleReady(instance.map, function() {
        instance.map.setSky(payload.sky || {});
      });
    }
  });

  // -----------------------------------------------------------------------
  // deck_add_popup — attach click popup to a native MapLibre layer
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_add_popup", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var map = instance.map;
    var layerId = payload.layerId;
    var template = payload.template;

    // Store handler references for cleanup
    if (!instance.popupHandlers) instance.popupHandlers = {};

    // Remove existing handler for this layer
    if (instance.popupHandlers[layerId]) {
      map.off('click', layerId, instance.popupHandlers[layerId].click);
      map.off('mouseenter', layerId, instance.popupHandlers[layerId].enter);
      map.off('mouseleave', layerId, instance.popupHandlers[layerId].leave);
      delete instance.popupHandlers[layerId];
    }

    whenStyleReady(map, function() {
      var clickHandler = function (e) {
        if (!e.features || !e.features.length) return;
        var props = e.features[0].properties || {};
        var html = interpolateTemplate(template, props);

        var popupOpts = {
          closeButton: payload.closeButton !== false,
          closeOnClick: payload.closeOnClick !== false,
          maxWidth: payload.maxWidth || '300px'
        };
        if (payload.anchor) popupOpts.anchor = payload.anchor;

        new maplibregl.Popup(popupOpts)
          .setLngLat(e.lngLat)
          .setHTML(html)
          .addTo(map);

        // Also send click info to Shiny
        Shiny.setInputValue(payload.id + '_feature_click', {
          layerId: layerId,
          properties: props,
          longitude: e.lngLat.lng,
          latitude: e.lngLat.lat
        }, { priority: "event" });
      };

      var enterHandler = function () {
        map.getCanvas().style.cursor = 'pointer';
      };
      var leaveHandler = function () {
        map.getCanvas().style.cursor = '';
      };

      map.on('click', layerId, clickHandler);
      map.on('mouseenter', layerId, enterHandler);
      map.on('mouseleave', layerId, leaveHandler);

      instance.popupHandlers[layerId] = {
        click: clickHandler,
        enter: enterHandler,
        leave: leaveHandler
      };
    });
  });

  // -----------------------------------------------------------------------
  // deck_remove_popup — detach popup handler from a native layer
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_remove_popup", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance || !instance.popupHandlers) return;

    var layerId = payload.layerId;
    whenStyleReady(instance.map, function() {
      if (instance.popupHandlers[layerId]) {
        instance.map.off('click', layerId, instance.popupHandlers[layerId].click);
        instance.map.off('mouseenter', layerId, instance.popupHandlers[layerId].enter);
        instance.map.off('mouseleave', layerId, instance.popupHandlers[layerId].leave);
        delete instance.popupHandlers[layerId];
      }
    });
  });

  // -----------------------------------------------------------------------
  // deck_query_features — query rendered features and return to Shiny
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_query_features", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var map = instance.map;
    whenStyleReady(map, function() {
      var queryOpts = {};

      if (payload.layers) queryOpts.layers = payload.layers;
      if (payload.filter) queryOpts.filter = payload.filter;

      var features;
      if (payload.point) {
        features = map.queryRenderedFeatures(payload.point, queryOpts);
      } else if (payload.bounds) {
        features = map.queryRenderedFeatures(payload.bounds, queryOpts);
      } else {
        features = map.queryRenderedFeatures(queryOpts);
      }

      var simplified = features.map(function (f) {
        return {
          type: "Feature",
          geometry: f.geometry,
          properties: f.properties,
          layer: { id: f.layer ? f.layer.id : null },
          source: f.source || null
        };
      });

      Shiny.setInputValue(payload.id + '_query_result', {
        requestId: payload.requestId || 'default',
        features: simplified
      }, { priority: "event" });
    });
  });

  // -----------------------------------------------------------------------
  // deck_query_at_lnglat — project to pixels then query
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_query_at_lnglat", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var map = instance.map;
    whenStyleReady(map, function() {
      var point = map.project([payload.longitude, payload.latitude]);

      var queryOpts = {};
      if (payload.layers) queryOpts.layers = payload.layers;

      var features = map.queryRenderedFeatures(
        [point.x, point.y], queryOpts
      );

      var simplified = features.map(function (f) {
        return {
          type: "Feature",
          geometry: f.geometry,
          properties: f.properties,
          layer: { id: f.layer ? f.layer.id : null },
          source: f.source || null
        };
      });

      Shiny.setInputValue(payload.id + '_query_result', {
        requestId: payload.requestId || 'default',
        features: simplified
      }, { priority: "event" });
    });
  });

  // -----------------------------------------------------------------------
  // deck_add_marker — add or replace a named marker
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_add_marker", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    if (!instance.markers) instance.markers = {};
    var mapId = payload.id;

    // Remove existing marker with same id
    if (instance.markers[payload.markerId]) {
      instance.markers[payload.markerId].remove();
    }

    var marker = new maplibregl.Marker({
      color: payload.color || '#3FB1CE',
      draggable: payload.draggable || false
    }).setLngLat([payload.longitude, payload.latitude]);

    // Optional popup
    if (payload.popupHtml) {
      var popup = new maplibregl.Popup({ offset: 25 })
        .setHTML(payload.popupHtml);
      marker.setPopup(popup);
    }

    marker.addTo(instance.map);
    instance.markers[payload.markerId] = marker;

    // Click event → Shiny
    marker.getElement().addEventListener('click', function () {
      Shiny.setInputValue(mapId + '_marker_click', {
        markerId: payload.markerId,
        longitude: marker.getLngLat().lng,
        latitude: marker.getLngLat().lat
      }, { priority: "event" });
    });

    // Drag end event → Shiny
    if (payload.draggable) {
      marker.on('dragend', function () {
        var lngLat = marker.getLngLat();
        Shiny.setInputValue(mapId + '_marker_drag', {
          markerId: payload.markerId,
          longitude: lngLat.lng,
          latitude: lngLat.lat
        }, { priority: "event" });
      });
    }
  });

  // -----------------------------------------------------------------------
  // deck_remove_marker — remove a named marker
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_remove_marker", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance || !instance.markers) return;

    if (instance.markers[payload.markerId]) {
      instance.markers[payload.markerId].remove();
      delete instance.markers[payload.markerId];
    }
  });

  // -----------------------------------------------------------------------
  // deck_clear_markers — remove all named markers
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_clear_markers", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance || !instance.markers) return;

    Object.keys(instance.markers).forEach(function (mid) {
      instance.markers[mid].remove();
    });
    instance.markers = {};
  });

  // -----------------------------------------------------------------------
  // deck_enable_draw — add MapboxDraw to the map
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_enable_draw", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    if (typeof MapboxDraw === 'undefined') {
      console.warn('[shiny_deckgl] MapboxDraw not loaded. '
        + 'Include mapbox-gl-draw CDN in head_includes().');
      return;
    }

    whenStyleReady(instance.map, function() {
      // Remove existing draw control
      if (instance.draw) {
        instance.map.removeControl(instance.draw);
      }

      var drawOpts = {
        displayControlsDefault: false,
      };

      if (payload.controls) {
        drawOpts.controls = payload.controls;
      } else {
        var modes = payload.modes || ['draw_point', 'draw_line_string', 'draw_polygon'];
        drawOpts.controls = {
          point: modes.indexOf('draw_point') !== -1,
          line_string: modes.indexOf('draw_line_string') !== -1,
          polygon: modes.indexOf('draw_polygon') !== -1,
          trash: true
        };
      }

      var draw = new MapboxDraw(drawOpts);
      instance.map.addControl(draw, 'top-left');
      instance.draw = draw;

      if (payload.defaultMode && payload.defaultMode !== 'simple_select') {
        draw.changeMode(payload.defaultMode);
      }

      // Remove any previously-attached draw event listeners to prevent leaks
      if (instance._drawListeners) {
        instance.map.off('draw.create', instance._drawListeners.create);
        instance.map.off('draw.update', instance._drawListeners.update);
        instance.map.off('draw.delete', instance._drawListeners.del);
        instance.map.off('draw.modechange', instance._drawListeners.modechange);
      }

      var mapId = payload.id;
      function sendFeatures() {
        var fc = draw.getAll();
        Shiny.setInputValue(mapId + '_drawn_features', fc, { priority: "event" });
      }
      function onModeChange(e) {
        Shiny.setInputValue(mapId + '_draw_mode', e.mode);
      }

      instance.map.on('draw.create', sendFeatures);
      instance.map.on('draw.update', sendFeatures);
      instance.map.on('draw.delete', sendFeatures);
      instance.map.on('draw.modechange', onModeChange);

      instance._drawListeners = {
        create: sendFeatures,
        update: sendFeatures,
        del: sendFeatures,
        modechange: onModeChange,
      };
      instance._drawSendFeatures = sendFeatures;
    });
  });

  // -----------------------------------------------------------------------
  // deck_disable_draw — remove draw control
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_disable_draw", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance || !instance.draw) return;

    instance.map.removeControl(instance.draw);
    // Clean up draw event listeners
    if (instance._drawListeners) {
      instance.map.off('draw.create', instance._drawListeners.create);
      instance.map.off('draw.update', instance._drawListeners.update);
      instance.map.off('draw.delete', instance._drawListeners.del);
      instance.map.off('draw.modechange', instance._drawListeners.modechange);
      delete instance._drawListeners;
    }
    delete instance._drawSendFeatures;
    delete instance.draw;
  });

  // -----------------------------------------------------------------------
  // deck_get_drawn_features — request current features
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_get_drawn_features", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance || !instance.draw) return;

    var fc = instance.draw.getAll();
    Shiny.setInputValue(payload.id + '_drawn_features', fc, { priority: "event" });
  });

  // -----------------------------------------------------------------------
  // deck_delete_drawn — delete specific or all drawn features
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_delete_drawn", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance || !instance.draw) return;

    if (payload.featureIds) {
      instance.draw.delete(payload.featureIds);
    } else {
      instance.draw.deleteAll();
    }
    if (instance._drawSendFeatures) instance._drawSendFeatures();
  });

  // -----------------------------------------------------------------------
  // deck_set_feature_state
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_set_feature_state", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var target = { source: payload.sourceId, id: payload.featureId };
    if (payload.sourceLayer) target.sourceLayer = payload.sourceLayer;

    whenStyleReady(instance.map, function() {
      instance.map.setFeatureState(target, payload.state);
    });
  });

  // -----------------------------------------------------------------------
  // deck_remove_feature_state
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_remove_feature_state", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var target = { source: payload.sourceId };
    if (payload.featureId != null) target.id = payload.featureId;
    if (payload.sourceLayer) target.sourceLayer = payload.sourceLayer;

    whenStyleReady(instance.map, function() {
      if (payload.key) {
        instance.map.removeFeatureState(target, payload.key);
      } else {
        instance.map.removeFeatureState(target);
      }
    });
  });

  // -----------------------------------------------------------------------
  // deck_export_image — screenshot the map canvas
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_export_image", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var map = instance.map;
    var canvas = map.getCanvas();
    var mimeTypes = { jpeg: 'image/jpeg', png: 'image/png', webp: 'image/webp' };
    var format = mimeTypes[payload.format] || 'image/png';
    var quality = payload.quality || 0.92;

    // Wait for tiles to finish loading before capturing
    function capture() {
      var dataUrl = canvas.toDataURL(format, quality);
      Shiny.setInputValue(payload.id + '_export_result', {
        requestId: payload.requestId || 'default',
        dataUrl: dataUrl,
        width: canvas.width,
        height: canvas.height
      }, { priority: "event" });
    }

    map.triggerRepaint();
    if (map.isStyleLoaded && map.isStyleLoaded() && !map.isMoving()) {
      requestAnimationFrame(capture);
    } else {
      map.once('idle', function () {
        requestAnimationFrame(capture);
      });
    }
  });

  // -----------------------------------------------------------------------
  // deck_add_cluster_layer — convenience: GeoJSON source + cluster layers
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_add_cluster_layer", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    whenStyleReady(instance.map, function () {
      var map = instance.map;
      var srcId = payload.sourceId;
      var data = payload.data;
      var opts = payload.options || {};

      // Defaults
      var clusterRadius = opts.clusterRadius || 50;
      var clusterMaxZoom = opts.clusterMaxZoom || 14;

      var clusterColor = opts.clusterColor || "#51bbd6";
      var clusterStrokeColor = opts.clusterStrokeColor || "#ffffff";
      var clusterStrokeWidth = opts.clusterStrokeWidth || 1;
      var clusterTextColor = opts.clusterTextColor || "#ffffff";
      var clusterTextSize = opts.clusterTextSize || 12;

      var pointColor = opts.pointColor || "#11b4da";
      var pointRadius = opts.pointRadius || 5;
      var pointStrokeColor = opts.pointStrokeColor || "#ffffff";
      var pointStrokeWidth = opts.pointStrokeWidth || 1;

      // Size steps: [count, radius] pairs for interpolation
      var sizeSteps = opts.sizeSteps || [
        [0, 18], [100, 24], [750, 32]
      ];

      // Build circle-radius stops array for step expression
      var radiusStops = ["step", ["get", "point_count"]];
      for (var i = 0; i < sizeSteps.length; i++) {
        if (i === 0) {
          radiusStops.push(sizeSteps[i][1]);  // default value
        } else {
          radiusStops.push(sizeSteps[i][0]);   // threshold
          radiusStops.push(sizeSteps[i][1]);   // radius
        }
      }

      // Clean up existing layers & source
      var layerIds = [srcId + "-clusters", srcId + "-count", srcId + "-unclustered"];
      layerIds.forEach(function (lid) {
        if (map.getLayer(lid)) map.removeLayer(lid);
      });
      if (map.getSource(srcId)) map.removeSource(srcId);

      // Add source
      var sourceSpec = {
        type: "geojson",
        data: data,
        cluster: true,
        clusterRadius: clusterRadius,
        clusterMaxZoom: clusterMaxZoom
      };
      if (opts.clusterProperties) {
        sourceSpec.clusterProperties = opts.clusterProperties;
      }
      map.addSource(srcId, sourceSpec);

      // Cluster circles
      map.addLayer({
        id: srcId + "-clusters",
        type: "circle",
        source: srcId,
        filter: ["has", "point_count"],
        paint: {
          "circle-color": clusterColor,
          "circle-radius": radiusStops,
          "circle-stroke-color": clusterStrokeColor,
          "circle-stroke-width": clusterStrokeWidth
        }
      });

      // Cluster count labels
      map.addLayer({
        id: srcId + "-count",
        type: "symbol",
        source: srcId,
        filter: ["has", "point_count"],
        layout: {
          "text-field": ["get", "point_count_abbreviated"],
          "text-size": clusterTextSize
        },
        paint: {
          "text-color": clusterTextColor
        }
      });

      // Unclustered points
      map.addLayer({
        id: srcId + "-unclustered",
        type: "circle",
        source: srcId,
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-color": pointColor,
          "circle-radius": pointRadius,
          "circle-stroke-color": pointStrokeColor,
          "circle-stroke-width": pointStrokeWidth
        }
      });

      // Track native layers
      layerIds.forEach(function (lid) {
        instance.nativeLayers[lid] = true;
      });

      // Click-to-zoom on cluster circles
      map.on("click", srcId + "-clusters", function (e) {
        var features = map.queryRenderedFeatures(e.point, {
          layers: [srcId + "-clusters"]
        });
        if (!features.length) return;
        var clusterId = features[0].properties.cluster_id;
        map.getSource(srcId).getClusterExpansionZoom(clusterId)
          .then(function (zoom) {
            map.easeTo({
              center: features[0].geometry.coordinates,
              zoom: zoom
            });
          });
      });

      // Pointer cursor on clusters
      map.on("mouseenter", srcId + "-clusters", function () {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", srcId + "-clusters", function () {
        map.getCanvas().style.cursor = "";
      });
    });
  });

  // -----------------------------------------------------------------------
  // deck_remove_cluster_layer — remove cluster source + all its layers
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_remove_cluster_layer", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    whenStyleReady(instance.map, function () {
      var map = instance.map;
      var srcId = payload.sourceId;
      var layerIds = [srcId + "-clusters", srcId + "-count", srcId + "-unclustered"];
      layerIds.forEach(function (lid) {
        if (map.getLayer(lid)) {
          map.removeLayer(lid);
          delete instance.nativeLayers[lid];
        }
      });
      if (map.getSource(srcId)) {
        map.removeSource(srcId);
      }
    });
  });

  // -----------------------------------------------------------------------
  // Tab visibility: resize maps when a Bootstrap tab becomes visible
  // -----------------------------------------------------------------------
  document.addEventListener('shown.bs.tab', function (event) {
    var href = event.target.getAttribute('data-bs-target')
            || event.target.getAttribute('href');
    if (!href) return;
    var panel;
    try { panel = document.querySelector(href); } catch (e) { return; }
    if (!panel) return;
    panel.querySelectorAll('.deckgl-map').forEach(function (el) {
      var inst = mapInstances[el.id];
      if (inst && inst.map) {
        setTimeout(function () {
          inst.map.resize();
          // Re-apply current layers to force deck.gl re-render
          if (inst.overlay && inst.lastLayers && inst.lastLayers.length) {
            var deckLayers = buildDeckLayers(
              JSON.parse(JSON.stringify(inst.lastLayers)),
              el.id,
              inst.tooltipConfig
            );
            inst.overlay.setProps({ layers: deckLayers });
            inst.map.triggerRepaint();
          }
        }, 50);
      }
    });
  });

  // -----------------------------------------------------------------------
  // deck_update_tooltip — change tooltip config and re-render layers
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_update_tooltip", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;
    instance.tooltipConfig = payload.tooltip || null;

    // Re-render existing layers so the new tooltip config takes effect
    // immediately (onHover closures capture tooltipConfig at build time).
    if (instance.lastLayers && instance.lastLayers.length > 0) {
      var deckLayers = buildDeckLayers(
        instance.lastLayers.map(function (lp) { return Object.assign({}, lp); }),
        payload.id,
        instance.tooltipConfig
      );
      instance.overlay.setProps({ layers: deckLayers });
      instance.map.triggerRepaint();
    }
  });

  // Expose helpers for standalone HTML exports
  window.__deckgl_initMap = initMap;
  window.__deckgl_buildDeckLayers = buildDeckLayers;
  window.__deckgl_buildEffects = buildEffects;
})();
