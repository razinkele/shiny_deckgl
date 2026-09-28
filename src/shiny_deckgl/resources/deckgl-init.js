(function () {
  // Store map instances by ID
  // Exposed on window for standalone HTML exports
  const mapInstances = window.__deckgl_instances = {};

  // Clone an array of layer-props objects.  Uses shallow Object.assign
  // plus targeted deep-cloning of mutable nested objects (transitions,
  // updateTriggers).  Handles non-cloneable values like Canvas elements
  // (from rasterised SVG icon atlases) that structuredClone cannot copy.
  function cloneLayersData(layersData) {
    return layersData.map(cloneLayer);
  }

  function cloneLayer(lp) {
    {
      var clone = Object.assign({}, lp);
      // Deep-clone nested objects that buildDeckLayers mutates in-place.
      // transitions needs two levels: the map of prop→spec AND each spec
      // object (buildDeckLayers writes tSpec.easing and deletes @@easing).
      if (clone.transitions) {
        var src = clone.transitions;
        var t = {};
        for (var k in src) {
          t[k] = (src[k] && typeof src[k] === 'object') ? Object.assign({}, src[k]) : src[k];
        }
        clone.transitions = t;
      }
      if (clone.updateTriggers) clone.updateTriggers = Object.assign({}, clone.updateTriggers);
      // Deep-clone @@binary attribute markers so resolveBinaryAttributes'
      // delete + decode doesn't destroy the cached originals.
      // Also deep-clone the data object which gets mutated (data.attributes).
      for (var key in clone) {
        var val = clone[key];
        if (val && typeof val === 'object' && val['@@binary']) {
          clone[key] = Object.assign({}, val);
        }
      }
      // Only deep-clone data when it's a binary-transport object (not a plain array).
      // Object.assign({}, array) would destroy the array prototype.
      if (clone.data && typeof clone.data === 'object' && !Array.isArray(clone.data)) {
        clone.data = Object.assign({}, clone.data);
        if (clone.data.attributes) {
          clone.data.attributes = Object.assign({}, clone.data.attributes);
        }
        if (clone.data.startIndices && Array.isArray(clone.data.startIndices)) {
          clone.data.startIndices = clone.data.startIndices.slice();
        }
      }
      return clone;
    }
  }

  // -----------------------------------------------------------------------
  // Tooltip helper
  // -----------------------------------------------------------------------
  function getOrCreateTooltipEl(mapId) {
    let el = document.getElementById(mapId + '__tooltip');
    if (el) return el;
    const container = document.getElementById(mapId);
    if (!container) return null;
    el = document.createElement('div');
    el.id = mapId + '__tooltip';
    el.className = 'deckgl-tooltip';
    container.style.position = 'relative';
    container.appendChild(el);
    return el;
  }

  // HTML-escape a string to prevent XSS when interpolating user data into tooltips
  function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Sanitize HTML via DOM parsing — defence-in-depth for popup_html and
  // interpolated popup templates.  Uses DOMParser so the browser's own HTML
  // parser handles edge cases (unclosed tags, nested scripts, entity encoding).
  // Fail-closed: returns '' on any error rather than passing input through.
  // SVG animation elements are stripped because they can rewrite an href to
  // javascript: after sanitising; <math> because its parsing quirks are the
  // usual source of mutation-XSS.
  var SANITIZE_STRIP_TAGS = /^(script|style|iframe|object|embed|applet|form|base|meta|link|template|noscript|math|animate|animatemotion|animatetransform|set)$/i;
  var SANITIZE_STRIP_ATTRS = /^on/i;
  // Browsers strip TAB/LF/CR from anywhere in a URL and leading C0 controls
  // before parsing the scheme, so a TAB inside the scheme word, or a leading
  // control byte, both slip past a plain /javascript:/ regex yet still
  // execute. Normalise the same way the URL parser does, then compare the
  // scheme exactly -- a substring regex over the raw value is bypassable.
  var SANITIZE_URI_SCHEME = /^([a-zA-Z][a-zA-Z0-9+.-]*):/;
  var SANITIZE_DANGEROUS_SCHEMES = new Set(['javascript', 'vbscript']);
  // `data:` is only inert for raster images. A data:text/html (or SVG, which
  // runs its own script and event handlers) navigated to from href executes
  // just like javascript:, so everything outside this allowlist is blocked.
  var SANITIZE_DATA_URI_SAFE = /^data:image\/(png|jpe?g|gif|webp|bmp|avif|x-icon|vnd\.microsoft\.icon)\s*[;,]/i;

  function isDangerousUri(value) {
    if (value == null) return false;
    var normalized = String(value).replace(/[\t\n\r]/g, '').replace(/^[\x00-\x20]+/, '');
    var m = SANITIZE_URI_SCHEME.exec(normalized);
    if (!m) return false;  // relative or scheme-less: cannot be javascript:
    var scheme = m[1].toLowerCase();
    if (scheme === 'data') return !SANITIZE_DATA_URI_SAFE.test(normalized);
    return SANITIZE_DANGEROUS_SCHEMES.has(scheme);
  }
  var SANITIZE_URI_ATTRS = new Set(['href', 'src', 'action', 'formaction', 'srcdoc', 'data', 'xlink:href']);

  function sanitizeHtml(html) {
    if (!html) return '';
    // Serialising and re-parsing can change a DOM (mutation XSS), so the
    // markup handed to innerHTML must itself come through a pass unchanged.
    var out = String(html);
    for (var pass = 0; pass < 4; pass++) {
      var next = sanitizeHtmlOnce(out);
      if (next === out) return out;
      out = next;
    }
    console.error('[shiny_deckgl] sanitizeHtml output did not stabilise, blocking output');
    return '';
  }

  function sanitizeHtmlOnce(html) {
    try {
      var doc = new DOMParser().parseFromString(html, 'text/html');
      // Walk all elements and remove dangerous ones
      var all = doc.body.querySelectorAll('*');
      for (var i = all.length - 1; i >= 0; i--) {
        var el = all[i];
        if (SANITIZE_STRIP_TAGS.test(el.tagName)) {
          el.remove();
          continue;
        }
        // Remove dangerous attributes
        for (var j = el.attributes.length - 1; j >= 0; j--) {
          var attr = el.attributes[j];
          if (SANITIZE_STRIP_ATTRS.test(attr.name)) {
            el.removeAttribute(attr.name);
          } else if (SANITIZE_URI_ATTRS.has(attr.name.toLowerCase()) &&
                     isDangerousUri(attr.value)) {
            el.removeAttribute(attr.name);
          }
        }
      }
      return doc.body.innerHTML;
    } catch (e) {
      console.error('[shiny_deckgl] sanitizeHtml failed, blocking output:', e);
      return '';
    }
  }

  function interpolateTemplate(template, obj) {
    if (!template || !obj) return '';
    return template.replace(/\{([\w-]+(?:\.[\w-]+)*)\}/g, function (_match, path) {
      let val = obj;
      for (const key of path.split('.')) {
        if (val == null) return '';
        val = val[key];
      }
      // HTML-escape interpolated values to prevent XSS attacks
      return escapeHtml(val);
    });
  }

  // -----------------------------------------------------------------------
  // DeckLayerLegendWidget — deck.gl widget version of the layer legend
  //
  // Implements the deck.gl Widget interface (onAdd / onRemove / setProps)
  // so it can be passed in the widgets array alongside ZoomWidget, etc.
  // Styled by the .deck-legend-* classes in styles.css.
  // -----------------------------------------------------------------------
  // DeckLayerLegendWidget is created lazily via createDeckLayerLegendWidget()
  // because deck.Widget may not be available when this script first loads.
  var _DeckLayerLegendWidgetClass = null;
  var LEGEND_DEFAULTS = {
    entries: [], showCheckbox: true, collapsed: false, title: null,
    autoIntrospect: false, excludeLayers: [], labelMap: {}, includeHidden: false,
  };

  function createDeckLayerLegendWidget(props) {
    if (!_DeckLayerLegendWidgetClass) {
      var Base = (typeof deck !== 'undefined' && deck.Widget) ? deck.Widget : null;

      if (Base) {
        // deck.gl >= 9.x: extend the real Widget base class
        _DeckLayerLegendWidgetClass = class extends Base {
          constructor(p) {
            super(p);
            this._initLegend(p);
          }
        };
      } else {
        // Fallback: plain constructor (shouldn't happen with deck.gl 9.2)
        _DeckLayerLegendWidgetClass = function (p) {
          this.id = (p && p.id) || 'deck-layer-legend';
          this.placement = (p && p.placement) || 'top-left';
          this.viewId = (p && p.viewId) || null;
          this._initLegend(p);
        };
      }

      var proto = _DeckLayerLegendWidgetClass.prototype;

      proto._initLegend = function (p) {
        this.id = (p && p.id) || 'deck-layer-legend';
        this.placement = (p && p.placement) || 'top-left';
        this.viewId = (p && p.viewId) || null;
        this._legendProps = Object.assign({}, LEGEND_DEFAULTS, p);
        this._mapId = null;
        this._rootEl = null;
        // Collapse state set by the user's clicks. It survives re-renders and
        // is only reset when the `collapsed` prop itself changes.
        this._collapsedProp = this._legendProps.collapsed;
        this._collapsed = !!this._collapsedProp;
      };

      proto.onRemove = function () {
        var inst = this._mapId ? mapInstances[this._mapId] : null;
        if (inst && inst._legendWidget === this) inst._legendWidget = null;
        this._mapId = null;
        this._rootEl = null;
      };

      proto.onRenderHTML = function (el) {
        el.classList.add('deck-legend-ctrl', 'deck-layer-legend-widget');
        // Lift bottom-placed widgets above the MapLibre attribution bar
        if (this.placement && this.placement.startsWith('bottom')) {
          el.style.marginBottom = '34px';
        }
        this._rootEl = el;
        // Sync _legendProps from this.props (kept updated by base setProps)
        if (this.props) {
          this._legendProps = Object.assign({}, LEGEND_DEFAULTS, this.props);
        }
        if (this._legendProps.collapsed !== this._collapsedProp) {
          this._collapsedProp = this._legendProps.collapsed;
          this._collapsed = !!this._collapsedProp;
        }
        this._resolveMapId();
        // Register this widget on the mapInstance for refresh callbacks
        if (this._mapId && mapInstances[this._mapId]) {
          mapInstances[this._mapId]._legendWidget = this;
        }
        this._renderInto(el);
      };

      proto._resolveMapId = function () {
        if (this._mapId) return;
        // Find which mapInstance owns this deck overlay
        if (this.deck) {
          for (var id of Object.keys(mapInstances)) {
            var inst = mapInstances[id];
            if (inst.overlay === this.deck || inst.overlay._deck === this.deck) {
              this._mapId = id;
              return;
            }
          }
        }
      };

      proto._renderInto = function (container) {
        var opts = this._legendProps;
        container.innerHTML = '';

        // Auto-introspect if enabled and no manual entries provided
        var entries = opts.entries && opts.entries.length > 0
          ? opts.entries
          : (opts.autoIntrospect ? this._introspectLayers() : []);

        var self = this;
        var body = document.createElement('div');
        body.className = 'deck-legend-body';

        // The header is the only way to expand the panel, so a collapsed
        // legend always gets one, titled "Layers" when no title was given.
        if (opts.title || opts.collapsed) {
          var header = document.createElement('button');
          header.type = 'button';
          header.className = 'deck-legend-header';
          header.setAttribute('aria-label', 'Toggle legend');
          var titleEl = document.createElement('span');
          titleEl.className = 'deck-legend-title';
          titleEl.textContent = opts.title || 'Layers';
          var arrow = document.createElement('span');
          arrow.className = 'deck-legend-arrow';
          var syncCollapsed = function () {
            body.style.display = self._collapsed ? 'none' : '';
            arrow.textContent = self._collapsed ? '\u25B6' : '\u25BC';
            header.setAttribute('aria-expanded', String(!self._collapsed));
          };
          header.addEventListener('click', function () {
            self._collapsed = !self._collapsed;
            syncCollapsed();
          });
          header.appendChild(titleEl);
          header.appendChild(arrow);
          container.appendChild(header);
          syncCollapsed();
        } else {
          this._collapsed = false;
        }

        for (var i = 0; i < entries.length; i++) {
          var entry = entries[i];
          var row = document.createElement('label');
          row.className = 'deck-legend-row';

          if (opts.showCheckbox && entry.layer_id) {
            var cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.checked = this._isLayerVisible(entry.layer_id);
            cb.className = 'deck-legend-cb';
            (function (layerId) {
              cb.addEventListener('change', function () {
                self._toggleLayer(layerId, this.checked);
              });
            })(entry.layer_id);
            row.appendChild(cb);
          }

          row.appendChild(this._createSwatch(entry));

          var lbl = document.createElement('span');
          lbl.className = 'deck-legend-label';
          lbl.textContent = entry.label || entry.layer_id || '';
          row.appendChild(lbl);

          body.appendChild(row);
        }
        container.appendChild(body);
      };

      // Layer type → swatch shape mapping
      var TYPE_SHAPE = {
        // Points / markers
        ScatterplotLayer: 'circle', GeoJsonLayer: 'circle',
        IconLayer: 'circle', PointCloudLayer: 'circle', TextLayer: 'circle',
        // Arcs
        ArcLayer: 'arc', GreatCircleLayer: 'arc',
        // Lines / paths
        PathLayer: 'line', LineLayer: 'line', TripsLayer: 'line',
        // Polygons / columns / cells
        ColumnLayer: 'rect', GridCellLayer: 'rect',
        H3HexagonLayer: 'rect', H3ClusterLayer: 'rect',
        PolygonLayer: 'rect', SolidPolygonLayer: 'rect', BitmapLayer: 'rect',
        // Geo-index layers
        A5Layer: 'rect', GeohashLayer: 'rect', QuadkeyLayer: 'rect', S2Layer: 'rect',
        // Aggregation layers colour by a ramp, not a single colour
        HeatmapLayer: 'gradient', ContourLayer: 'gradient', ScreenGridLayer: 'gradient',
        HexagonLayer: 'gradient', GridLayer: 'gradient',
        // Tile / raster / 3D
        TileLayer: 'rect', MVTLayer: 'rect', Tile3DLayer: 'rect',
        WMSLayer: 'rect', TerrainLayer: 'rect',
        // Mesh / scene
        SimpleMeshLayer: 'rect', ScenegraphLayer: 'rect',
      };

      // deck.gl's default colorRange (ColorBrewer YlOrRd, 6 classes): what the
      // aggregation layers draw when they are given none.
      var DECK_DEFAULT_COLOR_RANGE = [
        [255, 255, 178], [254, 217, 118], [254, 178, 76],
        [253, 141, 60], [240, 59, 32], [189, 0, 38],
      ];

      // "@@d.a.b" / "@@=d.a.b": a colour read straight from a field of the row.
      var ACCESSOR_PATH_RE = /^@@=?\s*d((?:\s*\.\s*[A-Za-z_$][A-Za-z0-9_$]*)+)\s*$/;

      // Fallback colors for layer types where color props aren't statically extractable
      var LAYER_TYPE_DEFAULT_COLOR = {
        IconLayer: [60, 60, 60],          // dark grey (icons are image-based)
        TileLayer: [100, 140, 180],       // slate
        Tile3DLayer: [100, 140, 180],
        TerrainLayer: [120, 160, 100],    // earthy green
        WMSLayer: [100, 140, 180],        // slate
      };

      proto._introspectLayers = function () {
        if (!this._mapId) return [];
        var inst = mapInstances[this._mapId];
        if (!inst || !inst.lastLayers) return [];
        var exclude = this._legendProps.excludeLayers || [];
        var labelMap = this._legendProps.labelMap || {};
        var includeHidden = !!this._legendProps.includeHidden;
        // Layers the user unticked here stay listed (unchecked), or they could
        // never be ticked again. Layers the server hid are left out unless
        // includeHidden is set.
        var userHidden = inst._legendUserHidden || {};
        var entries = [];
        for (var i = 0; i < inst.lastLayers.length; i++) {
          var lp = inst.lastLayers[i];
          if (!lp || !lp.id) continue;
          if (lp.visible !== false) {
            delete userHidden[lp.id];
          } else if (!includeHidden && !userHidden[lp.id]) {
            continue;
          }
          if (exclude.indexOf(lp.id) >= 0) continue;
          var entry = this._extractEntry(lp, labelMap);
          if (entry) entries.push(entry);
        }
        return entries;
      };

      proto._extractEntry = function (lp, labelMap) {
        var layerType = lp.type || lp['@@type'] || '';
        // Strip module prefix (e.g. "HexagonLayer" from "@deck.gl/aggregation-layers/HexagonLayer")
        var shortType = layerType.split('/').pop() || layerType;
        var shape = TYPE_SHAPE[shortType] || 'circle';
        // GeoJSON can hold points, lines or polygons: use the first feature's.
        if (shortType === 'GeoJsonLayer') {
          var f = this._firstDatum(lp);
          var g = f && f.geometry && f.geometry.type;
          if (/LineString$/.test(g || '')) shape = 'line';
          else if (/Polygon$/.test(g || '')) shape = 'rect';
        }
        var label = (labelMap && labelMap[lp.id]) || lp.id;
        var entry = { layer_id: lp.id, label: label, shape: shape };

        // Color extraction priority chain
        // 1. Aggregation layers colour by a ramp: their contours' colours,
        //    their colorRange, or deck.gl's default ramp.
        if (shape === 'gradient') {
          entry.colors = (shortType === 'ContourLayer' && this._contourColors(lp.contours))
            || this._resolveColorRange(lp.colorRange)
            || DECK_DEFAULT_COLOR_RANGE;
          return entry;
        }
        // 2. Arc shapes use source/target color pair
        if (shape === 'arc') {
          var src = this._colorOf(lp, lp.getSourceColor);
          var tgt = this._colorOf(lp, lp.getTargetColor);
          if (src && tgt) {
            entry.color = src;
            entry.color2 = tgt;
            return entry;
          }
        }
        // 3. Standard color props: getFillColor → getColor → getLineColor,
        //    each a constant or read through its own accessor path.
        var color = this._colorOf(lp, lp.getFillColor)
                 || this._colorOf(lp, lp.getColor)
                 || this._colorOf(lp, lp.getLineColor);
        // 4. No colour accessor at all: try the usual field names. Not when
        //    an accessor exists but can't be read -- a `color` field it
        //    doesn't use would give the wrong swatch.
        if (!color && lp.getFillColor == null && lp.getColor == null && lp.getLineColor == null) {
          color = this._sampleDataColor(lp);
        }
        // 5. Types whose colour comes from images or tiles
        if (!color) {
          color = LAYER_TYPE_DEFAULT_COLOR[shortType] || null;
        }
        entry.color = color || [150, 150, 150];
        return entry;
      };

      // A colour prop's swatch value: a constant, or the field its accessor
      // path reads, taken from the first row.
      proto._colorOf = function (lp, val) {
        var c = this._resolveColor(val);
        if (c) return c;
        if (typeof val !== 'string') return null;
        var m = ACCESSOR_PATH_RE.exec(val);
        if (!m) return null;
        var v = this._firstDatum(lp);
        var keys = m[1].split('.');
        for (var i = 0; i < keys.length && v != null; i++) {
          var k = keys[i].trim();
          if (k) v = v[k];
        }
        return this._toColor(v);
      };

      proto._firstDatum = function (lp) {
        var data = lp.data;
        if (!data) return null;
        if (Array.isArray(data)) return data[0] || null;
        // GeoJSON: accessors receive each feature
        if (Array.isArray(data.features)) return data.features[0] || null;
        return null;
      };

      proto._toColor = function (c) {
        if (Array.isArray(c) && c.length >= 3 && typeof c[0] === 'number') return c;
        if (typeof c === 'string' && c.charAt(0) === '[') {
          try {
            var p = JSON.parse(c);
            if (Array.isArray(p) && p.length >= 3 && typeof p[0] === 'number') return p;
          } catch (e) { console.debug('[shiny_deckgl] legend: data color parse failed:', e.message); }
        }
        return null;
      };

      proto._contourColors = function (contours) {
        if (!Array.isArray(contours)) return null;
        var out = [];
        for (var i = 0; i < contours.length; i++) {
          var c = contours[i] && this._toColor(contours[i].color);
          if (c) out.push(c);
        }
        return out.length ? out : null;
      };

      proto._resolveColor = function (val) {
        if (!val) return null;
        // Static array like [255, 0, 0] or [255, 0, 0, 200]
        if (Array.isArray(val) && val.length >= 3 && typeof val[0] === 'number') {
          return val;
        }
        if (typeof val === 'string') {
          // @@= accessor string — can't resolve statically
          if (val.charAt(0) === '@') return null;
          // Try parsing JSON-encoded array (e.g. "[255,0,0]")
          if (val.charAt(0) === '[') {
            try {
              var parsed = JSON.parse(val);
              if (Array.isArray(parsed) && parsed.length >= 3 && typeof parsed[0] === 'number') {
                return parsed;
              }
            } catch (e) { console.debug('[shiny_deckgl] legend: color parse failed:', e.message); }
          }
          // CSS color string
          return val;
        }
        return null;
      };

      proto._resolveColorRange = function (val) {
        if (!val) return null;
        // Already a nested array [[r,g,b], ...]
        if (Array.isArray(val) && val.length > 0 && Array.isArray(val[0])) return val;
        // JSON-encoded nested array
        if (typeof val === 'string' && val.charAt(0) === '[') {
          try {
            var parsed = JSON.parse(val);
            if (Array.isArray(parsed) && parsed.length > 0 && Array.isArray(parsed[0])) {
              return parsed;
            }
          } catch (e) { console.debug('[shiny_deckgl] legend: colorRange parse failed:', e.message); }
        }
        return null;
      };

      // No colour accessor was given: try the usual field names on the first row.
      proto._sampleDataColor = function (lp) {
        var d = this._firstDatum(lp);
        if (!d) return null;
        return this._toColor(d.color || d.sourceColor || d.fillColor);
      };

      proto._refresh = function () {
        if (!this._rootEl) return;
        this._resolveMapId();
        this._renderInto(this._rootEl);
      };

      proto._toCSS = function (c) {
        if (!c) return '#666';
        if (typeof c === 'string') return c;
        if (Array.isArray(c)) {
          if (c.length >= 4) return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + (c[3] / 255) + ')';
          return 'rgb(' + c[0] + ',' + c[1] + ',' + c[2] + ')';
        }
        return '#666';
      };

      proto._createSwatch = function (entry) {
        var shape = entry.shape || 'circle';
        var el = document.createElement('span');
        el.className = 'deck-legend-swatch deck-legend-sh-' + shape;
        if (shape === 'arc' && entry.color2) {
          el.style.background = 'linear-gradient(90deg,' + this._toCSS(entry.color) + ',' + this._toCSS(entry.color2) + ')';
        } else if (shape === 'gradient' && Array.isArray(entry.colors)) {
          el.style.background = 'linear-gradient(90deg,' + entry.colors.map(function (c2) { return proto._toCSS(c2); }).join(',') + ')';
        } else {
          el.style.backgroundColor = this._toCSS(entry.color);
        }
        return el;
      };

      proto._isLayerVisible = function (layerId) {
        if (!this._mapId) return true;
        var inst = mapInstances[this._mapId];
        if (!inst) return true;
        var lp = inst.lastLayers.find(function (l) { return l.id === layerId; });
        return lp ? lp.visible !== false : true;
      };

      proto._toggleLayer = function (layerId, visible) {
        if (!this._mapId) return;
        var inst = mapInstances[this._mapId];
        if (!inst) return;
        inst.lastLayers = inst.lastLayers.map(function (lp) {
          if (lp.id !== layerId) return lp;
          return Object.assign({}, lp, { visible: visible });
        });
        if (!inst._legendUserHidden) inst._legendUserHidden = {};
        if (visible) delete inst._legendUserHidden[layerId];
        else inst._legendUserHidden[layerId] = true;
        renderNow(inst, this._mapId);
        // Report the toggle so the server can keep its own state in step;
        // otherwise its next update() would silently undo the user's choice.
        Shiny.setInputValue(this._mapId + '_legend_visibility',
          { layer_id: layerId, visible: visible }, { priority: 'event' });
      };
    }

    return new _DeckLayerLegendWidgetClass(props);
  }

  // -----------------------------------------------------------------------
  // Map interaction ("controller").
  //
  // Under MapLibreOverlay, MapLibre does the panning and zooming, so deck.gl's
  // `controller` prop has no effect: map the value onto MapLibre's handlers.
  // true = everything on, false = everything off, a dict (deck.gl controller
  // option names) = everything on except the options set to false.
  // -----------------------------------------------------------------------
  var CONTROLLER_HANDLERS = {
    dragPan: 'dragPan', scrollZoom: 'scrollZoom', dragRotate: 'dragRotate',
    doubleClickZoom: 'doubleClickZoom', keyboard: 'keyboard', boxZoom: 'boxZoom',
  };

  // data-map-options: extra MapLibre Map constructor options (maxBounds,
  // maxPitch, renderWorldCopies, antialias, ...). They win over the
  // view-state-derived defaults; container and style stay pinned.
  function mergeMapOptions(base, el) {
    var raw = el && el.dataset ? el.dataset.mapOptions : undefined;
    if (!raw) return Object.assign({}, base);
    var extra;
    try { extra = JSON.parse(raw); } catch (e) {
      console.warn('[shiny_deckgl] Ignoring malformed data-map-options:', e.message);
      return Object.assign({}, base);
    }
    var out = Object.assign({}, base, extra);
    out.container = base.container;
    out.style = base.style;
    return out;
  }

  // deck.gl 9.4's MapLibre integration reads map.getProjection().type on
  // every render and throws ("Unsupported MapLibre projection") for anything
  // but 'mercator' or 'globe' -- e.g. a style whose projection is a zoom
  // expression or 'vertical-perspective'. Normalise to the nearest supported
  // preset so deck keeps syncing. Returns the type in force afterwards.
  function normaliseProjection(map) {
    var p = map.getProjection && map.getProjection();
    var t = p && p.type;
    if (t == null || t === 'mercator' || t === 'globe') return t;
    var globe = Array.isArray(t) || t === 'vertical-perspective';
    var next = globe ? 'globe' : 'mercator';
    console.warn('[shiny_deckgl] deck.gl 9.4 supports only mercator/globe projections; ' +
      'normalising ' + JSON.stringify(t) + ' to ' + next);
    map.setProjection({ type: next });
    return next;
  }

  // ZoomWidget/CompassWidget default to top-right, where our default MapLibre
  // NavigationControl sits; MapLibre's control is the later sibling, so it
  // paints over the deck widget and takes its clicks. When the app never
  // chose controls (the navigation control is only our default), drop it in
  // favour of the widgets that replace it.
  var NAV_REPLACING_WIDGETS = /^_?(Zoom|Compass)Widget$/;
  function dropImplicitNavigation(instance, widgetSpecs) {
    if (!instance || !instance._implicitNavigation || !widgetSpecs) return false;
    var nav = instance.controls && instance.controls.navigation;
    if (!nav) return false;
    var replaces = widgetSpecs.some(function (s) {
      return !!s && NAV_REPLACING_WIDGETS.test(s['@@widgetClass'] || '');
    });
    if (!replaces) return false;
    try { instance.map.removeControl(nav.control); } catch (e) { /* already gone */ }
    delete instance.controls.navigation;
    return true;
  }

  // map.setStyle(style, {diff: true}) applies the diff in place and fires no
  // 'style.load' (only the setState-failed fallback does), so the guard that
  // deck_set_style raises would stay up until its 30 s timeout and stall every
  // whenStyleReady() caller (add_source, add_maplibre_layer, popups, ...).
  // Settle it: synchronously for a style object (the diff already ran inside
  // setStyle), on the next 'styledata' for a URL (fired once the fetched diff
  // is applied). Idempotent, so the fallback's 'style.load' handler and the
  // timeout can still run without harm.
  function settleDiffStyle(instance, style) {
    var done = function () {
      if (!instance.map._deckStyleChanging) return;
      if (instance._styleChangeTimeout) {
        clearTimeout(instance._styleChangeTimeout);
        instance._styleChangeTimeout = null;
      }
      if (instance._styleLoadHandler) {
        instance.map.off('style.load', instance._styleLoadHandler);
        instance._styleLoadHandler = null;
      }
      instance.map._deckStyleChanging = false;
      if (instance.map._deckStyleDrainFn) instance.map._deckStyleDrainFn();
    };
    if (style && typeof style === 'object') done();
    else instance.map.once('styledata', done);
  }

  function applyController(map, value) {
    var opts = (value && typeof value === 'object') ? value : null;
    var on = value !== false;
    Object.keys(CONTROLLER_HANDLERS).forEach(function (key) {
      var h = map[CONTROLLER_HANDLERS[key]];
      if (!h) return;
      var enable = on && !(opts && opts[key] === false);
      if (enable) h.enable(); else h.disable();
    });
    var tzr = map.touchZoomRotate;
    if (tzr) {
      var touchZoom = on && !(opts && opts.touchZoom === false);
      var touchRotate = on && !(opts && opts.touchRotate === false);
      if (touchZoom || touchRotate) tzr.enable(); else tzr.disable();
      if (touchRotate) tzr.enableRotation(); else tzr.disableRotation();
    }
  }

  // -----------------------------------------------------------------------
  // Native-layer tracking and the MapLibre legend's default targets.
  //
  // A legend_control() given no targets lists the app's own native layers
  // rather than every layer of the basemap style (~100 on CARTO). The plugin
  // re-reads its `targets` object on every update, so it gets one live object
  // per map that is kept in step with the native layers. The plugin treats an
  // empty object as "all layers", hence the sentinel key.
  // -----------------------------------------------------------------------
  var LEGEND_NO_TARGET = '__shiny_deckgl_no_layer__';

  function newLegendTargets() {
    var t = {};
    t[LEGEND_NO_TARGET] = '';
    return t;
  }

  function trackNativeLayer(instance, id, present) {
    if (present) instance.nativeLayers[id] = true;
    else delete instance.nativeLayers[id];
    var t = instance._legendAutoTargets;
    if (t) {
      if (present) t[id] = id;
      else delete t[id];
    }
    refreshLegendWhenDrawn(instance);
  }

  // The legend plugin rebuilds on 'styledata', which fires when a layer is
  // added but before it is drawn, so with onlyRendered (the default) a new
  // layer stays out of the legend until the user pans. Redraw it once the
  // map has drawn the change ('idle'), or after a second if an animation
  // keeps the map from ever going idle.
  function refreshLegendWhenDrawn(instance) {
    var legend = instance.controls && instance.controls.legend;
    if (!legend || !instance.map || instance._legendRefreshPending) return;
    instance._legendRefreshPending = true;
    var done = false;
    var run = function () {
      if (done) return;
      done = true;
      instance._legendRefreshPending = false;
      instance.map.off('idle', run);
      clearTimeout(timer);
      var current = instance.controls && instance.controls.legend;
      if (current && current.control && typeof current.control.redraw === 'function') {
        try { current.control.redraw(); } catch (e) { console.debug('[shiny_deckgl] legend redraw failed:', e.message); }
      }
    };
    var timer = setTimeout(run, 1000);
    instance.map.once('idle', run);
  }

  function resetNativeLayers(instance) {
    instance.nativeLayers = {};
    var t = instance._legendAutoTargets;
    if (t) {
      Object.keys(t).forEach(function (k) { if (k !== LEGEND_NO_TARGET) delete t[k]; });
    }
  }

  // Identity of a control spec: same key, same control.
  function controlKey(spec) {
    return JSON.stringify([spec.position || 'top-right', spec.options || {}]);
  }

  // Make the map's controls match `specs` (one per type). Controls whose
  // spec is unchanged are kept: re-creating them loses their state (an open
  // legend panel) and, for the legend plugin, leaks the map listeners its
  // onRemove never detaches.
  function applyControls(instance, specs) {
    var wanted = {};
    specs.forEach(function (spec) { if (spec && spec.type) wanted[spec.type] = spec; });
    Object.keys(instance.controls).forEach(function (type) {
      var have = instance.controls[type];
      var spec = wanted[type];
      if (spec && have.key === controlKey(spec)) return;  // unchanged: keep
      try {
        instance.map.removeControl(have.control);
      } catch (e) {
        console.debug('[shiny_deckgl] removeControl failed (may already be removed):', e.message);
      }
      delete instance.controls[type];
    });
    specs.forEach(function (spec) {
      if (!spec || !spec.type || instance.controls[spec.type]) return;
      var control = createControl(spec.type, spec.options || {}, instance._legendAutoTargets);
      if (!control) return;
      var position = spec.position || 'top-right';
      instance.map.addControl(control, position);
      instance.controls[spec.type] = { control: control, position: position, key: controlKey(spec) };
    });
  }

  // -----------------------------------------------------------------------
  // Helper: create MapLibre control by type name. `legendTargets` is the
  // live default-targets object used when a legend spec has no targets.
  // -----------------------------------------------------------------------
  function createControl(type, opts, legendTargets) {
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
          // Explicit targets win ({} means every style layer); none given
          // means the app's own native layers.
          const legendOpts = Object.assign({}, opts);
          delete legendOpts.targets;
          const targets = opts.targets != null ? opts.targets : legendTargets;
          return new MaplibreLegendControl.MaplibreLegendControl(targets, legendOpts);
        }
        console.warn('[shiny_deckgl] MaplibreLegendControl not loaded. Include the @watergis/maplibre-gl-legend CDN script.');
        return null;
      case 'opacity':
        if (typeof OpacityControl !== 'undefined') {
          return new OpacityControl(opts);
        }
        console.warn('[shiny_deckgl] OpacityControl not loaded. Include the maplibre-gl-opacity CDN script.');
        return null;
      default:
        console.warn('[shiny_deckgl] Unknown control type: ' + type);
        return null;
    }
  }

  // -----------------------------------------------------------------------
  // Style-readiness guard — defers callback until the map style is parsed.
  // Also respects _deckStyleChanging flag set by deck_set_style to avoid
  // a race where the old style still reports ready during a style swap.
  // -----------------------------------------------------------------------
  var STYLE_DRAIN_EVENTS = ['style.load', 'styledata', 'idle'];

  // Sources and layers can be added once the style JSON is parsed. Do not use
  // map.isStyleLoaded() for this: it is also false while any source or tile
  // is loading (e.g. straight after add_source, or during a pan), and a call
  // queued then used to wait for a 'style.load' that never came.
  function isStyleReady(map) {
    if (map._deckStyleChanging) return false;
    var style = map.style;
    if (style && typeof style._loaded === 'boolean') return style._loaded;
    return map.isStyleLoaded();
  }

  function whenStyleReady(map, fn) {
    // Keep FIFO order: while earlier calls are queued, later ones queue too.
    if (!map._deckStyleQueue && isStyleReady(map)) {
      fn();
      return;
    }
    if (!map._deckStyleQueue) {
      map._deckStyleQueue = [];
      var drainFn = function () {
        if (!isStyleReady(map)) return;  // keep waiting for a later event
        var queue = map._deckStyleQueue || [];
        STYLE_DRAIN_EVENTS.forEach(function (ev) { map.off(ev, drainFn); });
        map._deckStyleQueue = null;
        map._deckStyleDrainFn = null;
        for (var i = 0; i < queue.length; i++) {
          try { queue[i](); } catch (e) {
            console.error('[shiny_deckgl] Queued style callback [' + i + '/' + queue.length + '] failed:', e);
          }
        }
      };
      map._deckStyleDrainFn = drainFn;
      STYLE_DRAIN_EVENTS.forEach(function (ev) { map.on(ev, drainFn); });
    }
    map._deckStyleQueue.push(fn);
  }

  /** Clean up the style-ready queue and its listener (used on error/timeout). */
  function _clearStyleQueue(map) {
    var abandoned = map._deckStyleQueue || [];
    if (map._deckStyleDrainFn) {
      var drainFn = map._deckStyleDrainFn;
      STYLE_DRAIN_EVENTS.forEach(function (ev) { map.off(ev, drainFn); });
      map._deckStyleDrainFn = null;
    }
    map._deckStyleQueue = null;
    if (abandoned.length > 0) {
      console.warn('[shiny_deckgl] ' + abandoned.length
        + ' queued style callback(s) abandoned due to style load failure');
    }
  }

  // -----------------------------------------------------------------------
  // Map initialisation
  // -----------------------------------------------------------------------
  function initMap(el) {
    const mapId = el.id;
    if (!mapId) return;

    // Read initial view state from data attributes (set by MapWidget)
    const initLon = isNaN(parseFloat(el.dataset.initialLongitude)) ? 0 : parseFloat(el.dataset.initialLongitude);
    const initLat = isNaN(parseFloat(el.dataset.initialLatitude)) ? 0 : parseFloat(el.dataset.initialLatitude);
    const initZoom = isNaN(parseFloat(el.dataset.initialZoom)) ? 1 : parseFloat(el.dataset.initialZoom);
    const initPitch = isNaN(parseFloat(el.dataset.initialPitch)) ? 0 : parseFloat(el.dataset.initialPitch);
    const initBearing = isNaN(parseFloat(el.dataset.initialBearing)) ? 0 : parseFloat(el.dataset.initialBearing);
    const initMinZoom = isNaN(parseFloat(el.dataset.initialMinZoom)) ? 0 : parseFloat(el.dataset.initialMinZoom);
    const initMaxZoom = isNaN(parseFloat(el.dataset.initialMaxZoom)) ? 24 : parseFloat(el.dataset.initialMaxZoom);
    const mapStyle = el.dataset.style ||
      'https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json';
    // Dark from the first frame when the page already is (no double load).
    const darkStyle = el.dataset.darkStyle || null;
    const startDark = !!darkStyle && el.dataset.followDarkMode !== 'false' &&
      document.documentElement.getAttribute('data-bs-theme') === 'dark';
    const startStyle = startDark ? darkStyle : mapStyle;
    if (startDark) el.classList.toggle('deckgl-dark', true);

    // Optional Mapbox API key — enables mapbox:// style URLs
    const mapboxApiKey = el.dataset.mapboxApiKey || null;

    // Parse tooltip config from data-tooltip (JSON)
    let tooltipConfig = null;
    if (el.dataset.tooltip) {
      try {
        var parsed = JSON.parse(el.dataset.tooltip);
        if (parsed && typeof parsed.html === 'string') {
          tooltipConfig = parsed;
        } else {
          console.warn('[shiny_deckgl] data-tooltip JSON must have an "html" string key, got:', typeof parsed.html);
        }
      } catch (e) {
        console.warn('[shiny_deckgl] Failed to parse data-tooltip JSON:', e.message);
      }
    }

    const mapOpts = {
      container: mapId,
      style: startStyle,
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
        // Only attach the token to genuine Mapbox endpoints. Parse the URL and
        // match the hostname exactly (or the mapbox:// scheme) so the token is
        // never leaked to look-alike hosts such as "api.mapbox.com.evil.tld".
        var isMapbox = false;
        if (url.startsWith('mapbox://')) {
          isMapbox = true;
        } else {
          try {
            var host = new URL(url, window.location.href).hostname.toLowerCase();
            isMapbox = (host === 'api.mapbox.com' || host.endsWith('.tiles.mapbox.com'));
          } catch (e) {
            isMapbox = false;
          }
        }
        if (isMapbox && url.indexOf('access_token') === -1) {
          const sep = url.indexOf('?') === -1 ? '?' : '&';
          return { url: url + sep + 'access_token=' + mapboxApiKey };
        }
      };
    }
    const map = new maplibregl.Map(mergeMapOptions(mapOpts, el));
    // Every style (initial and set_style) must leave a projection deck 9.4 accepts.
    map.on('style.load', function () { normaliseProjection(map); });

    // Apply initial controller setting from data attribute
    if (el.dataset.controller !== undefined) {
      try {
        applyController(map, JSON.parse(el.dataset.controller));
      } catch (e) {
        console.warn('[shiny_deckgl] Failed to parse data-controller JSON:', e.message);
      }
    }

    // ---- Configurable initial controls ------------------------------------
    // Parse controls config from data-controls attribute (JSON array).
    // When the attribute is present (even as "[]") honour it exactly;
    // only fall back to a default NavigationControl when the attribute
    // is absent (i.e. the widget was constructed with controls=None).
    let controlsConfig = [];
    if (el.dataset.controls !== undefined) {
      try {
        controlsConfig = JSON.parse(el.dataset.controls);
      } catch (e) {
        console.warn('[shiny_deckgl] Failed to parse data-controls JSON:', e.message);
      }
    } else {
      controlsConfig = [{ type: 'navigation', position: 'top-right' }];
    }

    const initialControls = {};
    const legendAutoTargets = newLegendTargets();
    controlsConfig.forEach(function (cfg) {
      const ctrl = createControl(cfg.type, cfg.options || {}, legendAutoTargets);
      if (ctrl) {
        const pos = cfg.position || 'top-right';
        map.addControl(ctrl, pos);
        initialControls[cfg.type] = { control: ctrl, position: pos, key: controlKey(cfg) };
      }
    });

    // Send view state back to Shiny on every meaningful camera move
    map.on('moveend', function () {
      const center = map.getCenter();
      const bounds = map.getBounds();
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

    const interleavedMode = el.dataset.interleaved === 'true';
    const overlay = new deck.MapLibreOverlay({
      interleaved: interleavedMode,
      layers: [],
      // Forward widget-initiated view state changes (e.g. CompassWidget
      // bearing reset, ZoomWidget zoom) back to the MapLibre map.
      // Without this, the overlay silently consumes the change and MapLibre
      // overwrites it on the next render frame.
      onViewStateChange: function (params) {
        const vs = params.viewState;
        if (!vs) return;
        const opts = {
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
    const initialDeckProps = {};
    if (el.dataset.pickingRadius) {
      initialDeckProps.pickingRadius = parseInt(el.dataset.pickingRadius, 10) || 0;
    }
    if (el.dataset.useDevicePixels !== undefined) {
      try {
        initialDeckProps.useDevicePixels = JSON.parse(el.dataset.useDevicePixels);
      } catch (e) {
        console.warn('[shiny_deckgl] Failed to parse data-useDevicePixels JSON:', e.message);
      }
    }
    if (el.dataset.animate === 'true') {
      initialDeckProps._animate = true;
    }
    if (el.dataset.parameters) {
      try {
        initialDeckProps.parameters = JSON.parse(el.dataset.parameters);
      } catch (e) {
        console.warn('[shiny_deckgl] Failed to parse data-parameters JSON:', e.message);
      }
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
      el: el,
      lightStyle: mapStyle,    // dark mode (v1.13.0): the pair to swap between
      darkStyle: darkStyle,
      currentStyle: startStyle,
      dark: startDark,
      controls: initialControls,
      // true when the navigation control is our default, not the app's choice
      _implicitNavigation: el.dataset.controls === undefined,
      nativeLayers: {},        // tracks native MapLibre layers added via add_maplibre_layer
      _legendAutoTargets: legendAutoTargets,  // live default targets for legend controls
      // TripsLayer animation state (v0.9.0)
      tripsAnimation: null     // see startTripsAnimation()
    };
    watchBootstrapTheme(mapInstances[mapId], mapId);

    // Dismiss tooltip when the cursor is over empty map space.
    // Per-layer onHover only fires while the pointer is near that layer's
    // features; once it moves away, deck.gl stops firing and the tooltip
    // can get stuck.  This map-level listener catches every mouse move and
    // hides the tooltip when deck.gl picking finds nothing underneath.
    map.on('mousemove', function (e) {
      const inst = mapInstances[mapId];
      if (!inst || !inst.tooltipConfig || !inst.tooltipConfig.html) return;
      const result = overlay.pickObject({
        x: e.point.x,
        y: e.point.y,
        radius: 0,
      });
      if (!result || !result.object) {
        const tooltipEl = document.getElementById(mapId + '__tooltip');
        if (tooltipEl) tooltipEl.style.display = 'none';
      }
    });
  }

  // Check whether an element is in a currently visible Bootstrap tab panel.
  // Walks the full ancestor chain to handle nested tabs correctly.
  // Elements not inside any .tab-pane are always considered visible.
  function isInVisibleTab(el) {
    var pane = el.closest('.tab-pane');
    while (pane) {
      if (!pane.classList.contains('active') && !pane.classList.contains('show')) {
        return false;
      }
      pane = pane.parentElement ? pane.parentElement.closest('.tab-pane') : null;
    }
    return true;
  }

  // Safely initialise a single map element with error handling.
  function safeInitMap(el) {
    if (mapInstances[el.id]) return; // already initialised
    try {
      initMap(el);
      // Replay any messages queued while this map was uninitialised (e.g.
      // deferred during CDN load for a visible map). replayDeferredMessages
      // consumes the queue, so redundant calls elsewhere are harmless no-ops.
      if (mapInstances[el.id]) replayDeferredMessages(el.id);
    } catch(e) {
      console.error('[shiny_deckgl] initMap failed for "' + el.id + '":', e);
      el.innerHTML = '<div style="padding:20px;color:#c00;font:14px sans-serif">' +
        '[shiny_deckgl] Map failed to initialise. Check browser console.</div>';
    }
  }

  // Tear down a map instance and release its resources when its DOM node is
  // removed (e.g. a Shiny tab/UI is re-rendered). Without this, MapLibre maps,
  // deck.gl overlays, RAF loops and animation globals leak.
  // True when `removedEl` is the container of `instance` and has left the
  // document. Checking the id instead is wrong: Shiny's render.ui swaps in a
  // replacement with the same id before the MutationObserver runs, so the id
  // still resolves while the map's own node is gone. A node that was only
  // moved is still connected and keeps its map.
  function isDetachedMapContainer(instance, removedEl) {
    var container = null;
    try { container = instance.map && instance.map.getContainer(); } catch (e) { /* ignore */ }
    if (!container) return !document.getElementById(removedEl.id);
    return container === removedEl && !container.isConnected;
  }

  function disposeMap(id) {
    var instance = mapInstances[id];
    if (!instance) return;
    // Stop the frame loop.
    try {
      if (instance._frameRaf) cancelAnimationFrame(instance._frameRaf);
    } catch (e) { /* ignore */ }
    instance._frameRaf = null;
    try { if (instance._themeObserver) instance._themeObserver.disconnect(); } catch (e) { /* ignore */ }
    // Finalise the deck.gl overlay, then the MapLibre map.
    try { if (instance.overlay && instance.overlay.finalize) instance.overlay.finalize(); } catch (e) { /* ignore */ }
    try { if (instance.map && instance.map.remove) instance.map.remove(); } catch (e) { /* ignore */ }
    // Drop the animation globals this map's @@animate markers created.
    Object.keys(instance._animGlobals || {}).forEach(function (k) {
      try { delete window[k]; } catch (e2) { window[k] = undefined; }
    });
    delete mapInstances[id];
    if (typeof _deferredMessages !== 'undefined') delete _deferredMessages[id];
  }

  // -----------------------------------------------------------------------
  // MapLibre GL JS v6 loader
  //
  // v6 is ESM-only -- it ships no UMD/IIFE build, so there is no <script src>
  // tag that can publish the `maplibregl` global this file depends on. The
  // module URL arrives in an inert JSON data block (so a strict script-src CSP
  // needs no 'unsafe-inline'), and we import() it once, publishing the module
  // namespace as window.maplibregl. The namespace is frozen, but every use
  // here is a read, so binding it directly is safe.
  // -----------------------------------------------------------------------
  var _maplibrePromise = null;

  function maplibreModuleUrl() {
    var el = document.getElementById('shiny-deckgl-cdn');
    if (!el) return null;
    try {
      return JSON.parse(el.textContent).maplibre || null;
    } catch (e) {
      console.error('[shiny_deckgl] Malformed CDN config block:', e);
      return null;
    }
  }

  function loadMapLibre() {
    if (typeof window.maplibregl !== 'undefined' && window.maplibregl) {
      return Promise.resolve(window.maplibregl);
    }
    if (_maplibrePromise) return _maplibrePromise;

    var url = maplibreModuleUrl();
    if (!url) {
      return Promise.reject(new Error(
        'MapLibre module URL not found: missing <script id="shiny-deckgl-cdn">'));
    }
    _maplibrePromise = import(url).then(function (ns) {
      // v6 exposes named exports only; older builds had a default export.
      window.maplibregl = (ns && ns.Map) ? ns : (ns && ns.default) || ns;
      return window.maplibregl;
    }).catch(function (err) {
      _maplibrePromise = null;   // allow a retry
      console.error('[shiny_deckgl] Failed to load MapLibre GL JS from ' + url, err);
      throw err;
    });
    return _maplibrePromise;
  }

  window.__deckgl_loadMapLibre = loadMapLibre;

  // Initialize deckgl-map divs on page load inside shiny.
  // Only init maps in the currently visible tab to avoid exhausting
  // WebGL contexts.  Maps in hidden tabs are lazy-initialised when
  // their tab is first shown (see shown.bs.tab handler below).
  // Shiny signals readiness with `$(document).trigger({type:
  // "shiny:connected"})`. A jQuery-triggered event does NOT reach a native
  // addEventListener handler, so registering only natively meant this gate
  // never ran under Shiny: the map on the first tab stayed blank, and only
  // maps whose tab was switched to came up (shown.bs.tab is a real DOM event).
  // Register both ways -- jQuery for Shiny, native for standalone hosts -- and
  // guard against running twice if both fire.
  var _shinyConnectedHandled = false;
  var _reconnectCount = 0;

  function onShinyConnected() {
    if (_shinyConnectedHandled) {
      // A later shiny:connected is a reconnect (session.allow_reconnect()).
      // Shiny resends inputs and recalculates outputs, but the maps are fed
      // by custom messages, which are not replayed: tell the server which
      // maps are still live so it can resend_last_update().
      _reconnectCount++;
      Object.keys(mapInstances).forEach(function (id) {
        Shiny.setInputValue(id + '_reconnected', { count: _reconnectCount }, { priority: 'event' });
      });
      return;
    }
    _shinyConnectedHandled = true;
    var attempts = 0;
    // Start the MapLibre module fetch immediately; the poll below waits for
    // the global it publishes, alongside the classic deck.gl bundle.
    loadMapLibre().catch(function () { /* reported by the poll's timeout */ });
    function tryInit() {
      attempts++;
      // Wait for CDN libraries to finish loading
      if (typeof maplibregl === 'undefined' || typeof deck === 'undefined') {
        if (attempts < 50) {
          setTimeout(tryInit, 200);
        } else {
          console.error('[shiny_deckgl] CDN libraries (maplibregl/deck) failed to load after 10s');
          document.querySelectorAll('.deckgl-map').forEach(function(el) {
            if (!mapInstances[el.id]) {
              el.innerHTML = '<div style="padding:20px;color:#c00;font:14px sans-serif">' +
                '[shiny_deckgl] Map libraries failed to load. Check network connection.</div>';
            }
          });
        }
        return;
      }
      var maps = document.querySelectorAll('.deckgl-map');
      if (maps.length === 0 && attempts < 50) {
        setTimeout(tryInit, 200);
        return;
      }
      maps.forEach(function(el) {
        if (isInVisibleTab(el)) {
          safeInitMap(el);
        }
      });
    }
    tryInit();
  }

  if (window.jQuery) {
    window.jQuery(document).on('shiny:connected', onShinyConnected);
  }
  document.addEventListener('shiny:connected', onShinyConnected);

  // -----------------------------------------------------------------------
  // Helper: resolve @@ accessors
  // -----------------------------------------------------------------------
  // Validate an @@= accessor expression before handing it to new Function().
  //
  // The permitted language is: property access over the datum `d`, numeric and
  // string literals, and the arithmetic / comparison / logical / ternary
  // operators. Everything else -- calls, assignment, arrow functions, template
  // literals, and any identifier other than `d` -- is rejected, so the compiled
  // function has no way to reach a global.
  var ACCESSOR_DANGEROUS_PROPS_RE = /(?:__proto__|constructor|prototype)/i;
  var ACCESSOR_ALLOWED_IDENTS = { d: true, true: true, false: true, null: true, undefined: true };
  var ACCESSOR_KEY_RE = /^\s*(?:\d+(?:\.\d+)?|d(?:\s*\??\.\s*[A-Za-z_$][A-Za-z0-9_$]*)*)\s*$/;

  function isSafeAccessorExpr(expr) {
    if (typeof expr !== 'string') return false;
    expr = expr.trim();
    if (!expr || expr.length > 200) return false;
    if (ACCESSOR_DANGEROUS_PROPS_RE.test(expr)) return false;

    // Blank out string literals so their contents cannot trip the token rules.
    // Backslashes are disallowed outright, so no escape handling is needed.
    if (expr.indexOf('\\') !== -1) return false;
    var s = expr.replace(/"[^"]*"|'[^']*'/g, '0');

    // No statements, blocks, template literals or comments.
    if (/[;{}`]/.test(s)) return false;
    if (s.indexOf('//') !== -1 || s.indexOf('/*') !== -1) return false;
    // No increment/decrement, no arrow functions.
    if (/\+\+|--|=>/.test(s)) return false;
    // A '(' directly after an identifier, ')', ']' or '.' is a call; the '.'
    // case is the optional call `f?.(...)`.
    if (/[A-Za-z0-9_$)\].]\s*\(/.test(s)) return false;
    // A computed key must be a literal (strings are blanked to 0 above) or a
    // plain `d.a.b` path. Anything else, e.g. "con"+"structor", could build a
    // name at run time that ACCESSOR_DANGEROUS_PROPS_RE never saw.
    var keys = s.split('[').slice(1);
    for (var k = 0; k < keys.length; k++) {
      var close = keys[k].indexOf(']');
      if (close === -1 || !ACCESSOR_KEY_RE.test(keys[k].slice(0, close))) return false;
    }
    // Assignment: strip the multi-character comparison operators first, then
    // any '=' that remains is an assignment (or an arrow already excluded).
    if (/=/.test(s.replace(/===|!==|==|!=|<=|>=/g, ' '))) return false;

    // Every bare identifier must be `d` or a literal keyword; identifiers that
    // follow a '.' are property names and are unrestricted.
    var bare = s.replace(/\.\s*[A-Za-z_$][A-Za-z0-9_$]*/g, '.');
    var idents = bare.match(/[A-Za-z_$][A-Za-z0-9_$]*/g) || [];
    for (var i = 0; i < idents.length; i++) {
      if (!Object.prototype.hasOwnProperty.call(ACCESSOR_ALLOWED_IDENTS, idents[i])) return false;
    }
    if (idents.indexOf('d') === -1) return false;

    // Finally, only whitelisted characters may appear at all.
    return /^[\sA-Za-z0-9_$.\[\]()+\-*\/%?:<>!&|=]*$/.test(s);
  }

  // deck.gl 8 identified coordinate systems by integer; deck.gl 9 uses
  // strings and rejects the integers with "Invalid coordinateSystem: 1" at
  // draw time. Accept either so apps written against the old constants keep
  // rendering.
  var LEGACY_COORDINATE_SYSTEMS = {
    '-1': 'default',
    '0': 'cartesian',
    '1': 'lnglat',
    '2': 'meter-offsets',
    '3': 'lnglat-offsets'
  };

  function normaliseCoordinateSystem(value) {
    if (value == null) return value;
    if (typeof value === 'number') {
      var mapped = LEGACY_COORDINATE_SYSTEMS[String(value)];
      if (mapped) return mapped;
      console.warn('[shiny_deckgl] Unknown numeric coordinateSystem: ' + value);
      return 'default';
    }
    return value;
  }

  function resolveAccessors(layerProps) {
    if ('coordinateSystem' in layerProps) {
      layerProps.coordinateSystem = normaliseCoordinateSystem(layerProps.coordinateSystem);
    }
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
      if (raw.startsWith('=')) {
        const expr = raw.slice(1).trim();
        if (!isSafeAccessorExpr(expr)) {
          console.warn('[shiny_deckgl] Rejected unsafe accessor expression "' + val +
            '": only arithmetic, comparison and property access over `d` are allowed ' +
            '(no function calls; a [...] index must be a number, a quoted string or a d.a.b path).');
          // Delete rather than leave the raw "@@=..." string behind: deck.gl
          // treats a non-function accessor as a constant and coerces the
          // string to NaN, silently rendering nothing.
          delete layerProps[key];
          continue;
        }
        try {
          // eslint-disable-next-line no-new-func
          layerProps[key] = new Function('d', 'return (' + expr + ');');
        } catch (e) {
          console.warn('[shiny_deckgl] Bad accessor "' + val + '":', e.message);
          delete layerProps[key];
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
        // deck.gl exports experimental classes with a leading underscore
        // (deck._TerrainExtension), like the widgets and GlobeView.
        const Cls = resolveWidgetClass(deck, item);
        if (!Cls) {
          console.warn('[shiny_deckgl] Unknown extension: ' + item);
          return null;
        }
        return new Cls();
      }
      // Object form: { "@@extClass": "Name", "@@extOpts": {...} }
      if (item && item['@@extClass']) {
        const Cls = resolveWidgetClass(deck, item['@@extClass']);
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
    int32: Int32Array,
    uint32: Uint32Array
  };

  /** Decode a single @@binary transport dict into a TypedArray. */
  function decodeBinaryValue(val) {
    const ArrayCtor = TYPED_ARRAY_MAP[val.dtype] || Float32Array;
    const raw = atob(val.value);
    const bytes = Uint8Array.from(raw, function(c) { return c.charCodeAt(0); });
    return new ArrayCtor(bytes.buffer);
  }

  function resolveBinaryAttributes(layerProps) {
    const binaryAttrs = {};
    let hasBinary = false;
    for (const key of Object.keys(layerProps)) {
      // Skip _mesh* keys — they are decoded by the SimpleMeshLayer-specific handler
      if (key.startsWith('_mesh')) continue;
      const val = layerProps[key];
      if (val && typeof val === 'object' && val['@@binary']) {
        try {
          const typed = decodeBinaryValue(val);
          binaryAttrs[key] = { value: typed, size: val.size || 1 };
          delete layerProps[key];
          hasBinary = true;
        } catch (err) {
          console.warn('[shiny_deckgl] Failed to decode binary attribute "' + key + '":', err);
          delete layerProps[key];  // Remove corrupted attribute to prevent further errors
        }
      }
    }
    // deck.gl v9 requires binary attributes in data.attributes
    if (hasBinary) {
      if (!layerProps.data || typeof layerProps.data !== 'object') {
        layerProps.data = {};
      }
      if (typeof layerProps.data.length === 'undefined') {
        // Infer length from first binary attribute
        const firstKey = Object.keys(binaryAttrs)[0];
        const attr = binaryAttrs[firstKey];
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
  // Resolve a named luma.gl shader module. These live in @luma.gl/effects,
  // which is NOT part of the deck.gl standalone bundle, so the lookup can
  // legitimately come up empty -- callers must handle null rather than hand
  // deck.gl a name string where it expects a module object.
  function resolvePostProcessModule(name, scope) {
    if (!name) return null;
    var root = scope || (typeof globalThis !== 'undefined' ? globalThis : window);
    var namespaces = [root.lumaEffects, root.luma, root.deck];
    for (var i = 0; i < namespaces.length; i++) {
      var ns = namespaces[i];
      if (ns && ns[name] && typeof ns[name] === 'object') return ns[name];
    }
    return null;
  }

  function buildEffects(effectsData) {
    if (!effectsData) return undefined;
    // An explicit [] clears the effects an earlier update set.
    if (!effectsData.length) return [];
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
        if (Array.isArray(spec.sunLights) && deck._SunLight) {
          spec.sunLights.forEach((sl, i) => {
            const slProps = Object.assign({}, sl);
            delete slProps['@@sunLight'];
            lights['sun' + i] = new deck._SunLight(slProps);
          });
        }
        return new deck.LightingEffect(lights);
      }
      // PostProcessEffect: deck.gl's signature is (module, props), where
      // module is a luma.gl shader module object. Passing the spec dict as the
      // module threw, and the throw took the whole effects array down with it.
      if (spec.type === 'PostProcessEffect' && deck.PostProcessEffect) {
        var ppModule = resolvePostProcessModule(spec.shaderModule);
        if (!ppModule) {
          console.warn('[shiny_deckgl] PostProcessEffect shader module not available: ' +
                       spec.shaderModule + ' (requires @luma.gl/effects)');
          return null;
        }
        var ppProps = Object.assign({}, spec);
        delete ppProps.type;
        delete ppProps.shaderModule;
        return new deck.PostProcessEffect(ppModule, ppProps);
      }
      console.warn('[shiny_deckgl] Unknown effect type: ' + spec.type);
      return null;
    }).filter(e => e !== null);
  }

  // -----------------------------------------------------------------------
  // Helper: resolve view specs → deck.gl View instances
  // -----------------------------------------------------------------------
  // Translate a (possibly partial) view_state into MapLibre camera options.
  //
  // Only the axes the caller actually supplied are emitted: substituting
  // defaults for omitted keys -- zoom 1, pitch/bearing 0 -- made
  // update(view_state={'longitude': x}) reset the whole camera instead of
  // nudging one axis.
  // Update generation tokens. deck_update awaits an async SVG-atlas preload
  // before rendering; without a token an earlier, slower update resolves last
  // and paints layers that no longer match instance.lastLayers.
  function claimUpdateGeneration(instance) {
    instance._updateGen = (instance._updateGen || 0) + 1;
    return instance._updateGen;
  }

  function isStaleUpdate(instance, gen) {
    return instance._updateGen !== gen;
  }

  // Whether a layer update may (re)start the trips RAF loop. An update must
  // not resurrect an animation the user explicitly paused; an explicit
  // resume/reset may.
  function shouldStartTripsAnimation(instance, fromUpdate) {
    if (!fromUpdate) return true;
    return !instance._tripsPaused;
  }

  // Flatten the MapLibre canvas and deck.gl's own canvas into one image.
  // Outside interleaved mode deck.gl draws into a separate canvas stacked
  // above the basemap, so capturing map.getCanvas() alone loses every layer.
  function compositeMapCanvases(baseCanvas, overlayCanvas) {
    if (!overlayCanvas || overlayCanvas === baseCanvas) return baseCanvas;
    var out = document.createElement('canvas');
    out.width = baseCanvas.width;
    out.height = baseCanvas.height;
    var ctx = out.getContext('2d');
    ctx.drawImage(baseCanvas, 0, 0);
    ctx.drawImage(overlayCanvas, 0, 0, out.width, out.height);
    return out;
  }

  function buildCameraOptions(vs) {
    const opts = {};
    if (vs.longitude != null && vs.latitude != null) {
      opts.center = [vs.longitude, vs.latitude];
    }
    if (vs.zoom != null) opts.zoom = vs.zoom;
    if (vs.pitch != null) opts.pitch = vs.pitch;
    if (vs.bearing != null) opts.bearing = vs.bearing;
    return opts;
  }

  function buildViews(viewsData) {
    if (!viewsData) return undefined;
    // An explicit [] restores deck.gl's default view.
    if (!viewsData.length) return null;
    return viewsData.map(spec => {
      const typeName = spec['@@type'] || 'MapView';
      const props = Object.assign({}, spec);
      delete props['@@type'];
      // deck.gl 9.x exports experimental views with a leading underscore
      // (deck._GlobeView), so fall back to that before giving up -- the
      // LightingEffect branch does the same for deck._SunLight.
      const ViewClass = deck[typeName] || deck['_' + typeName];
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
  // Resolve a widget class by name, tolerating either naming.
  //
  // deck.gl marks experimental widgets with a leading underscore and drops it
  // when they stabilise (`_InfoWidget` -> `InfoWidget`). Looking up only the
  // requested name, or only that name with an underscore *added*, meant a
  // helper written against the experimental name stopped resolving the moment
  // the widget was promoted -- the widget was silently dropped with a console
  // warning. Try the name as given, then with the underscore added, then with
  // it stripped.
  function resolveWidgetClass(deckNs, className) {
    if (!deckNs || !className) return undefined;
    if (deckNs[className]) return deckNs[className];
    if (deckNs['_' + className]) return deckNs['_' + className];
    if (className.charAt(0) === '_' && deckNs[className.slice(1)]) {
      return deckNs[className.slice(1)];
    }
    return undefined;
  }

  // Widget callbacks (deck.gl >= 9.3) forwarded to Shiny as one input per
  // map: <mapId>_widget_event = {id, widget, event, value}. Keyed by the
  // class name without the experimental "_" prefix.
  var WIDGET_EVENTS = {
    TimelineWidget: ['onTimeChange', 'onPlayingChange'],
    ToggleWidget: ['onChange'],
    SelectorWidget: ['onChange'],
    IconWidget: ['onClick'],
    PopupWidget: ['onOpenChange'],
    StatsWidget: ['onExpandedChange'],
    ThemeWidget: ['onThemeModeChange'],
    GeocoderWidget: ['onGeocode'],
    ZoomWidget: ['onZoom'],
    FullscreenWidget: ['onFullscreenChange'],
    LoadingWidget: ['onLoadingChange'],
    ResetViewWidget: ['onReset'],
  };

  // Patches the constructed widget's props: widgets read callbacks from
  // this.props at event time, the instance carries the real id (its class
  // default when the spec set none), and Widget.setProps merges, so the
  // shim survives later set_widgets() calls.
  function attachWidgetEvents(widget, className, targetId) {
    var name = className.replace(/^_/, '');
    var events = WIDGET_EVENTS[name];
    if (!events || !widget || !widget.props) return widget;
    // props.id is the spec's id merged over the class default. Some classes
    // (TimelineWidget 9.4) also declare a class field `id = '...'` that runs
    // after super(props) and clobbers widget.id, so props.id is the one to trust.
    var widgetId = widget.props.id != null ? widget.props.id
      : (widget.id != null ? widget.id : name);
    events.forEach(function (prop) {
      var own = typeof widget.props[prop] === 'function' ? widget.props[prop] : null;
      var event = prop.charAt(2).toLowerCase() + prop.slice(3);   // onTimeChange -> timeChange
      widget.props[prop] = function (value) {
        if (own) own.apply(this, arguments);
        Shiny.setInputValue(targetId + '_widget_event', {
          id: widgetId, widget: name, event: event,
          value: arguments.length ? value : null,
        }, { priority: 'event' });
      };
    });
    return widget;
  }

  function buildWidgets(widgetSpecs, targetId) {
    if (!widgetSpecs) return undefined;
    // An explicit empty list must reach overlay.setProps so deck.gl removes
    // the current widgets; `undefined` would leave them in place.
    if (!widgetSpecs.length) return [];
    // Resolve the map container element so FullscreenWidget can target it
    const containerEl = targetId ? document.getElementById(targetId) : null;
    return widgetSpecs.map(spec => {
      const className = spec['@@widgetClass'];
      if (!className) return null;
      const props = Object.assign({}, spec);
      delete props['@@widgetClass'];
      // FullscreenWidget must target the map container, not the deck canvas
      if (className === 'FullscreenWidget' && containerEl && !props.container) {
        props.container = containerEl;
      }
      // Custom shiny_deckgl widgets
      if (className === '_DeckLayerLegendWidget') {
        return createDeckLayerLegendWidget(props);
      }
      const Cls = resolveWidgetClass(deck, className);
      if (!Cls) {
        console.warn('[shiny_deckgl] Unknown widget: ' + className +
          ' (no such class in this deck.gl build)');
        return null;
      }
      return attachWidgetEvents(new Cls(props), className, targetId);
    }).filter(Boolean);
  }

  // -----------------------------------------------------------------------
  // Built-in easing functions for layer transitions (v0.8.0)
  // -----------------------------------------------------------------------
  // Must stay in sync with the EasingFunction enum in enums.py -- a name the
  // enum publishes but this table omits falls through to the identity function
  // and animates linearly with no warning.
  const EASINGS = {
    'linear': function(t) { return t; },
    'ease-in-cubic': function(t) { return t * t * t; },
    'ease-out-cubic': function(t) { return 1 - Math.pow(1 - t, 3); },
    'ease-in-out-cubic': function(t) { return t < 0.5 ? 4*t*t*t : 1 - Math.pow(-2*t+2, 3)/2; },
    'ease-in-sine': function(t) { return 1 - Math.cos((t * Math.PI) / 2); },
    'ease-out-sine': function(t) { return Math.sin((t * Math.PI) / 2); },
    'ease-in-out-sine': function(t) { return -(Math.cos(Math.PI * t) - 1) / 2; },
    'ease-in-quad': function(t) { return t * t; },
    'ease-out-quad': function(t) { return 1 - (1 - t) * (1 - t); },
    'ease-in-out-quad': function(t) { return t < 0.5 ? 2*t*t : 1 - Math.pow(-2*t+2, 2)/2; },
    'ease-in-expo': function(t) { return t === 0 ? 0 : Math.pow(2, 10*t - 10); },
    'ease-out-expo': function(t) { return t === 1 ? 1 : 1 - Math.pow(2, -10*t); },
    'ease-in-out-expo': function(t) {
      if (t === 0) return 0;
      if (t === 1) return 1;
      return t < 0.5 ? Math.pow(2, 20*t - 10)/2 : (2 - Math.pow(2, -20*t + 10))/2;
    }
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

  // -----------------------------------------------------------------------
  // Layer construction: resolve once, instantiate per render.
  //
  // Resolving a layer's props (accessor strings -> functions, @@binary ->
  // typed arrays, extensions, easing, pick handlers, meshes) is cached per
  // source props object, the entries of instance.lastLayers. Re-rendering the
  // same object -- every animation frame, a tab show, a visibility toggle of
  // another layer -- then hands deck.gl the SAME functions and data, so it
  // does not recompute attributes or re-upload buffers. A patched layer is a
  // new object and is resolved afresh. Resolution works on a clone, so the
  // cached source is never mutated.
  // -----------------------------------------------------------------------
  var _resolvedLayerCache = new WeakMap();

  function buildDeckLayers(layersData, targetId) {
    var out = [];
    for (var i = 0; i < layersData.length; i++) {
      var layer = instantiateLayer(resolveLayerCached(layersData[i], targetId));
      if (layer) out.push(layer);
    }
    return out;
  }

  function resolveLayerCached(lp, targetId) {
    var hit = lp && typeof lp === 'object' ? _resolvedLayerCache.get(lp) : null;
    if (hit && hit.targetId === targetId) return hit.resolved;
    var resolved = resolveLayerProps(cloneLayer(lp), targetId);
    if (lp && typeof lp === 'object') {
      _resolvedLayerCache.set(lp, { targetId: targetId, resolved: resolved });
    }
    return resolved;
  }

  // Per-render values that must not be cached: the current value of each
  // @@animate prop and the rasterised SVG icon atlas (it may finish loading
  // after the layer was first resolved). `extra` overrides (e.g. currentTime).
  function instantiateLayer(resolved, extra) {
    if (!resolved) return null;
    var props = Object.assign({}, resolved);
    var anim = resolved._animConfigs;
    if (anim) {
      for (var key in anim) props[key] = window[anim[key].globalKey];
    }
    if (typeof props.iconAtlas === 'string'
        && props.iconAtlas.indexOf('data:image/svg+xml') === 0
        && _svgAtlasCache[props.iconAtlas]) {
      props.iconAtlas = _svgAtlasCache[props.iconAtlas];
    }
    if (extra) Object.assign(props, extra);
    var LayerClass = props._LayerClass;
    delete props._LayerClass;
    return new LayerClass(props);
  }

  // Everything about a layer that does not change from frame to frame.
  // Returns the props object (with the class in _LayerClass), or null.
  function resolveLayerProps(layerProps, targetId) {
    {
      resolveAccessors(layerProps);
      resolveExtensions(layerProps);
      resolveBinaryAttributes(layerProps);

      // Detect @@animate markers and extract animation configs (v1.7.0)
      const animConfigs = {};
      for (const key of Object.keys(layerProps)) {
        const val = layerProps[key];
        if (val && typeof val === 'object' && val['@@animate'] === true) {
          // Replace with accessor that reads the animated global
          const globalKey = '_deckgl_anim_' + targetId + '_' + val.prop;
          animConfigs[key] = {
            prop: val.prop,
            speed: val.speed || 1,
            loop: val.loop !== false,
            rangeMin: val.range_min != null ? val.range_min : 0,
            rangeMax: val.range_max != null ? val.range_max : 360,
            globalKey: globalKey,
          };
          if (window[globalKey] === undefined) {
            window[globalKey] = val.range_min != null ? val.range_min : 0;
          }
          // Record the key so disposeMap() removes exactly this map's
          // globals (a prefix match on "map" also caught "map_2").
          var owner = mapInstances[targetId];
          if (owner) (owner._animGlobals = owner._animGlobals || {})[globalKey] = true;
          // The current value is filled in by instantiateLayer() on every
          // render as a plain number; deck.gl sees it change by value.
          layerProps[key] = window[globalKey];
        }
      }
      if (Object.keys(animConfigs).length > 0) {
        layerProps._animConfigs = animConfigs;
      }

      // Resolve @@easing in transitions specs (v0.8.0)
      if (layerProps.transitions) {
        for (const prop in layerProps.transitions) {
          const tSpec = layerProps.transitions[prop];
          if (tSpec && tSpec['@@easing']) {
            tSpec.easing = EASINGS[tSpec['@@easing']] || function(t) { return t; };
            delete tSpec['@@easing'];
          }
        }
      }

      // Set up pick handling for non-raster layers
      if (!RASTER_TYPES.has(layerProps.type) && layerProps.pickable !== false) {
        // Keep '3d' (depth picking, deck.gl >= 9.3); only fill in the default.
        if (layerProps.pickable !== '3d') layerProps.pickable = true;

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

            // Read tooltip config from the live instance instead of the
            // build-time closure, so updates take effect without rebuilding layers.
            const currentTooltip = (mapInstances[targetId] || {}).tooltipConfig;
            if (currentTooltip && currentTooltip.html) {
              const tooltipEl = getOrCreateTooltipEl(targetId);
              if (!tooltipEl) return;  // container gone — skip tooltip
              if (info.object) {
                const src = info.object.properties || info.object;
                tooltipEl.innerHTML = sanitizeHtml(interpolateTemplate(currentTooltip.html, src));
                tooltipEl.style.cssText = '';
                tooltipEl.style.display = 'block';
                tooltipEl.style.left = (info.x || 0) + 'px';
                tooltipEl.style.top = (info.y || 0) + 'px';
                if (currentTooltip.style) {
                  Object.assign(tooltipEl.style, currentTooltip.style);
                }
              } else {
                tooltipEl.style.display = 'none';
              }
            }
          };
        }
      }

      const LayerClass = deck[layerProps.type] || deck['_' + layerProps.type];
      if (!LayerClass) {
        console.warn('[shiny_deckgl] Unknown layer type: ' + layerProps.type + ' — skipped');
        return null;
      }

      // SimpleMeshLayer: resolve @@CubeGeometry / @@SphereGeometry mesh
      const isSimpleMesh = layerProps.type === 'SimpleMeshLayer';
      const meshIsBuiltin = isSimpleMesh
        && typeof layerProps.mesh === 'string'
        && layerProps.mesh.startsWith('@@')
        && layerProps.mesh !== '@@CustomGeometry';
      if (meshIsBuiltin) {
        const geoName = layerProps.mesh.slice(2);
        if (typeof luma !== 'undefined' && luma[geoName]) {
          layerProps.mesh = new luma[geoName]();
        } else {
          console.warn('[shiny_deckgl] Unknown luma geometry: ' + geoName);
        }
      }

      // SimpleMeshLayer: decode binary-encoded mesh arrays (if present)
      if (isSimpleMesh) {
        for (const key of ['_meshPositions', '_meshIndices', '_meshNormals', '_meshColors']) {
          const val = layerProps[key];
          if (val && typeof val === 'object' && val['@@binary']) {
            try {
              layerProps[key] = decodeBinaryValue(val);
            } catch (err) {
              console.warn('[shiny_deckgl] Failed to decode binary mesh attr ' + key + ':', err);
              delete layerProps[key];
            }
          }
        }
      }

      // SimpleMeshLayer: build mesh object from inline vertex data.
      // Builds a loaders.gl-compatible plain mesh object that deck.gl
      // internally wraps in a luma.Geometry.
      if (isSimpleMesh && layerProps.mesh === '@@CustomGeometry') {
        const pos = layerProps._meshPositions;
        const idx = layerProps._meshIndices;
        const nrm = layerProps._meshNormals;
        const col = layerProps._meshColors;

        /** Ensure value is the expected TypedArray, converting plain arrays. */
        function ensureTyped(val, ArrayCtor) {
          return (val instanceof ArrayCtor) ? val : new ArrayCtor(val);
        }

        if (pos && idx) {
          try {
            const numVerts = pos.length / 3;
            const meshObj = {
              attributes: {
                POSITION: {value: ensureTyped(pos, Float32Array), size: 3},
              },
              indices: {value: ensureTyped(idx, Uint32Array)},
            };
            if (nrm && nrm.length > 0) {
              meshObj.attributes.NORMAL = {value: ensureTyped(nrm, Float32Array), size: 3};
            }
            if (col && col.length > 0) {
              const colorSize = numVerts > 0 ? Math.round(col.length / numVerts) : 3;
              meshObj.attributes.COLOR_0 = {value: ensureTyped(col, Float32Array), size: colorSize};
            }
            layerProps.mesh = meshObj;
            console.log('[shiny_deckgl] Built custom mesh: ' +
              numVerts + ' vertices, ' + (idx.length / 3) + ' triangles');
          } catch (e) {
            console.error('[shiny_deckgl] Failed to build custom mesh:', e);
            layerProps.mesh = null;
          }
        } else {
          console.warn('[shiny_deckgl] CustomGeometry requires _meshPositions and _meshIndices');
          layerProps.mesh = null;
        }
        // Clean up temporary props so deck.gl doesn't choke on them
        delete layerProps._meshPositions;
        delete layerProps._meshIndices;
        delete layerProps._meshNormals;
        delete layerProps._meshColors;
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
            let bboxStr;
            if (epsg === '3857') {
              bboxStr = [
                lonToMercX(west), latToMercY(south),
                lonToMercX(east), latToMercY(north)
              ].join(',');
            } else {
              // EPSG:4326 or other geographic CRS — use lon/lat directly
              bboxStr = [west, south, east, north].join(',');
            }
            const url = urlTemplate.replace(WMS_BBOX_RE, bboxStr);
            return fetch(url, { signal: tile.signal })
              .then(function (r) {
                if (!r.ok) return null;
                const ct = (r.headers.get('content-type') || '').toLowerCase();
                // WMS servers may return XML errors with 200 status
                if (ct.indexOf('xml') !== -1 || ct.indexOf('text') !== -1) return null;
                return r.blob();
              })
              .then(function (blob) {
                if (!blob || blob.size === 0) return null;
                return createImageBitmap(blob);
              })
              .catch(function (err) {
                // Log fetch/decode failures for debugging (ignore abort signals)
                if (err && err.name !== 'AbortError') {
                  console.warn('[shiny_deckgl] WMS tile fetch failed:', err.message || err);
                }
                return null;
              });
          };
          // Remove the raw URL so TileLayer doesn't try its own fetch
          delete layerProps.data;
        }
      }

      // The rasterised SVG icon atlas is swapped in by instantiateLayer().
      layerProps._LayerClass = LayerClass;
      return layerProps;
    }
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
    const heads = [];
    for (let i = 0; i < tripsData.length; i++) {
      const trip = tripsData[i];
      const path = trip.path;
      if (!path || path.length < 2) continue;

      let pos = null;
      let angle = 0; // degrees for deck.gl getAngle (billboard:false)
      for (let j = 0; j < path.length - 1; j++) {
        const t0 = path[j][2];
        const t1 = path[j + 1][2];
        if (currentTime >= t0 && currentTime <= t1) {
          const frac = (t1 !== t0) ? (currentTime - t0) / (t1 - t0) : 0;
          const dx = path[j + 1][0] - path[j][0];
          const dy = path[j + 1][1] - path[j][1];
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
            const dx0 = path[1][0] - path[0][0];
            const dy0 = path[1][1] - path[0][1];
            angle = Math.atan2(dy0, dx0) * 180 / Math.PI;
          }
        } else {
          const last = path[path.length - 1];
          pos = [last[0], last[1]];
          if (path.length >= 2) {
            const prev = path[path.length - 2];
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

  // -----------------------------------------------------------------------
  // SVG atlas rasteriser — deck.gl needs a raster texture, not raw SVG
  // -----------------------------------------------------------------------
  var _svgAtlasCache = {};

  /**
   * If *src* is an SVG data-URI, rasterise it to an off-screen canvas and
   * return a Promise that resolves to the canvas.  The result is cached so
   * subsequent frames reuse the same object.  Non-SVG sources are returned
   * as-is (wrapped in a resolved promise).
   */
  function rasteriseIconAtlas(src) {
    if (typeof src !== 'string' || src.indexOf('data:image/svg+xml') !== 0) {
      return Promise.resolve(src);
    }
    if (_svgAtlasCache[src]) return Promise.resolve(_svgAtlasCache[src]);

    return new Promise(function (resolve) {
      var img = new Image();
      img.onload = function () {
        var canvas = document.createElement('canvas');
        canvas.width = img.naturalWidth || img.width;
        canvas.height = img.naturalHeight || img.height;
        canvas.getContext('2d').drawImage(img, 0, 0);
        _svgAtlasCache[src] = canvas;
        resolve(canvas);
      };
      img.onerror = function () {
        console.warn('[shiny_deckgl] Failed to rasterise SVG atlas, using raw URI:', src.substring(0, 80));
        resolve(src);           // fall back to the raw data-URI
      };
      img.src = src;
    });
  }

  // -----------------------------------------------------------------------
  // Property animation loop (v1.7.0)
  // -----------------------------------------------------------------------
  // -----------------------------------------------------------------------
  // Rendering and the per-map frame loop.
  //
  // renderLayers() is the one place deck.gl layers are built from
  // instance.lastLayers. It applies the current animation state -- each
  // TripsLayer's currentTime (running or paused) plus its head icons, and
  // the @@animate values -- so every render path (updates, visibility,
  // legend toggles, tab shows, animation frames) draws the same thing.
  //
  // One requestAnimationFrame loop per map advances both the trips clock and
  // the property animations, then renders. It runs only while something is
  // animating. There used to be one loop per animation kind, each setting
  // the whole layer list, so a map with both flickered between them.
  // -----------------------------------------------------------------------

  function tripsTime(ta) {
    if (!ta) return 0;
    if (ta.running) return (performance.now() - ta.startedAt) / 1000 + (ta.timeOffset || 0);
    return ta.pausedAt || 0;
  }

  // Rebuilt every frame on purpose: the head positions move each frame, so
  // new accessors (and deck.gl recomputing their attributes) are correct.
  function headIconLayer(lp, hi, currentTime) {
    var atlas = hi._rasterAtlas || hi.iconAtlas;
    // An SVG atlas is drawn once rasterised (see startTripsAnimation).
    if (typeof atlas === 'string' && atlas.indexOf('data:image/svg+xml') === 0) return null;
    var heads = interpolateTripHeads(lp.data, currentTime, hi.iconField || 'species');
    if (heads.length === 0) return null;
    var props = {
      id: (lp.id || 'trips') + '_heads',
      data: heads,
      iconAtlas: atlas,
      iconMapping: hi.iconMapping,
      getPosition: function (d) { return d.position; },
      getIcon: function (d) { return d.icon; },
      getColor: function (d) { return d.color; },
      getAngle: function (d) { return d.angle || 0; },
      getSize: hi.getSize || 24,
      sizeScale: hi.sizeScale || 1,
      sizeMinPixels: hi.sizeMinPixels || 10,
      sizeMaxPixels: hi.sizeMaxPixels || 64,
      billboard: false,
      pickable: false,
      visible: lp.visible !== false,
    };
    if (lp.coordinateSystem != null) {
      props.coordinateSystem = normaliseCoordinateSystem(lp.coordinateSystem);
    }
    if (lp.coordinateOrigin != null) props.coordinateOrigin = lp.coordinateOrigin;
    return new deck.IconLayer(props);
  }

  function renderLayers(instance, targetId) {
    var ta = instance.tripsAnimation;
    var trips = {};
    if (ta && ta.configs) {
      var t = tripsTime(ta);
      for (var c = 0; c < ta.configs.length; c++) {
        var cfg = ta.configs[c];
        trips[cfg.layerId] = { cfg: cfg, currentTime: (t * cfg.speed) % cfg.loopLength };
      }
    }
    var out = [];
    var layers = instance.lastLayers || [];
    for (var i = 0; i < layers.length; i++) {
      var lp = layers[i];
      var tr = lp && trips[lp.id];
      var layer = instantiateLayer(resolveLayerCached(lp, targetId),
                                   tr ? { currentTime: tr.currentTime } : null);
      if (!layer) continue;
      out.push(layer);
      if (tr && tr.cfg.headIcons) {
        var heads = headIconLayer(lp, tr.cfg.headIcons, tr.currentTime);
        if (heads) out.push(heads);
      }
    }
    return out;
  }

  function renderNow(instance, targetId) {
    instance.overlay.setProps({ layers: renderLayers(instance, targetId) });
    instance.map.triggerRepaint();
  }

  function isAnimating(instance) {
    return !!((instance.tripsAnimation && instance.tripsAnimation.running)
      || (instance.animations && Object.keys(instance.animations).length));
  }

  function ensureFrameLoop(instance, targetId) {
    if (instance._frameRaf || !isAnimating(instance)) return;
    instance._lastFrameTime = performance.now();
    function tick(now) {
      instance._frameRaf = null;
      if (mapInstances[targetId] !== instance || !isAnimating(instance)) return;
      var dt = (now - instance._lastFrameTime) / 1000;
      instance._lastFrameTime = now;
      advancePropertyAnimations(instance, dt);
      // setProps alone: deck.gl redraws itself. renderNow() would also make
      // MapLibre repaint the whole basemap on every frame.
      instance.overlay.setProps({ layers: renderLayers(instance, targetId) });
      instance._frameRaf = requestAnimationFrame(tick);
    }
    instance._frameRaf = requestAnimationFrame(tick);
  }

  function advancePropertyAnimations(instance, dt) {
    var anims = instance.animations || {};
    for (var layerId in anims) {
      var layerConfigs = anims[layerId];
      for (var propKey in layerConfigs) {
        var cfg = layerConfigs[propKey];
        var current = window[cfg.globalKey];
        var val = (current != null ? current : cfg.rangeMin) + cfg.speed * dt;
        if (cfg.loop) {
          var range = cfg.rangeMax - cfg.rangeMin;
          val = cfg.rangeMin + ((val - cfg.rangeMin) % range);
          if (val < cfg.rangeMin) val += range; // handle negative speed
        } else {
          val = Math.min(Math.max(val, cfg.rangeMin), cfg.rangeMax);
        }
        window[cfg.globalKey] = val;
      }
    }
  }

  function startPropertyAnimations(instance, mapId) {
    // Collect animation configs from all layers by scanning for @@animate
    // markers in the raw layer props (instance.lastLayers).
    const allConfigs = {};
    for (let i = 0; i < instance.lastLayers.length; i++) {
      const lp = instance.lastLayers[i];
      const configs = {};
      for (const key of Object.keys(lp)) {
        const val = lp[key];
        if (val && typeof val === 'object' && val['@@animate'] === true) {
          const globalKey = '_deckgl_anim_' + mapId + '_' + val.prop;
          configs[key] = {
            prop: val.prop,
            speed: val.speed || 1,
            loop: val.loop !== false,
            rangeMin: val.range_min != null ? val.range_min : 0,
            rangeMax: val.range_max != null ? val.range_max : 360,
            globalKey: globalKey,
          };
          // Ensure window global is initialised
          if (window[globalKey] === undefined) {
            window[globalKey] = val.range_min != null ? val.range_min : 0;
          }
          (instance._animGlobals = instance._animGlobals || {})[globalKey] = true;
        }
      }
      if (Object.keys(configs).length > 0) {
        allConfigs[lp.id] = configs;
      }
    }
    if (Object.keys(allConfigs).length === 0) return;
    // Merge into existing animations (don't overwrite in-flight configs)
    instance.animations = Object.assign(instance.animations || {}, allConfigs);
    ensureFrameLoop(instance, mapId);
  }

  function cleanupAnimations(instance, mapId, currentLayerIds) {
    if (!instance.animations) return;
    // Remove configs for layers that no longer exist; the frame loop stops
    // by itself once nothing is animating.
    for (const layerId of Object.keys(instance.animations)) {
      if (!currentLayerIds.has(layerId)) {
        const configs = instance.animations[layerId];
        for (const propKey of Object.keys(configs)) {
          delete window[configs[propKey].globalKey];
        }
        delete instance.animations[layerId];
      }
    }
  }

  function scanTripsConfigs(layers) {
    var configs = [];  // {layerId, loopLength, speed, headIcons?}
    for (var i = 0; i < layers.length; i++) {
      var lp = layers[i];
      if (lp.type === 'TripsLayer' && lp._tripsAnimation) {
        var cfg = {
          layerId: lp.id,
          loopLength: lp._tripsAnimation.loopLength || 1800,
          speed: lp._tripsAnimation.speed || 1,
        };
        if (lp._tripsHeadIcons) cfg.headIcons = lp._tripsHeadIcons;
        configs.push(cfg);
      }
    }
    return configs;
  }

  function startTripsAnimation(instance, targetId, fromUpdate) {
    var prev = instance.tripsAnimation;
    if (!shouldStartTripsAnimation(instance, fromUpdate === true)) {
      // Paused: keep the frozen time, but follow the updated layers so the
      // paused frame (and its head icons) still matches what is drawn.
      if (prev && !prev.running) prev.configs = scanTripsConfigs(instance.lastLayers);
      return;
    }
    if (fromUpdate !== true) instance._tripsPaused = false;
    // Carry the animation time over: from a pause, or -- for a layer update
    // -- from the running clock, which used to snap back to 0 on every
    // update()/partial_update().
    var carried = 0;
    if (prev && !prev.running && prev.pausedAt != null) carried = prev.pausedAt;
    else if (fromUpdate === true && prev && prev.running) carried = tripsTime(prev);
    var prevSpeed = prev ? prev.speed : null;

    var configs = scanTripsConfigs(instance.lastLayers);
    if (configs.length === 0) { instance.tripsAnimation = null; return; }

    // Time is multiplied by speed, so after a speed change rescale the
    // carried-over time: the trails then continue from the same point.
    var speed0 = configs[0].speed;
    if (prevSpeed && speed0 && prevSpeed !== speed0) carried = carried * prevSpeed / speed0;

    instance.tripsAnimation = {
      configs: configs, running: true, speed: speed0,
      startedAt: performance.now(), timeOffset: carried, pausedAt: null,
    };
    ensureFrameLoop(instance, targetId);

    // Rasterise SVG head-icon atlases; the heads are drawn once ready.
    configs.forEach(function (cfg) {
      var hi = cfg.headIcons;
      if (!hi || !hi.iconAtlas || hi._rasterAtlas) return;
      rasteriseIconAtlas(hi.iconAtlas).then(function (raster) {
        hi._rasterAtlas = raster;
      }).catch(function (err) {
        console.error('[shiny_deckgl] TripsLayer head-icon atlas failed for "' + targetId + '":', err);
      });
    });
  }

  function pauseTripsAnimation(instance) {
    // Remember that the pause was deliberate, so a later layer update does
    // not quietly start the animation playing again.
    instance._tripsPaused = true;
    var ta = instance.tripsAnimation;
    if (ta && ta.running) {
      ta.pausedAt = tripsTime(ta);
      ta.running = false;
    }
  }

  function stopTripsAnimation(instance) {
    // Full stop: the next start begins from 0.
    instance.tripsAnimation = null;
  }

  // -----------------------------------------------------------------------
  // Ensure instance helper — lazy init with deferred message queue
  // -----------------------------------------------------------------------
  // Messages that arrive for maps in hidden tabs are queued here and
  // replayed when the tab becomes visible (see shown.bs.tab handler).
  var _deferredMessages = {};  // mapId → [{handler, payload}, ...]

  // ensureInstance() removed — addDeferrable() already guarantees the map is
  // initialised (or the message is deferred) before invoking the handler.
  // Handlers now use mapInstances[id] directly.

  // Queue a Shiny message for a deferred (hidden-tab) map.
  // Layer messages a later full deck_update makes redundant.
  var SUPERSEDED_BY_UPDATE = { deck_update: 1, deck_partial_update: 1, deck_layer_visibility: 1 };
  var DEFERRED_QUEUE_LIMIT = 1000;

  function deferMessage(mapId, handler, payload) {
    if (!_deferredMessages[mapId]) _deferredMessages[mapId] = [];
    var queue = _deferredMessages[mapId];
    // A full deck_update replaces every layer, so the layer messages queued
    // right before it are redundant -- a timer-driven update() to a hidden
    // map otherwise queued every full payload. Only the tail is merged, so
    // the order relative to other messages is kept; props the new update
    // doesn't set (widgets, effects, viewState, ...) are carried over from
    // the updates it replaces.
    if (handler === 'deck_update') {
      var merged = payload;
      while (queue.length && SUPERSEDED_BY_UPDATE[queue[queue.length - 1].handler]) {
        var prev = queue.pop();
        if (prev.handler === 'deck_update') {
          merged = Object.assign({}, prev.payload, merged);
          // The newest update decides the transport: drop the other form.
          if (payload.url) delete merged.layers; else delete merged.url;
        }
      }
      payload = merged;
    }
    queue.push({handler: handler, payload: payload});
    if (queue.length > DEFERRED_QUEUE_LIMIT) {
      queue.splice(0, queue.length - DEFERRED_QUEUE_LIMIT);
      if (!queue._warned) {
        queue._warned = true;
        console.warn('[shiny_deckgl] More than ' + DEFERRED_QUEUE_LIMIT + ' messages queued for hidden map "' +
          mapId + '"; dropping the oldest.');
      }
    }
  }

  // Registered handler functions — populated by addDeferrable() below.
  var _handlerFns = {};

  // Replay all deferred messages for a map after it has been initialised.
  // Each handler is wrapped in try/catch so one failure doesn't abort the rest.
  function replayDeferredMessages(mapId) {
    var queue = _deferredMessages[mapId];
    if (!queue || !queue.length) return;
    // Only consume the queue if the map was successfully initialised;
    // otherwise keep it for a future retry on the next tab show.
    if (!mapInstances[mapId]) {
      console.warn('[shiny_deckgl] replayDeferredMessages: map "' + mapId +
        '" not initialised — keeping ' + queue.length + ' queued messages');
      return;
    }
    delete _deferredMessages[mapId];
    queue.forEach(function (msg) {
      var fn = _handlerFns[msg.handler];
      if (fn) {
        try {
          fn(msg.payload);
        } catch (e) {
          console.error('[shiny_deckgl] Deferred "' + msg.handler +
            '" for map "' + mapId + '" failed during replay:', e);
        }
      } else {
        console.warn('[shiny_deckgl] No handler for deferred "' + msg.handler + '"');
      }
    });
  }

  // Wrap a Shiny message handler to defer messages for maps in hidden tabs.
  // Messages are queued and replayed when the tab becomes visible.
  // HTTP transport (v1.13.0): update(transport="http"/"auto") sends
  // {id, url, seq, bytes}; the JSON is fetched here and applied through
  // onDeckUpdate. The fetch is remembered on the instance so that layer
  // messages arriving meanwhile (partial_update, layer_visibility,
  // set_widgets, another update) run after it, in order.
  var FETCH_ORDERED = { deck_update: 1, deck_partial_update: 1, deck_layer_visibility: 1, deck_set_widgets: 1 };

  function fetchPayload(instance, payload) {
    var p = (instance._pendingFetch || Promise.resolve()).then(function () {
      return fetch(payload.url, { cache: 'no-store' }).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      }).then(function (full) { onDeckUpdate(full); });
    }).catch(function (e) {
      console.error('[shiny_deckgl] deck_update: fetching ' + payload.url + ' failed:', e);
    }).then(function () {
      if (instance._pendingFetch === p) instance._pendingFetch = null;
    });
    instance._pendingFetch = p;
    return p;
  }

  function addDeferrable(name, fn) {
    // Guard live handler execution so a throw in one handler cannot abort the
    // whole Shiny custom-message callback (mirrors replayDeferredMessages).
    function runNow(payload) {
      try {
        fn(payload);
      } catch (e) {
        console.error('[shiny_deckgl] Handler "' + name + '" failed:', e);
      }
    }
    function runFn(payload) {
      var inst = payload && payload.id ? mapInstances[payload.id] : null;
      if (inst && inst._pendingFetch && FETCH_ORDERED[name]) {
        // A fetched deck_update is still in flight: keep the order, and clear
        // the chain once this (last) link has run so later messages run at once.
        var next = inst._pendingFetch.then(function () { runNow(payload); }).then(function () {
          if (inst._pendingFetch === next) inst._pendingFetch = null;
        });
        inst._pendingFetch = next;
        return;
      }
      runNow(payload);
    }
    _handlerFns[name] = fn;
    Shiny.addCustomMessageHandler(name, function (payload) {
      if (!payload || !payload.id) { runFn(payload); return; }
      // If map is already initialised, run immediately
      if (mapInstances[payload.id]) { runFn(payload); return; }
      // Map not initialised — check if it's in a hidden tab
      var el = document.getElementById(payload.id);
      if (el && !isInVisibleTab(el)) {
        deferMessage(payload.id, name, payload);
        return;
      }
      // Visible but not init'd — try to init if CDN libs are ready
      if (el) {
        if (typeof maplibregl === 'undefined' || typeof deck === 'undefined') {
          // CDN not loaded yet — defer instead of destroying the DOM
          deferMessage(payload.id, name, payload);
          return;
        }
        safeInitMap(el);
        if (mapInstances[payload.id]) { runFn(payload); return; }
      }
      console.warn('[shiny_deckgl] Map "' + payload.id + '" not found — "' + name + '" ignored');
    });
  }

  // -----------------------------------------------------------------------
  // deck_update — main layer push
  // -----------------------------------------------------------------------
  function onDeckUpdate(payload) {
    if (!payload || !payload.id) return;
    const targetId = payload.id;
    const instance = mapInstances[targetId];
    if (!instance) {
      console.warn('[shiny_deckgl] deck_update: map "' + targetId + '" not found');
      return;
    }
    // HTTP transport (v1.13.0): the message is only a pointer to the payload.
    if (payload.url) { fetchPayload(instance, payload); return; }

    const { map, overlay } = instance;

    // Handle view state updates (flyTo if duration > 0, else jumpTo)
    if (payload.viewState) {
      const opts = buildCameraOptions(payload.viewState);
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
    if (instance._legendWidget) instance._legendWidget._refresh();

    // Pre-rasterise any SVG icon atlases so the cache is warm before
    // buildDeckLayers runs (it checks the cache synchronously).
    var svgAtlasPreloads = [];
    for (let li = 0; li < layersData.length; li++) {
      var la = layersData[li].iconAtlas;
      if (la && typeof la === 'string' && la.indexOf('data:image/svg+xml') === 0) {
        svgAtlasPreloads.push(rasteriseIconAtlas(la));
      }
    }

    // Wait for all SVG atlases to rasterise (instant if cache hit or none).
    var updateGen = claimUpdateGeneration(instance);
    Promise.all(svgAtlasPreloads).then(function () {
    // A newer update started while we were rasterising: its layers are the
    // ones in instance.lastLayers, so drop this stale render.
    if (isStaleUpdate(instance, updateGen)) return;
    // The map was disposed (e.g. its output re-rendered) while the atlases
    // loaded: don't touch the finalized overlay or start animation loops.
    if (mapInstances[targetId] !== instance) return;
    // Render the cache as it is now, not the array captured above: a
    // visibility change, legend toggle or partial update may have patched
    // it (and rendered) while the atlases were loading.
    const overlayProps = { layers: renderLayers(instance, targetId) };

    // Effects (lighting, post-processing)
    const effects = buildEffects(payload.effects);
    if (effects) overlayProps.effects = effects;

    // Views (MapView, OrthographicView, FirstPersonView)
    const views = buildViews(payload.views);
    if (views !== undefined) overlayProps.views = views;

    // Deck-level props (v0.7.0)
    if (payload.pickingRadius !== undefined) overlayProps.pickingRadius = payload.pickingRadius;
    if (payload.useDevicePixels !== undefined) overlayProps.useDevicePixels = payload.useDevicePixels;
    if (payload._animate !== undefined) overlayProps._animate = payload._animate;

    // Widgets (v0.8.0)
    dropImplicitNavigation(mapInstances[targetId], payload.widgets);
    const widgets = buildWidgets(payload.widgets, targetId);
    if (widgets) overlayProps.widgets = widgets;

    overlay.setProps(overlayProps);
    map.triggerRepaint();

    // Start/stop TripsLayer animation if needed (v0.9.0).
    // fromUpdate=true: a layer update must not resurrect a paused animation.
    startTripsAnimation(instance, targetId, true);

    // Start property animations if any layers have @@animate markers (v1.7.0)
    startPropertyAnimations(instance, targetId);
    // Clean up animations for removed layers
    const currentIds = new Set(instance.lastLayers.map(function (l) { return l.id; }));
    cleanupAnimations(instance, targetId, currentIds);
    }).catch(function (err) {
      console.error('[shiny_deckgl] deck_update rendering failed for "' + targetId + '":', err);
    }); // end SVG atlas preload .then()
  }
  addDeferrable("deck_update", onDeckUpdate);

  // -----------------------------------------------------------------------
  // deck_partial_update — lightweight layer patch (merge into cached layers)
  // -----------------------------------------------------------------------
  addDeferrable("deck_partial_update", function (payload) {
    if (!payload || !payload.id) return;
    const targetId = payload.id;
    const instance = mapInstances[targetId];
    if (!instance) return;

    const patches = payload.layers || [];
    if (!patches.length) return;

    // Build lookup of cached layers by id
    const cached = instance.lastLayers || [];
    const cacheMap = {};
    cached.forEach(function (lp) { cacheMap[lp.id] = lp; });

    // Merge each patch into cache: shallow-merge existing, append new
    patches.forEach(function (patch) {
      if (cacheMap[patch.id]) {
        cacheMap[patch.id] = Object.assign({}, cacheMap[patch.id], patch);
      } else {
        cacheMap[patch.id] = patch;
      }
    });

    // Rebuild ordered array (preserve original order, new layers at end)
    const mergedIds = new Set();
    const merged = [];
    cached.forEach(function (lp) {
      if (cacheMap[lp.id]) {
        merged.push(cacheMap[lp.id]);
        mergedIds.add(lp.id);
      }
    });
    patches.forEach(function (patch) {
      if (!mergedIds.has(patch.id)) {
        merged.push(cacheMap[patch.id]);
        mergedIds.add(patch.id);
      }
    });

    // Update the canonical cache synchronously so rapid consecutive partial
    // updates merge against the latest patch even while SVG atlases preload.
    instance.lastLayers = merged;
    if (instance._legendWidget) instance._legendWidget._refresh();
    instance._partialUpdateGen = (instance._partialUpdateGen || 0) + 1;
    var partialUpdateGen = instance._partialUpdateGen;

    // Pre-rasterise SVG atlases before building layers (same as deck_update)
    var svgAtlasPreloads = [];
    for (var li = 0; li < merged.length; li++) {
      var la = merged[li].iconAtlas;
      if (la && typeof la === 'string' && la.indexOf('data:image/svg+xml') === 0) {
        svgAtlasPreloads.push(rasteriseIconAtlas(la));
      }
    }

    Promise.all(svgAtlasPreloads).then(function () {
      if (partialUpdateGen !== instance._partialUpdateGen) return;
      if (mapInstances[targetId] !== instance) return;  // disposed meanwhile
      // As in deck_update: render the current cache, which may have been
      // patched again while the atlases were loading.
      renderNow(instance, targetId);

      // Restart TripsLayer animation if patched layers include one (v0.9.0).
      // fromUpdate=true: see deck_update.
      startTripsAnimation(instance, targetId, true);

      // Property animations: start for new animated layers, clean up removed ones
      startPropertyAnimations(instance, targetId);
      const currentLayerIds = new Set(instance.lastLayers.map(function (lp) { return lp.id; }));
      cleanupAnimations(instance, targetId, currentLayerIds);
    }).catch(function (err) {
      console.error('[shiny_deckgl] deck_partial_update rendering failed for "' + targetId + '":', err);
    });
  });

  // -----------------------------------------------------------------------
  // deck_trips_control — pause / resume / reset TripsLayer animation
  // -----------------------------------------------------------------------
  // payload: { id: "map_id", action: "pause" | "resume" | "reset" }
  addDeferrable("deck_trips_control", function (payload) {
    if (!payload || !payload.id) return;
    const targetId = payload.id;
    const instance = mapInstances[targetId];
    if (!instance) return;
    const action = payload.action || 'pause';

    if (action === 'pause') {
      pauseTripsAnimation(instance);
    } else if (action === 'resume') {
      // Resume from where we paused
      startTripsAnimation(instance, targetId);
    } else if (action === 'reset') {
      // Full stop then restart from time 0
      stopTripsAnimation(instance);
      startTripsAnimation(instance, targetId);
    } else {
      console.warn('[shiny_deckgl] deck_trips_control: unknown action "' + action + '" — expected "pause", "resume", or "reset"');
    }
  });

  // -----------------------------------------------------------------------
  // deck_set_widgets — update widgets without resending layers (v0.8.0)
  // -----------------------------------------------------------------------
  addDeferrable("deck_set_widgets", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;
    dropImplicitNavigation(instance, payload.widgets);
    const widgets = buildWidgets(payload.widgets, payload.id);
    if (widgets) {
      instance.overlay.setProps({ widgets: widgets });
      instance.map.triggerRepaint();
    }
  });

  // -----------------------------------------------------------------------
  // deck_fly_to — smooth flyTo camera transition (v0.8.0)
  // -----------------------------------------------------------------------
  addDeferrable("deck_fly_to", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;
    const vs = payload.viewState || {};
    const opts = {
      center: [vs.longitude != null ? vs.longitude : 0, vs.latitude != null ? vs.latitude : 0],
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
  addDeferrable("deck_ease_to", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;
    const vs = payload.viewState || {};
    const opts = {
      center: [vs.longitude != null ? vs.longitude : 0, vs.latitude != null ? vs.latitude : 0],
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
  addDeferrable("deck_set_controller", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;
    applyController(instance.map, payload.controller);
  });

  // -----------------------------------------------------------------------
  // deck_set_cooperative_gestures — toggle cooperative gestures
  // -----------------------------------------------------------------------
  addDeferrable("deck_set_cooperative_gestures", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;
    const map = instance.map;
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
  addDeferrable("deck_layer_visibility", function (payload) {
    if (!payload || !payload.id) return;
    const targetId = payload.id;
    const instance = mapInstances[targetId];
    if (!instance) return;

    const visMap = payload.visibility || {};
    const patched = instance.lastLayers.map(lp => {
      if (!(lp.id in visMap)) return lp;
      const copy = Object.assign({}, lp);
      copy.visible = visMap[copy.id];
      return copy;
    });
    instance.lastLayers = patched;
    if (instance._legendWidget) instance._legendWidget._refresh();

    renderNow(instance, targetId);
  });

  // -----------------------------------------------------------------------
  // deck_add_drag_marker — draggable MapLibre marker → Shiny input
  // -----------------------------------------------------------------------
  addDeferrable("deck_add_drag_marker", function (payload) {
    if (!payload || !payload.id) return;
    const targetId = payload.id;
    const instance = mapInstances[targetId];
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
  // Swap the basemap style. Shared by deck_set_style and the dark-mode
  // switch, so both get the native-layer warning, the style-change guard
  // and the tracker reset.
  function applyStyle(instance, style, diff) {
    if (!instance || !style) return;
    instance.currentStyle = style;
    if (instance.nativeLayers && Object.keys(instance.nativeLayers).length > 0) {
      console.warn('[shiny_deckgl] set_style will remove all native sources/layers. '
        + 'Re-add them after the style loads.');
    }
    // Guard against whenStyleReady race: mark the map as style-changing so
    // that any Shiny messages arriving between setStyle() and the next
    // 'style.load' event correctly queue instead of running immediately.
    instance.map._deckStyleChanging = true;

    // Clear any previous style-change timeout and style.load handler
    // to avoid stale callbacks when deck_set_style is called rapidly.
    if (instance._styleChangeTimeout) {
      clearTimeout(instance._styleChangeTimeout);
    }
    if (instance._styleLoadHandler) {
      instance.map.off('style.load', instance._styleLoadHandler);
    }

    // Timeout fallback: clear the flag after 30s in case style.load never fires
    // (e.g., network error, invalid style URL, malformed JSON)
    instance._styleChangeTimeout = setTimeout(function () {
      instance._styleChangeTimeout = null;
      instance._styleLoadHandler = null;
      if (instance.map._deckStyleChanging) {
        instance.map._deckStyleChanging = false;
        if (instance.map._deckStyleDrainFn && isStyleReady(instance.map)) {
          // No 'style.load' came (e.g. a diff), but the style is usable:
          // run the queued calls rather than throwing them away.
          console.warn('[shiny_deckgl] No style.load within 30s; running queued calls against the current style');
          instance.map._deckStyleDrainFn();
        } else {
          console.warn('[shiny_deckgl] Style load timed out after 30s, clearing guard flag');
          _clearStyleQueue(instance.map);
        }
      }
    }, 30000);

    instance._styleLoadHandler = function () {
      clearTimeout(instance._styleChangeTimeout);
      instance._styleChangeTimeout = null;
      instance._styleLoadHandler = null;
      instance.map._deckStyleChanging = false;
      // Run calls queued during the swap now, rather than waiting for a later
      // 'idle', which never comes while an animation keeps repainting.
      if (instance.map._deckStyleDrainFn) instance.map._deckStyleDrainFn();
    };
    instance.map.once('style.load', instance._styleLoadHandler);

    // Note: we rely on the 30s timeout for style-load failure recovery.
    // A once('error') handler was removed because MapLibre fires 'error'
    // for unrelated tile/data errors that would prematurely clear the
    // style-change guard and abandon queued callbacks.
    // Always pass diff explicitly: MapLibre diffs by default, which does not
    // match set_style(diff=False). A diff never fires 'style.load' when the
    // style is unchanged, and when it lands after layers were re-added it
    // diffs them away against the bare basemap JSON.
    const styleOpts = { diff: !!diff };
    instance.map.setStyle(style, styleOpts);
    if (diff) settleDiffStyle(instance, style);
    // Clear stale tracker — all native layers/sources are removed by setStyle
    // (unless diff mode preserves them)
    if (!diff) {
      resetNativeLayers(instance);
    }
  }

  addDeferrable("deck_set_style", function (payload) {
    if (!payload || !payload.id) return;
    applyStyle(mapInstances[payload.id], payload.style, !!payload.diff);
  });

  // -----------------------------------------------------------------------
  // deck_set_dark_mode -- dark basemap + dark widgets (v1.13.0)
  // -----------------------------------------------------------------------
  // A Bootstrap dark app sets data-bs-theme="dark" on <html>. With a
  // dark_style= the map swaps its basemap through applyStyle(); with or
  // without one, the map div gets .deckgl-dark (dark deck widgets and
  // legend, see styles.css) and the server hears about it through
  // <id>_dark_mode = {dark, style}.
  function applyDarkMode(instance, mapId, dark) {
    if (!instance) return;
    dark = !!dark;
    var target = dark ? instance.darkStyle : instance.lightStyle;
    if (target && target !== instance.currentStyle) applyStyle(instance, target, false);
    if (instance.el && instance.el.classList) instance.el.classList.toggle('deckgl-dark', dark);
    instance.dark = dark;
    Shiny.setInputValue(mapId + '_dark_mode', { dark: dark, style: instance.currentStyle || null });
  }

  function handleSetDarkMode(payload) {
    if (!payload || !payload.id) return;
    applyDarkMode(mapInstances[payload.id], payload.id, payload.dark);
  }
  addDeferrable("deck_set_dark_mode", handleSetDarkMode);

  // Follow data-bs-theme on <html> (ui.input_dark_mode, or a fixed theme)
  // unless data-follow-dark-mode="false". Returns the observer, or null.
  function watchBootstrapTheme(instance, mapId) {
    var ds = (instance && instance.el && instance.el.dataset) || {};
    if (ds.followDarkMode === 'false' || typeof MutationObserver === 'undefined') return null;
    var root = document.documentElement;
    var observer = new MutationObserver(function () {
      applyDarkMode(instance, mapId, root.getAttribute('data-bs-theme') === 'dark');
    });
    observer.observe(root, { attributes: true, attributeFilter: ['data-bs-theme'] });
    instance._themeObserver = observer;
    return observer;
  }

  // -----------------------------------------------------------------------
  // deck_add_control — add a MapLibre control
  // -----------------------------------------------------------------------
  addDeferrable("deck_add_control", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;

    const spec = {
      type: payload.controlType,
      position: payload.position || 'top-right',
      options: payload.options || {},
    };
    // Same deferral as deck_set_controls, so a legend added right after
    // add_maplibre_layer sees that layer. Controls of other types are kept.
    whenStyleReady(instance.map, function () {
      const others = Object.keys(instance.controls)
        .filter(function (t) { return t !== spec.type; })
        .map(function (t) {
          const c = instance.controls[t];
          return { type: t, position: c.position, options: JSON.parse(c.key)[1] };
        });
      // Re-adding an identical control is kept as is; a changed one replaces.
      applyControls(instance, others.concat([spec]));
    });
  });

  // -----------------------------------------------------------------------
  // deck_remove_control — remove a MapLibre control
  // -----------------------------------------------------------------------
  addDeferrable("deck_remove_control", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;

    const type = payload.controlType;
    if (instance.controls[type]) {
      instance.map.removeControl(instance.controls[type].control);
      delete instance.controls[type];
    }
  });

  // -----------------------------------------------------------------------
  // deck_set_controls — replace all MapLibre controls at once
  // -----------------------------------------------------------------------
  addDeferrable("deck_set_controls", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;

    // Defer until style is loaded so that native sources/layers added
    // via deck_add_source / deck_add_maplibre_layer (which also use
    // whenStyleReady) are present before legend/opacity controls inspect
    // the map style.
    whenStyleReady(instance.map, function() {
      applyControls(instance, payload.controls || []);
    });
  });

  // -----------------------------------------------------------------------
  // deck_fit_bounds — fit map to geographic bounds
  // -----------------------------------------------------------------------
  addDeferrable("deck_fit_bounds", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;

    const bounds = payload.bounds;  // [[sw_lng, sw_lat], [ne_lng, ne_lat]]
    const opts = {};

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
  addDeferrable("deck_add_source", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;

    whenStyleReady(instance.map, function() {
      const map = instance.map;
      const sourceId = payload.sourceId;
      const spec = payload.spec;

      // Remove existing source if present (along with its layers)
      if (map.getSource(sourceId)) {
        const style = map.getStyle();
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
  addDeferrable("deck_add_maplibre_layer", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;

    whenStyleReady(instance.map, function() {
      const map = instance.map;
      const layerSpec = payload.layerSpec;
      const beforeId = payload.beforeId || undefined;

      // Remove existing layer with same id
      if (map.getLayer(layerSpec.id)) {
        map.removeLayer(layerSpec.id);
      }

      map.addLayer(layerSpec, beforeId);
      trackNativeLayer(instance, layerSpec.id, true);
    });
  });

  // -----------------------------------------------------------------------
  // deck_remove_maplibre_layer — remove a native MapLibre layer
  // -----------------------------------------------------------------------
  addDeferrable("deck_remove_maplibre_layer", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;

    whenStyleReady(instance.map, function() {
      if (instance.map.getLayer(payload.layerId)) {
        instance.map.removeLayer(payload.layerId);
        trackNativeLayer(instance, payload.layerId, false);
      }
    });
  });

  // -----------------------------------------------------------------------
  // deck_remove_source — remove a native MapLibre source
  // -----------------------------------------------------------------------
  addDeferrable("deck_remove_source", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
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
  addDeferrable("deck_set_source_data", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;

    whenStyleReady(instance.map, function() {
      const source = instance.map.getSource(payload.sourceId);
      if (source && typeof source.setData === 'function') {
        source.setData(payload.data);
      }
    });
  });

  // -----------------------------------------------------------------------
  // deck_add_image — load a remote image into the map style for symbol layers
  // -----------------------------------------------------------------------
  addDeferrable("deck_add_image", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;
    whenStyleReady(instance.map, function() {
      const map = instance.map;
      const imageId = payload.imageId;
      const url = payload.url;
      const options = {};
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
        const imgData = result && result.data ? result.data : result;
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
  addDeferrable("deck_remove_image", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
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
  addDeferrable("deck_has_image", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;
    whenStyleReady(instance.map, function() {
      const exists = instance.map.hasImage(payload.imageId);
      Shiny.setInputValue(payload.id + '_has_image', {
        imageId: payload.imageId,
        exists: exists
      });
    });
  });

  // -----------------------------------------------------------------------
  // deck_set_paint_property — set paint property on a MapLibre layer
  // -----------------------------------------------------------------------
  addDeferrable("deck_set_paint_property", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;
    whenStyleReady(instance.map, function() {
      instance.map.setPaintProperty(payload.layerId, payload.name, payload.value);
    });
  });

  // -----------------------------------------------------------------------
  // deck_set_layout_property — set layout property on a MapLibre layer
  // -----------------------------------------------------------------------
  addDeferrable("deck_set_layout_property", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;
    whenStyleReady(instance.map, function() {
      instance.map.setLayoutProperty(payload.layerId, payload.name, payload.value);
    });
  });

  // -----------------------------------------------------------------------
  // deck_set_filter — set data-driven filter on a MapLibre layer
  // -----------------------------------------------------------------------
  addDeferrable("deck_set_filter", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;
    whenStyleReady(instance.map, function() {
      instance.map.setFilter(payload.layerId, payload.filter || null);
    });
  });

  // -----------------------------------------------------------------------
  // deck_set_projection — switch between mercator and globe
  // -----------------------------------------------------------------------
  addDeferrable("deck_set_projection", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
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
  addDeferrable("deck_set_terrain", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
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
  addDeferrable("deck_set_sky", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
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
  addDeferrable("deck_add_popup", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;

    const map = instance.map;
    const layerId = payload.layerId;
    const template = payload.template;

    // Store handler references for cleanup
    if (!instance.popupHandlers) instance.popupHandlers = {};

    whenStyleReady(map, function() {
      // Cleanup inside whenStyleReady so both removal and registration
      // are serialized — prevents handler leaks during style swaps.
      if (instance.popupHandlers[layerId]) {
        map.off('click', layerId, instance.popupHandlers[layerId].click);
        map.off('mouseenter', layerId, instance.popupHandlers[layerId].enter);
        map.off('mouseleave', layerId, instance.popupHandlers[layerId].leave);
        delete instance.popupHandlers[layerId];
      }
      const clickHandler = function (e) {
        if (!e.features || !e.features.length) return;
        const props = e.features[0].properties || {};
        const html = sanitizeHtml(interpolateTemplate(template, props));

        const popupOpts = {
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

      const enterHandler = function () {
        map.getCanvas().style.cursor = 'pointer';
      };
      const leaveHandler = function () {
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
  addDeferrable("deck_remove_popup", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance || !instance.popupHandlers) return;

    const layerId = payload.layerId;
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
  // A MapLibre feature reduced to what the server needs (and can serialise).
  function simplifyFeature(f) {
    return {
      type: "Feature",
      geometry: f.geometry,
      properties: f.properties,
      layer: { id: f.layer ? f.layer.id : null },
      source: f.source || null
    };
  }

  // Flatten the basemap and the deck.gl canvas into one image once the map
  // is idle; done({dataUrl, width, height}). Shared by deck_export_image and
  // the exportImage RPC so both paths stay identical.
  function captureMapImage(instance, params, done) {
    const map = instance.map;
    const canvas = map.getCanvas();
    const mimeTypes = { jpeg: 'image/jpeg', png: 'image/png', webp: 'image/webp' };
    const format = mimeTypes[params.format] || 'image/png';
    const quality = params.quality || 0.92;
    function capture() {
      // deck.gl renders into its own canvas unless interleaved, so flatten
      // both before encoding -- otherwise the export is basemap-only.
      var deckCanvas = null;
      try {
        var dk = instance.overlay && (instance.overlay._deck || instance.overlay.deck);
        if (dk && typeof dk.getCanvas === 'function') deckCanvas = dk.getCanvas();
        else if (dk && dk.canvas) deckCanvas = dk.canvas;
      } catch (e) {
        deckCanvas = null;
      }
      const shot = compositeMapCanvases(canvas, deckCanvas);
      done({ dataUrl: shot.toDataURL(format, quality), width: shot.width, height: shot.height });
    }
    map.triggerRepaint();
    if (map.isStyleLoaded && map.isStyleLoaded() && !map.isMoving()) {
      requestAnimationFrame(capture);
    } else {
      map.once('idle', function () { requestAnimationFrame(capture); });
    }
  }

  // -----------------------------------------------------------------------
  // deck_request — server -> client request with a reply (v1.13.0)
  // -----------------------------------------------------------------------
  // Python's MapWidget.rpc() sends {id, requestId, method, params}; the
  // method's value (or the promise it returns) goes back through
  // Shiny.shinyapp.makeRequest() to the handler set_message_handler()
  // registered as "<id>_rpc_reply", as [requestId, result, error].
  var RPC_METHODS = {
    getViewState: function (instance) {
      var map = instance.map, c = map.getCenter(), b = map.getBounds();
      return {
        longitude: c.lng, latitude: c.lat, zoom: map.getZoom(),
        pitch: map.getPitch(), bearing: map.getBearing(),
        bounds: { sw: [b.getWest(), b.getSouth()], ne: [b.getEast(), b.getNorth()] }
      };
    },
    queryFeatures: function (instance, params) {
      return new Promise(function (resolve) {
        whenStyleReady(instance.map, function () {
          var opts = {};
          if (params.layers) opts.layers = params.layers;
          if (params.filter) opts.filter = params.filter;
          var geom = params.point || params.bounds;
          if (params.lnglat) {
            var p = instance.map.project(params.lnglat);
            geom = [p.x, p.y];
          }
          var feats = geom ? instance.map.queryRenderedFeatures(geom, opts)
                           : instance.map.queryRenderedFeatures(opts);
          resolve(feats.map(simplifyFeature));
        });
      });
    },
    exportImage: function (instance, params) {
      return new Promise(function (resolve) { captureMapImage(instance, params, resolve); });
    },
    hasImage: function (instance, params) {
      return !!instance.map.hasImage(params.imageId);
    }
  };

  function rpcReply(payload, result, error) {
    if (!(window.Shiny && Shiny.shinyapp && Shiny.shinyapp.makeRequest)) {
      console.warn('[shiny_deckgl] deck_request: Shiny.shinyapp.makeRequest unavailable');
      return;
    }
    Shiny.shinyapp.makeRequest(payload.id + '_rpc_reply', [payload.requestId, result, error],
      function () {},
      function (err) { console.warn('[shiny_deckgl] rpc reply failed:', err); });
  }

  function handleDeckRequest(payload) {
    if (!payload || !payload.id || !payload.requestId) return;
    var instance = mapInstances[payload.id];
    var fn = RPC_METHODS[payload.method];
    if (!instance) return rpcReply(payload, null, 'no such map: ' + payload.id);
    if (!fn) return rpcReply(payload, null, 'unknown rpc method: ' + payload.method);
    var out;
    try {
      out = fn(instance, payload.params || {});
    } catch (e) {
      return rpcReply(payload, null, String(e && e.message || e));
    }
    Promise.resolve(out).then(
      function (v) { rpcReply(payload, v === undefined ? null : v, null); },
      function (e) { rpcReply(payload, null, String(e && e.message || e)); });
  }
  addDeferrable("deck_request", handleDeckRequest);

  addDeferrable("deck_query_features", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;

    const map = instance.map;
    whenStyleReady(map, function() {
      const queryOpts = {};

      if (payload.layers) queryOpts.layers = payload.layers;
      if (payload.filter) queryOpts.filter = payload.filter;

      let features;
      if (payload.point) {
        features = map.queryRenderedFeatures(payload.point, queryOpts);
      } else if (payload.bounds) {
        features = map.queryRenderedFeatures(payload.bounds, queryOpts);
      } else {
        features = map.queryRenderedFeatures(queryOpts);
      }

      const simplified = features.map(simplifyFeature);

      Shiny.setInputValue(payload.id + '_query_result', {
        requestId: payload.requestId || 'default',
        features: simplified
      }, { priority: "event" });
    });
  });

  // -----------------------------------------------------------------------
  // deck_query_at_lnglat — project to pixels then query
  // -----------------------------------------------------------------------
  addDeferrable("deck_query_at_lnglat", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;

    const map = instance.map;
    whenStyleReady(map, function() {
      const point = map.project([payload.longitude, payload.latitude]);

      const queryOpts = {};
      if (payload.layers) queryOpts.layers = payload.layers;

      const features = map.queryRenderedFeatures(
        [point.x, point.y], queryOpts
      );

      const simplified = features.map(simplifyFeature);

      Shiny.setInputValue(payload.id + '_query_result', {
        requestId: payload.requestId || 'default',
        features: simplified
      }, { priority: "event" });
    });
  });

  // -----------------------------------------------------------------------
  // deck_add_marker — add or replace a named marker
  // -----------------------------------------------------------------------
  addDeferrable("deck_add_marker", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;

    if (!instance.markers) instance.markers = {};
    const mapId = payload.id;

    // Remove existing marker with same id
    if (instance.markers[payload.markerId]) {
      instance.markers[payload.markerId].remove();
    }

    const marker = new maplibregl.Marker({
      color: payload.color || '#3FB1CE',
      draggable: payload.draggable || false
    }).setLngLat([payload.longitude, payload.latitude]);

    // Optional popup
    if (payload.popupHtml) {
      const popup = new maplibregl.Popup({ offset: 25 })
        .setHTML(sanitizeHtml(payload.popupHtml));
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
        const lngLat = marker.getLngLat();
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
  addDeferrable("deck_remove_marker", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance || !instance.markers) return;

    if (instance.markers[payload.markerId]) {
      instance.markers[payload.markerId].remove();
      delete instance.markers[payload.markerId];
    }
  });

  // -----------------------------------------------------------------------
  // deck_clear_markers — remove all named markers
  // -----------------------------------------------------------------------
  addDeferrable("deck_clear_markers", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance || !instance.markers) return;

    Object.keys(instance.markers).forEach(function (mid) {
      instance.markers[mid].remove();
    });
    instance.markers = {};
  });

  // -----------------------------------------------------------------------
  // deck_enable_draw — add MapboxDraw to the map
  // -----------------------------------------------------------------------
  addDeferrable("deck_enable_draw", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
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

      const drawOpts = {
        displayControlsDefault: false,
      };

      if (payload.controls) {
        drawOpts.controls = payload.controls;
      } else {
        const modes = payload.modes || ['draw_point', 'draw_line_string', 'draw_polygon'];
        drawOpts.controls = {
          point: modes.indexOf('draw_point') !== -1,
          line_string: modes.indexOf('draw_line_string') !== -1,
          polygon: modes.indexOf('draw_polygon') !== -1,
          trash: true
        };
      }

      const draw = new MapboxDraw(drawOpts);
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

      const mapId = payload.id;
      function sendFeatures() {
        const fc = draw.getAll();
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
  addDeferrable("deck_disable_draw", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
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
  addDeferrable("deck_get_drawn_features", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance || !instance.draw) return;

    const fc = instance.draw.getAll();
    Shiny.setInputValue(payload.id + '_drawn_features', fc, { priority: "event" });
  });

  // -----------------------------------------------------------------------
  // deck_delete_drawn — delete specific or all drawn features
  // -----------------------------------------------------------------------
  addDeferrable("deck_delete_drawn", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
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
  addDeferrable("deck_set_feature_state", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;

    const target = { source: payload.sourceId, id: payload.featureId };
    if (payload.sourceLayer) target.sourceLayer = payload.sourceLayer;

    whenStyleReady(instance.map, function() {
      instance.map.setFeatureState(target, payload.state);
    });
  });

  // -----------------------------------------------------------------------
  // deck_remove_feature_state
  // -----------------------------------------------------------------------
  addDeferrable("deck_remove_feature_state", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;

    const target = { source: payload.sourceId };
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
  addDeferrable("deck_export_image", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;

    captureMapImage(instance, payload, function (shot) {
      Shiny.setInputValue(payload.id + '_export_result', {
        requestId: payload.requestId || 'default',
        dataUrl: shot.dataUrl,
        width: shot.width,
        height: shot.height
      }, { priority: "event" });
    });
  });

  // -----------------------------------------------------------------------
  // deck_add_cluster_layer — convenience: GeoJSON source + cluster layers
  // -----------------------------------------------------------------------
  addDeferrable("deck_add_cluster_layer", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;

    whenStyleReady(instance.map, function () {
      const map = instance.map;
      const srcId = payload.sourceId;
      const data = payload.data;
      const opts = payload.options || {};

      // Defaults
      const clusterRadius = opts.clusterRadius || 50;
      const clusterMaxZoom = opts.clusterMaxZoom || 14;

      const clusterColor = opts.clusterColor || "#51bbd6";
      const clusterStrokeColor = opts.clusterStrokeColor || "#ffffff";
      const clusterStrokeWidth = opts.clusterStrokeWidth || 1;
      const clusterTextColor = opts.clusterTextColor || "#ffffff";
      const clusterTextSize = opts.clusterTextSize || 12;

      const pointColor = opts.pointColor || "#11b4da";
      const pointRadius = opts.pointRadius || 5;
      const pointStrokeColor = opts.pointStrokeColor || "#ffffff";
      const pointStrokeWidth = opts.pointStrokeWidth || 1;

      // Size steps: [count, radius] pairs for interpolation
      const sizeSteps = opts.sizeSteps || [
        [0, 18], [100, 24], [750, 32]
      ];

      // Build circle-radius stops array for step expression
      const radiusStops = ["step", ["get", "point_count"]];
      for (let i = 0; i < sizeSteps.length; i++) {
        if (i === 0) {
          radiusStops.push(sizeSteps[i][1]);  // default value
        } else {
          radiusStops.push(sizeSteps[i][0]);   // threshold
          radiusStops.push(sizeSteps[i][1]);   // radius
        }
      }

      // Clean up existing layers & source
      // Detach previously-registered event handlers for this source first,
      // otherwise re-adding the same cluster layer leaks the old handlers and
      // causes duplicate click/hover behaviour.
      if (instance.clusterHandlers && instance.clusterHandlers[srcId]) {
        var oldHandlers = instance.clusterHandlers[srcId];
        map.off("click", srcId + "-clusters", oldHandlers.click);
        map.off("mouseenter", srcId + "-clusters", oldHandlers.mouseenter);
        map.off("mouseleave", srcId + "-clusters", oldHandlers.mouseleave);
        delete instance.clusterHandlers[srcId];
      }
      const layerIds = [srcId + "-clusters", srcId + "-count", srcId + "-unclustered"];
      layerIds.forEach(function (lid) {
        if (map.getLayer(lid)) map.removeLayer(lid);
      });
      if (map.getSource(srcId)) map.removeSource(srcId);

      // Add source
      const sourceSpec = {
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
        trackNativeLayer(instance, lid, true);
      });

      // Initialize cluster handlers storage if needed
      instance.clusterHandlers = instance.clusterHandlers || {};

      // Click-to-zoom on cluster circles (store handler for cleanup)
      var clickHandler = function (e) {
        const features = map.queryRenderedFeatures(e.point, {
          layers: [srcId + "-clusters"]
        });
        if (!features.length) return;
        const clusterId = features[0].properties.cluster_id;
        map.getSource(srcId).getClusterExpansionZoom(clusterId)
          .then(function (zoom) {
            map.easeTo({
              center: features[0].geometry.coordinates,
              zoom: zoom
            });
          }).catch(function (err) {
            console.warn('[shiny_deckgl] Cluster expansion zoom failed:', err);
          });
      };
      map.on("click", srcId + "-clusters", clickHandler);

      // Pointer cursor on clusters (store handlers for cleanup)
      var mouseenterHandler = function () {
        map.getCanvas().style.cursor = "pointer";
      };
      var mouseleaveHandler = function () {
        map.getCanvas().style.cursor = "";
      };
      map.on("mouseenter", srcId + "-clusters", mouseenterHandler);
      map.on("mouseleave", srcId + "-clusters", mouseleaveHandler);

      // Store handlers for cleanup on removal
      instance.clusterHandlers[srcId] = {
        click: clickHandler,
        mouseenter: mouseenterHandler,
        mouseleave: mouseleaveHandler
      };
    });
  });

  // -----------------------------------------------------------------------
  // deck_remove_cluster_layer — remove cluster source + all its layers
  // -----------------------------------------------------------------------
  addDeferrable("deck_remove_cluster_layer", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;

    whenStyleReady(instance.map, function () {
      const map = instance.map;
      const srcId = payload.sourceId;

      // Remove event handlers to prevent memory leaks
      if (instance.clusterHandlers && instance.clusterHandlers[srcId]) {
        var handlers = instance.clusterHandlers[srcId];
        map.off("click", srcId + "-clusters", handlers.click);
        map.off("mouseenter", srcId + "-clusters", handlers.mouseenter);
        map.off("mouseleave", srcId + "-clusters", handlers.mouseleave);
        delete instance.clusterHandlers[srcId];
      }

      const layerIds = [srcId + "-clusters", srcId + "-count", srcId + "-unclustered"];
      layerIds.forEach(function (lid) {
        if (map.getLayer(lid)) {
          map.removeLayer(lid);
          trackNativeLayer(instance, lid, false);
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
    const href = event.target.getAttribute('data-bs-target')
            || event.target.getAttribute('href');
    if (!href) return;
    let panel;
    try {
      panel = document.querySelector(href);
    } catch (e) {
      console.debug('[shiny_deckgl] Invalid selector in tab href:', href);
      return;
    }
    if (!panel) return;
    panel.querySelectorAll('.deckgl-map').forEach(function (el) {
      const inst = mapInstances[el.id];
      if (inst && inst.map) {
        // Already initialised — just resize and re-render
        setTimeout(function () {
          inst.map.resize();
          // Re-apply current layers to force deck.gl re-render
          if (inst.overlay && inst.lastLayers && inst.lastLayers.length) {
            renderNow(inst, el.id);
          }
        }, 50);
      } else {
        // Lazy-init: this map was deferred because its tab was hidden
        // at page load to avoid exhausting WebGL contexts.
        // After init, replay any Shiny messages that were queued.
        setTimeout(function () {
          if (typeof maplibregl === 'undefined' || typeof deck === 'undefined') {
            console.warn('[shiny_deckgl] CDN not ready on tab show for "' + el.id + '" — will retry on next tab show');
            return;
          }
          safeInitMap(el);
          replayDeferredMessages(el.id);
        }, 50);
      }
    });
  });

  // -----------------------------------------------------------------------
  // deck_update_tooltip — change tooltip config (no layer rebuild needed)
  // -----------------------------------------------------------------------
  addDeferrable("deck_update_tooltip", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;
    // onHover reads tooltipConfig from the instance at hover time,
    // so updating here is sufficient — no layer rebuild needed.
    instance.tooltipConfig = payload.tooltip || null;
  });

  // -----------------------------------------------------------------------
  // deck_set_animation — start/stop property animations for a layer
  // -----------------------------------------------------------------------
  addDeferrable("deck_set_animation", function (payload) {
    if (!payload || !payload.id) return;
    const instance = mapInstances[payload.id];
    if (!instance) return;

    const layerId = payload.layerId;
    const enabled = payload.enabled !== false;

    if (!enabled) {
      // Freeze: cancel RAF if this was the last animated layer
      if (instance.animations && instance.animations[layerId]) {
        delete instance.animations[layerId];
      }
    } else {
      // Resume: re-scan layers for animation configs and restart
      startPropertyAnimations(instance, payload.id);
    }
  });

  // -----------------------------------------------------------------------
  // MutationObserver: detect new .deckgl-map elements added dynamically
  // (e.g. by Shiny render.ui after a tab becomes visible) and initialise
  // them if they are in a visible tab.  This closes the race where
  // shown.bs.tab fires before Shiny has rendered the output.
  // -----------------------------------------------------------------------
  var _mutationObserver = new MutationObserver(function (mutations) {
    for (var i = 0; i < mutations.length; i++) {
      // Dispose maps whose DOM nodes were removed (tab/UI re-render) to avoid
      // leaking MapLibre/deck instances, listeners and RAF loops.
      var removed = mutations[i].removedNodes;
      for (var r = 0; r < removed.length; r++) {
        var rnode = removed[r];
        if (rnode.nodeType !== 1) continue;
        var rmaps = [];
        if (rnode.classList && rnode.classList.contains('deckgl-map')) {
          rmaps.push(rnode);
        } else if (rnode.querySelectorAll) {
          rmaps = rnode.querySelectorAll('.deckgl-map');
        }
        for (var m = 0; m < rmaps.length; m++) {
          var rel = rmaps[m];
          if (rel.id && mapInstances[rel.id] && isDetachedMapContainer(mapInstances[rel.id], rel)) {
            console.debug('[shiny_deckgl] MutationObserver: disposing removed .deckgl-map "' + rel.id + '"');
            disposeMap(rel.id);
            // The replacement may have been inserted before the old node was
            // removed; its add record was then skipped while the old map
            // still held the id, so initialise it here.
            var fresh = document.getElementById(rel.id);
            if (fresh && fresh !== rel && fresh.classList.contains('deckgl-map') &&
                typeof maplibregl !== 'undefined' && typeof deck !== 'undefined' &&
                isInVisibleTab(fresh)) {
              safeInitMap(fresh);
              replayDeferredMessages(fresh.id);
            }
          }
        }
      }
      if (typeof maplibregl === 'undefined' || typeof deck === 'undefined') continue;
      var added = mutations[i].addedNodes;
      for (var j = 0; j < added.length; j++) {
        var node = added[j];
        if (node.nodeType !== 1) continue;  // element nodes only
        var maps = [];
        if (node.classList && node.classList.contains('deckgl-map')) {
          maps.push(node);
        } else if (node.querySelectorAll) {
          maps = node.querySelectorAll('.deckgl-map');
        }
        for (var k = 0; k < maps.length; k++) {
          var el = maps[k];
          console.debug('[shiny_deckgl] MutationObserver: new .deckgl-map "' + el.id + '"');
          if (!mapInstances[el.id] && isInVisibleTab(el)) {
            safeInitMap(el);
            replayDeferredMessages(el.id);
          }
        }
      }
    }
  });
  function _startObserver() {
    console.debug('[shiny_deckgl] MutationObserver active');
    _mutationObserver.observe(document.body, { childList: true, subtree: true });
  }
  if (document.body) {
    _startObserver();
  } else {
    document.addEventListener('DOMContentLoaded', _startObserver);
  }

  // Expose helpers for standalone HTML exports
  window.__deckgl_initMap = initMap;
  window.__deckgl_buildDeckLayers = buildDeckLayers;
  window.__deckgl_buildEffects = buildEffects;
  window.__deckgl_resolveWidgetClass = resolveWidgetClass;
  window.__deckgl_cloneLayersData = cloneLayersData;
})();
