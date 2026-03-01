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
      default:
        console.warn('[shiny_deckgl] Unknown control type: ' + type);
        return null;
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
      maxZoom: initMaxZoom
    };
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

    // ---- Configurable initial controls ------------------------------------
    // Parse controls config from data-controls attribute (JSON array)
    var controlsConfig = [];
    if (el.dataset.controls) {
      try { controlsConfig = JSON.parse(el.dataset.controls); } catch (_) {}
    }
    // Default: navigation control in top-right if no config
    if (!controlsConfig.length) {
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

    const overlay = new deck.MapboxOverlay({
      interleaved: false,
      layers: []
    });
    map.addControl(overlay);

    mapInstances[mapId] = {
      map: map,
      overlay: overlay,
      tooltipConfig: tooltipConfig,
      dragMarker: null,
      lastLayers: [],          // cache for visibility toggling
      controls: initialControls
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
    layerProps.extensions = layerProps['@@extensions'].map(name => {
      const Cls = deck[name];
      if (!Cls) {
        console.warn('[shiny_deckgl] Unknown extension: ' + name);
        return null;
      }
      return new Cls();
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

    overlay.setProps(overlayProps);
    map.triggerRepaint();
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
    instance.map.setStyle(payload.style);
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

  // -----------------------------------------------------------------------
  // deck_add_maplibre_layer — add a native MapLibre rendering layer
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_add_maplibre_layer", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var map = instance.map;
    var layerSpec = payload.layerSpec;
    var beforeId = payload.beforeId || undefined;

    // Remove existing layer with same id
    if (map.getLayer(layerSpec.id)) {
      map.removeLayer(layerSpec.id);
    }

    map.addLayer(layerSpec, beforeId);
  });

  // -----------------------------------------------------------------------
  // deck_remove_maplibre_layer — remove a native MapLibre layer
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_remove_maplibre_layer", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    if (instance.map.getLayer(payload.layerId)) {
      instance.map.removeLayer(payload.layerId);
    }
  });

  // -----------------------------------------------------------------------
  // deck_remove_source — remove a native MapLibre source
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_remove_source", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    if (instance.map.getSource(payload.sourceId)) {
      instance.map.removeSource(payload.sourceId);
    }
  });

  // -----------------------------------------------------------------------
  // deck_set_source_data — update GeoJSON source data
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_set_source_data", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var source = instance.map.getSource(payload.sourceId);
    if (source && typeof source.setData === 'function') {
      source.setData(payload.data);
    }
  });

  // -----------------------------------------------------------------------
  // deck_set_paint_property — set paint property on a MapLibre layer
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_set_paint_property", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;
    instance.map.setPaintProperty(payload.layerId, payload.name, payload.value);
  });

  // -----------------------------------------------------------------------
  // deck_set_layout_property — set layout property on a MapLibre layer
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_set_layout_property", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;
    instance.map.setLayoutProperty(payload.layerId, payload.name, payload.value);
  });

  // -----------------------------------------------------------------------
  // deck_set_filter — set data-driven filter on a MapLibre layer
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_set_filter", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;
    instance.map.setFilter(payload.layerId, payload.filter || null);
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
  // deck_update_tooltip — change tooltip config without re-rendering
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_update_tooltip", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;
    instance.tooltipConfig = payload.tooltip || null;
  });

  // Expose helpers for standalone HTML exports
  window.__deckgl_initMap = initMap;
  window.__deckgl_buildDeckLayers = buildDeckLayers;
  window.__deckgl_buildEffects = buildEffects;
})();
