import { useEffect, useRef, useState } from 'react';
import type { NeighborhoodScoreResponse, FeaturedNeighborhood } from '../types';
import TetrisLoading from '@/components/ui/tetris-loader';

const DARK_STYLE: google.maps.MapTypeStyle[] = [
  { elementType: 'geometry', stylers: [{ color: '#0a0f14' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#0a0f14' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#5a6a7a' }] },
  { featureType: 'administrative', elementType: 'geometry', stylers: [{ color: '#15202e' }] },
  { featureType: 'administrative.country', elementType: 'geometry.stroke', stylers: [{ color: '#002c7c' }] },
  { featureType: 'poi', elementType: 'geometry', stylers: [{ color: '#0d1520' }] },
  { featureType: 'poi', elementType: 'labels.text.fill', stylers: [{ color: '#4a5a6a' }] },
  { featureType: 'poi.park', elementType: 'geometry', stylers: [{ color: '#0a1f12' }] },
  { featureType: 'poi.park', elementType: 'geometry.stroke', stylers: [{ color: '#0d2a16' }] },
  { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#151e2a' }] },
  { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#0a1018' }] },
  { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#1a2840' }] },
  { featureType: 'road.highway', elementType: 'geometry.stroke', stylers: [{ color: '#0d1828' }] },
  { featureType: 'road.arterial', elementType: 'geometry', stylers: [{ color: '#162030' }] },
  { featureType: 'transit', elementType: 'geometry', stylers: [{ color: '#152030' }] },
  { featureType: 'transit.station', elementType: 'labels.text.fill', stylers: [{ color: '#2ad587' }] },
  { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#001a3a' }] },
  { featureType: 'water', elementType: 'labels.text.fill', stylers: [{ color: '#003060' }] },
  { featureType: 'landscape.natural', elementType: 'geometry', stylers: [{ color: '#0c1218' }] },
];

const LIGHT_STYLE: google.maps.MapTypeStyle[] = [
  { elementType: 'geometry', stylers: [{ color: '#f0f4f3' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#4a5a6a' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#f0f4f3' }] },
  { featureType: 'administrative', elementType: 'geometry', stylers: [{ color: '#d8e4e0' }] },
  { featureType: 'poi', elementType: 'geometry', stylers: [{ color: '#e8ece8' }] },
  { featureType: 'poi.park', elementType: 'geometry', stylers: [{ color: '#d0f0d8' }] },
  { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#ffffff' }] },
  { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#d8e4e0' }] },
  { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#f8faf8' }] },
  { featureType: 'road.highway', elementType: 'geometry.stroke', stylers: [{ color: '#c0d0c8' }] },
  { featureType: 'transit', elementType: 'geometry', stylers: [{ color: '#dce8e0' }] },
  { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#c0e8d4' }] },
];

let _gmapsLoaded = false;
let _gmapsLoading = false;
const _gmapsCallbacks: (() => void)[] = [];

function loadGoogleMaps(apiKey: string, mapId?: string): Promise<void> {
  if (_gmapsLoaded) return Promise.resolve();
  return new Promise((resolve) => {
    _gmapsCallbacks.push(resolve);
    if (_gmapsLoading) return;
    _gmapsLoading = true;
    const script = document.createElement('script');
    let url = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&loading=async&callback=__gmapsInit`;
    if (mapId) url += `&map_ids=${mapId}`;
    script.src = url;
    script.async = true;
    script.defer = true;
    (window as unknown as Record<string, unknown>).__gmapsInit = () => {
      _gmapsLoaded = true;
      _gmapsLoading = false;
      _gmapsCallbacks.forEach(cb => cb());
      _gmapsCallbacks.length = 0;
    };
    document.head.appendChild(script);
  });
}

interface Props {
  data?: NeighborhoodScoreResponse | null;
  onMapClick: (lat: number, lon: number, address?: string) => void;
  loading: boolean;
  featuredNeighborhoods?: FeaturedNeighborhood[];
}

export default function NeighborhoodMap({ data, onMapClick, loading, featuredNeighborhoods = [] }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<google.maps.Map | null>(null);
  const circlesRef = useRef<google.maps.Circle[]>([]);
  const scoreOverlayRef = useRef<google.maps.OverlayView | null>(null);
  const pendingMarkerRef = useRef<google.maps.Marker | null>(null);
  const pendingCircleRef = useRef<google.maps.Circle | null>(null);
  const radiusLabelsRef = useRef<google.maps.OverlayView[]>([]);
  const pulseOverlayRef = useRef<google.maps.OverlayView | null>(null);
  const featuredOverlaysRef = useRef<google.maps.OverlayView[]>([]);
  const rotationFrameRef = useRef<number>(0);
  const onMapClickRef = useRef(onMapClick);
  onMapClickRef.current = onMapClick;

  const [ready, setReady] = useState(_gmapsLoaded);
  const [mapError, setMapError] = useState(false);
  const [clickLoading, setClickLoading] = useState(false);
  const [mapIdConfig, setMapIdConfig] = useState<string>('');

  useEffect(() => {
    if (_gmapsLoaded) { setReady(true); return; }
    const timeout = setTimeout(() => { if (!_gmapsLoaded) setMapError(true); }, 15000);
    fetch('/api/config/map')
      .then(r => r.json())
      .then(d => {
        if (d.google_maps_api_key) {
          if (d.google_maps_map_id) setMapIdConfig(d.google_maps_map_id);
          loadGoogleMaps(d.google_maps_api_key, d.google_maps_map_id || undefined).then(() => { clearTimeout(timeout); setReady(true); });
        } else { clearTimeout(timeout); setMapError(true); }
      })
      .catch(() => { clearTimeout(timeout); setMapError(true); });
    return () => clearTimeout(timeout);
  }, []);

  useEffect(() => {
    if (!ready || !containerRef.current || mapRef.current) return;
    const isDark = document.documentElement.classList.contains('dark');
    const center = data
      ? { lat: data.latitude, lng: data.longitude }
      : { lat: 12.9716, lng: 77.5946 };

    const mapOptions: google.maps.MapOptions = {
      center,
      zoom: data ? 13 : 12,
      disableDefaultUI: true,
      zoomControl: true,
      streetViewControl: false,
      fullscreenControl: false,
      clickableIcons: false,
      gestureHandling: 'greedy',
    };

    if (mapIdConfig) {
      mapOptions.mapId = mapIdConfig;
      if (isDark) mapOptions.colorScheme = 'DARK' as unknown as google.maps.ColorScheme;
    } else {
      mapOptions.styles = isDark ? DARK_STYLE : LIGHT_STYLE;
    }
    mapOptions.tilt = 45;
    mapOptions.heading = 0;

    const map = new google.maps.Map(containerRef.current, mapOptions);

    map.addListener('click', (e: google.maps.MapMouseEvent) => {
      if (!e.latLng) return;
      const pos = { lat: e.latLng.lat(), lng: e.latLng.lng() };

      pendingMarkerRef.current?.setMap(null);
      pendingCircleRef.current?.setMap(null);

      setClickLoading(true);
      onMapClickRef.current(pos.lat, pos.lng);
    });

    if (mapIdConfig) {
      let heading = 0;
      let paused = false;
      let resumeTimeout: ReturnType<typeof setTimeout>;

      const rotateMap = () => {
        if (!paused) {
          heading = (heading + 0.03) % 360;
          map.moveCamera({ heading });
        }
        rotationFrameRef.current = requestAnimationFrame(rotateMap);
      };
      rotationFrameRef.current = requestAnimationFrame(rotateMap);

      map.addListener('dragstart', () => {
        paused = true;
        clearTimeout(resumeTimeout);
      });
      map.addListener('dragend', () => {
        resumeTimeout = setTimeout(() => {
          heading = map.getHeading() ?? heading;
          paused = false;
        }, 3000);
      });
    }

    mapRef.current = map;

    return () => {
      if (rotationFrameRef.current) cancelAnimationFrame(rotationFrameRef.current);
    };
    // Map init only -- data is read for initial center but shouldn't trigger re-creation
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, mapIdConfig]);

  useEffect(() => {
    if (!mapRef.current || mapIdConfig) return;
    const observer = new MutationObserver(() => {
      const isDark = document.documentElement.classList.contains('dark');
      mapRef.current?.setOptions({ styles: isDark ? DARK_STYLE : LIGHT_STYLE });
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, [ready, mapIdConfig]);

  useEffect(() => {
    if (data) setClickLoading(false);
  }, [data]);

  useEffect(() => {
    if (!loading) setClickLoading(false);
  }, [loading]);

  useEffect(() => {
    if (!mapRef.current || !data) return;
    const map = mapRef.current;
    const target = { lat: data.latitude, lng: data.longitude };
    map.panTo(target);
    map.setZoom(13);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.latitude, data?.longitude]);

  useEffect(() => {
    if (!mapRef.current || !data) return;
    const map = mapRef.current;

    pendingMarkerRef.current?.setMap(null);
    pendingMarkerRef.current = null;
    pendingCircleRef.current?.setMap(null);
    pendingCircleRef.current = null;

    circlesRef.current.forEach(c => c.setMap(null));
    circlesRef.current = [];
    radiusLabelsRef.current.forEach(l => l.setMap(null));
    radiusLabelsRef.current = [];
    if (scoreOverlayRef.current) { scoreOverlayRef.current.setMap(null); scoreOverlayRef.current = null; }
    if (pulseOverlayRef.current) { pulseOverlayRef.current.setMap(null); pulseOverlayRef.current = null; }

    const neighborhoodName = data.address.split(',')[0]?.trim() || 'Location';

    class InteractiveMarker extends google.maps.OverlayView {
      private container: HTMLDivElement | null = null;
      private pos: google.maps.LatLng;
      private score: number;
      constructor(pos: google.maps.LatLng, score: number) {
        super();
        this.pos = pos;
        this.score = score;
      }
      onAdd() {
        this.container = document.createElement('div');
        Object.assign(this.container.style, {
          position: 'absolute',
          transform: 'translate(-50%, -100%)',
          cursor: 'pointer',
          zIndex: '1000',
          animation: 'map-marker-drop 0.5s cubic-bezier(0.34,1.56,0.64,1) both',
        });

        const sc = this.score;
        const safetyPink = data?.safety?.score != null && data.safety.score >= 90;
        const color = safetyPink ? '#ec4899' : sc >= 75 ? '#c0c7d0' : sc >= 68 ? '#3b82f6' : sc >= 60 ? '#2ad587' : sc >= 52 ? '#fbbf24' : '#f87171';
        const textColor = safetyPink ? '#fff' : sc >= 45 ? '#000' : '#fff';

        this.container.setAttribute('role', 'button');
        this.container.setAttribute('tabindex', '0');
        this.container.setAttribute('aria-label', `${neighborhoodName}: score ${Math.round(this.score)} out of 100. Click to explore.`);

        this.container.innerHTML = `
          <div class="map-marker-wrap" style="display:flex;flex-direction:column;align-items:center;transition:transform 0.3s cubic-bezier(0.34,1.56,0.64,1);transform-origin:bottom center;">
            <!-- Score badge -->
            <div style="
              background:${color};
              color:${textColor};
              border-radius:10px;
              padding:3px 10px;
              font-size:12px;
              font-weight:800;
              font-family:'JetBrains Mono',monospace;
              box-shadow:0 4px 12px ${color}50;
              white-space:nowrap;
              border:1px solid ${color}40;
              margin-bottom:3px;
            ">${Math.round(sc)}/100</div>
            <!-- Pin with house icon -->
            <svg width="40" height="48" viewBox="0 0 48 56" style="filter:drop-shadow(0 2px 6px ${color}40);">
              <path d="M24 0C12 0 2 10 2 22c0 16 22 34 22 34s22-18 22-34C46 10 36 0 24 0z" fill="${color}"/>
              <circle cx="24" cy="20" r="12" fill="rgba(255,255,255,0.2)"/>
              <path d="M16 22l8-6 8 6v8a1 1 0 0 1-1 1h-4v-5h-6v5h-4a1 1 0 0 1-1-1z" fill="white" stroke="white" stroke-width="0.5"/>
            </svg>
            <!-- Hover tooltip -->
            <div class="map-marker-tooltip" style="
              position:absolute;
              top:-44px;
              left:50%;
              transform:translateX(-50%) scale(0);
              opacity:0;
              background:#080c12;
              border:1px solid ${color}30;
              border-radius:10px;
              padding:8px 14px;
              white-space:nowrap;
              pointer-events:none;
              transition:all 0.25s cubic-bezier(0.34,1.56,0.64,1);
              box-shadow:0 8px 24px rgba(0,0,0,0.6);
              z-index:10;
            ">
              <div style="font-size:12px;font-weight:700;color:white;font-family:'Plus Jakarta Sans',sans-serif;">${neighborhoodName}</div>
              <div style="font-size:10px;color:rgba(255,255,255,0.5);margin-top:2px;">${data?.composite_label} · Click to explore</div>
            </div>
          </div>
        `;

        const wrap = this.container.querySelector('.map-marker-wrap') as HTMLElement;
        const tooltip = this.container.querySelector('.map-marker-tooltip') as HTMLElement;

        this.container.addEventListener('mouseenter', () => {
          this.container!.style.zIndex = '9999';
          wrap.style.animation = 'none';
          wrap.style.transform = 'scale(1.3)';
          tooltip.style.transform = 'translateX(-50%) scale(1)';
          tooltip.style.opacity = '1';
        });

        this.container.addEventListener('mouseleave', () => {
          this.container!.style.zIndex = '1000';
          wrap.style.transform = 'scale(1)';
          wrap.style.animation = 'map-marker-float 3s ease-in-out infinite';
          tooltip.style.transform = 'translateX(-50%) scale(0)';
          tooltip.style.opacity = '0';
        });

        this.container.addEventListener('click', () => {
          wrap.style.animation = 'none';
          wrap.style.transform = 'scale(0.85)';
          setTimeout(() => { wrap.style.transform = 'scale(1.3)'; }, 100);
          setTimeout(() => {
            wrap.style.transform = 'scale(1)';
            wrap.style.animation = 'map-marker-float 3s ease-in-out infinite';
          }, 300);
        });

        this.container.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            this.container?.click();
          }
        });

        setTimeout(() => {
          if (wrap) wrap.style.animation = 'map-marker-float 3s ease-in-out infinite';
        }, 1000);

        this.getPanes()?.overlayMouseTarget.appendChild(this.container);
      }
      draw() {
        if (!this.container) return;
        const proj = this.getProjection();
        const point = proj.fromLatLngToDivPixel(this.pos);
        if (point) {
          this.container.style.left = point.x + 'px';
          this.container.style.top = point.y + 'px';
        }
      }
      onRemove() { this.container?.parentNode?.removeChild(this.container); this.container = null; }
    }

    const marker = new InteractiveMarker(
      new google.maps.LatLng(data.latitude, data.longitude),
      data.composite_score
    );
    marker.setMap(map);
    scoreOverlayRef.current = marker;

    // Pulsing rings overlay at the location center
    class PulseOverlay extends google.maps.OverlayView {
      private div: HTMLDivElement | null = null;
      private pos: google.maps.LatLng;
      constructor(pos: google.maps.LatLng) {
        super();
        this.pos = pos;
      }
      onAdd() {
        this.div = document.createElement('div');
        Object.assign(this.div.style, {
          position: 'absolute',
          transform: 'translate(-50%, -50%)',
          width: '80px', height: '80px',
          pointerEvents: 'none',
        });
        this.div.innerHTML = `
          <div style="position:absolute;inset:0;border-radius:50%;border:2px solid #2ad587;opacity:0;animation:map-pulse 2.5s ease-out infinite"></div>
          <div style="position:absolute;inset:0;border-radius:50%;border:2px solid #007260;opacity:0;animation:map-pulse 2.5s ease-out 0.8s infinite"></div>
          <div style="position:absolute;inset:0;border-radius:50%;border:1px solid #002c7c;opacity:0;animation:map-pulse 2.5s ease-out 1.6s infinite"></div>
          <div style="position:absolute;inset:15px;border-radius:50%;background:radial-gradient(circle,rgba(42,213,135,0.15),transparent 70%)"></div>
        `;
        this.getPanes()?.overlayMouseTarget.appendChild(this.div);
      }
      draw() {
        if (!this.div) return;
        const proj = this.getProjection();
        const point = proj.fromLatLngToDivPixel(this.pos);
        if (point) {
          this.div.style.left = point.x + 'px';
          this.div.style.top = point.y + 'px';
        }
      }
      onRemove() { this.div?.parentNode?.removeChild(this.div); this.div = null; }
    }

    const pulse = new PulseOverlay(new google.maps.LatLng(data.latitude, data.longitude));
    pulse.setMap(map);
    pulseOverlayRef.current = pulse;

    // Radius circles with animated expansion
    const circleCenter = { lat: data.latitude, lng: data.longitude };
    const c2 = new google.maps.Circle({
      center: circleCenter, radius: 0, map,
      strokeColor: '#007260', strokeWeight: 1.5, strokeOpacity: 0.5,
      fillColor: '#002c7c', fillOpacity: 0.04,
    });
    const c5 = new google.maps.Circle({
      center: circleCenter, radius: 0, map,
      strokeColor: '#002c7c', strokeWeight: 2, strokeOpacity: 0.6,
      fillColor: '#002c7c', fillOpacity: 0.06,
    });
    circlesRef.current = [c2, c5];

    const animateCircle = (circle: google.maps.Circle, targetR: number, durationMs: number, onDone?: () => void) => {
      const start = performance.now();
      const step = (now: number) => {
        const t = Math.min((now - start) / durationMs, 1);
        const ease = 1 - Math.pow(1 - t, 3);
        circle.setRadius(targetR * ease);
        if (t < 1) requestAnimationFrame(step);
        else onDone?.();
      };
      requestAnimationFrame(step);
    };

    // Radius labels with brand styling -- start hidden, fade in after circle expands
    class RadiusLabel extends google.maps.OverlayView {
      private div: HTMLDivElement | null = null;
      private center: google.maps.LatLng;
      private radiusM: number;
      private text: string;
      constructor(center: google.maps.LatLng, radiusM: number, text: string) {
        super();
        this.center = center;
        this.radiusM = radiusM;
        this.text = text;
      }
      onAdd() {
        this.div = document.createElement('div');
        Object.assign(this.div.style, {
          position: 'absolute', transform: 'translate(-50%, -50%) translateY(6px)',
          color: '#2ad587', fontSize: '11px', fontWeight: '700',
          fontFamily: "'JetBrains Mono', monospace",
          whiteSpace: 'nowrap', pointerEvents: 'none',
          background: 'rgba(0,20,40,0.9)',
          padding: '2px 8px', borderRadius: '6px',
          border: '1px solid rgba(42,213,135,0.25)',
          boxShadow: '0 2px 8px rgba(0,44,124,0.2)',
          backdropFilter: 'blur(4px)',
          opacity: '0',
          transition: 'opacity 0.4s ease, transform 0.4s ease',
        });
        this.div.textContent = this.text;
        this.getPanes()?.overlayMouseTarget.appendChild(this.div);
      }
      reveal() {
        if (!this.div) return;
        this.div.style.opacity = '1';
        this.div.style.transform = 'translate(-50%, -50%)';
      }
      draw() {
        if (!this.div) return;
        const proj = this.getProjection();
        const edgeLat = this.center.lat();
        const edgeLng = this.center.lng() + (this.radiusM / 111320) / Math.cos(edgeLat * Math.PI / 180);
        const point = proj.fromLatLngToDivPixel(new google.maps.LatLng(edgeLat, edgeLng));
        if (point) { this.div.style.left = point.x + 'px'; this.div.style.top = point.y + 'px'; }
      }
      onRemove() { this.div?.parentNode?.removeChild(this.div); this.div = null; }
    }

    const center = new google.maps.LatLng(data.latitude, data.longitude);
    const label2 = new RadiusLabel(center, 2000, '2 km');
    label2.setMap(map);
    const label5 = new RadiusLabel(center, 5000, '5 km');
    label5.setMap(map);
    radiusLabelsRef.current = [label2, label5];

    animateCircle(c2, 2000, 600, () => label2.reveal());
    setTimeout(() => animateCircle(c5, 5000, 600, () => label5.reveal()), 200);
  }, [data]);

  useEffect(() => {
    if (!mapRef.current || featuredNeighborhoods.length === 0) return;
    const map = mapRef.current;

    featuredOverlaysRef.current.forEach(o => o.setMap(null));
    featuredOverlaysRef.current = [];

    const activeLat = data?.latitude;
    const activeLon = data?.longitude;

    let pinIndex = 0;

    class NeighborhoodPin extends google.maps.OverlayView {
      private container: HTMLDivElement | null = null;
      private pos: google.maps.LatLng;
      private info: FeaturedNeighborhood;
      private entranceDelay: number;
      constructor(pos: google.maps.LatLng, info: FeaturedNeighborhood, index: number) {
        super();
        this.pos = pos;
        this.info = info;
        this.entranceDelay = index * 80;
      }
      onAdd() {
        this.container = document.createElement('div');
        Object.assign(this.container.style, {
          position: 'absolute',
          transform: 'translate(-50%, -100%) scale(0.3)',
          cursor: 'pointer',
          zIndex: '500',
          opacity: '0',
          transition: `opacity 0.4s cubic-bezier(0.34,1.56,0.64,1), transform 0.4s cubic-bezier(0.34,1.56,0.64,1)`,
        });

        setTimeout(() => {
          if (!this.container) return;
          this.container.style.opacity = '1';
          this.container.style.transform = 'translate(-50%, -100%) scale(1)';
        }, this.entranceDelay);

        const safetyPink = this.info.safety_score != null && this.info.safety_score >= 90;
        const dotColor = safetyPink ? '#ec4899' : this.info.score >= 75 ? '#c0c7d0' : this.info.score >= 68 ? '#3b82f6' : this.info.score >= 60 ? '#2ad587' : this.info.score >= 52 ? '#fbbf24' : '#f87171';
        const scoreDark = this.info.score >= 55 ? '#000' : '#000';
        const priceText = this.info.avg_price_sqft ? `₹${(this.info.avg_price_sqft / 1000).toFixed(0)}K/sqft` : '';
        const growthText = this.info.yoy_growth_pct && this.info.yoy_growth_pct > 0 ? `+${this.info.yoy_growth_pct}%` : '';
        const subtitleParts = [priceText, growthText].filter(Boolean).join(' · ');
        const pinId = `fp-${Math.random().toString(36).slice(2, 8)}`;

        this.container.setAttribute('role', 'button');
        this.container.setAttribute('tabindex', '0');
        this.container.setAttribute('aria-label', `${this.info.name}: score ${Math.round(this.info.score)} out of 100. Click to explore.`);

        this.container.innerHTML = `
          <div class="featured-pin-wrap" style="display:flex;flex-direction:column;align-items:center;transition:transform 0.3s cubic-bezier(0.34,1.56,0.64,1);transform-origin:bottom center;">
            <svg width="32" height="42" viewBox="0 0 36 46" style="filter:drop-shadow(0 2px 6px ${dotColor}40);transition:transform 0.25s ease;">
              <defs>
                <linearGradient id="${pinId}" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="${dotColor}"/>
                  <stop offset="100%" stop-color="${dotColor}cc"/>
                </linearGradient>
              </defs>
              <path d="M18 0C9 0 1 8 1 17c0 12 17 29 17 29s17-17 17-29C35 8 27 0 18 0z" fill="url(#${pinId})" stroke="${dotColor}" stroke-width="0.5" stroke-opacity="0.4"/>
              <circle cx="18" cy="16" r="10" fill="rgba(0,0,0,0.25)"/>
              <text x="18" y="20" text-anchor="middle" fill="${scoreDark}" font-size="10" font-weight="800" font-family="'JetBrains Mono',monospace">${Math.round(this.info.score)}</text>
            </svg>
            <div class="featured-pin-tooltip" style="
              position:absolute;bottom:calc(100% + 4px);left:50%;
              transform:translateX(-50%) scale(0);
              opacity:0;
              background:rgba(8,12,18,0.95);
              border:1px solid ${dotColor}40;
              border-radius:10px;
              padding:8px 12px;
              white-space:nowrap;
              pointer-events:none;
              transition:all 0.2s cubic-bezier(0.34,1.56,0.64,1);
              box-shadow:0 8px 24px rgba(0,0,0,0.6);
              z-index:10;
            ">
              <div style="font-size:12px;font-weight:700;color:white;">${this.info.name}</div>
              <div style="display:flex;align-items:center;gap:6px;margin-top:3px;">
                <span style="font-size:11px;font-weight:700;color:${dotColor};font-family:'JetBrains Mono',monospace;">${Math.round(this.info.score)}/100</span>
                <span style="font-size:10px;color:rgba(255,255,255,0.5);">·</span>
                <span style="font-size:10px;color:rgba(255,255,255,0.5);">${this.info.label}</span>
              </div>
              ${subtitleParts ? `<div style="font-size:10px;color:rgba(255,255,255,0.4);margin-top:2px;">${subtitleParts}</div>` : ''}
              <div style="font-size:9px;color:${dotColor};margin-top:4px;opacity:0.7;">Click to explore →</div>
            </div>
          </div>
        `;

        const wrap = this.container.querySelector('.featured-pin-wrap') as HTMLElement;
        const tooltip = this.container.querySelector('.featured-pin-tooltip') as HTMLElement;

        this.container.addEventListener('mouseenter', () => {
          this.container!.style.zIndex = '9999';
          wrap.style.transform = 'scale(1.25)';
          tooltip.style.transform = 'translateX(-50%) scale(1)';
          tooltip.style.opacity = '1';
        });

        this.container.addEventListener('mouseleave', () => {
          this.container!.style.zIndex = '500';
          wrap.style.transform = 'scale(1)';
          tooltip.style.transform = 'translateX(-50%) scale(0)';
          tooltip.style.opacity = '0';
        });

        this.container.addEventListener('click', (e) => {
          e.stopPropagation();
          onMapClickRef.current(this.info.latitude, this.info.longitude, `${this.info.name}, Bangalore`);
        });

        this.container.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            this.container?.click();
          }
        });

        this.getPanes()?.overlayMouseTarget.appendChild(this.container);
      }
      draw() {
        if (!this.container) return;
        const proj = this.getProjection();
        const point = proj.fromLatLngToDivPixel(this.pos);
        if (point) {
          this.container.style.left = point.x + 'px';
          this.container.style.top = point.y + 'px';
        }
      }
      onRemove() { this.container?.parentNode?.removeChild(this.container); this.container = null; }
    }

    for (const n of featuredNeighborhoods) {
      if (activeLat != null && activeLon != null) {
        const dlat = n.latitude - activeLat;
        const dlon = n.longitude - activeLon;
        const distKm = Math.sqrt(dlat * dlat + dlon * dlon) * 111;
        if (distKm < 1.0) continue;
      }
      const pin = new NeighborhoodPin(
        new google.maps.LatLng(n.latitude, n.longitude),
        n,
        pinIndex++,
      );
      pin.setMap(map);
      featuredOverlaysRef.current.push(pin);
    }
  }, [featuredNeighborhoods, data?.latitude, data?.longitude]);

  return (
    <div className="absolute inset-0 z-0">
      <div className="absolute inset-0 z-[1] pointer-events-none">
        <div className="absolute top-0 left-0 right-0 h-16 bg-gradient-to-b from-black/30 to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-black/30 to-transparent" />
        <div className="absolute top-0 bottom-0 left-0 w-8 bg-gradient-to-r from-black/20 to-transparent" />
        <div className="absolute top-0 bottom-0 right-0 w-8 bg-gradient-to-l from-black/20 to-transparent" />
        <div className="absolute top-0 left-0 w-32 h-32 bg-radial-[at_0%_0%] from-brand-1/8 to-transparent" />
        <div className="absolute bottom-0 right-0 w-32 h-32 bg-radial-[at_100%_100%] from-brand-9/5 to-transparent" />
      </div>

      <div className="w-full h-full" ref={containerRef}>
        {!ready && !mapError && (
          <div className="h-full flex items-center justify-center bg-black">
            <div className="flex flex-col items-center gap-3 min-w-[160px]">
              <div className="w-full h-1 rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full w-[200%] bg-gradient-to-r from-transparent via-[#2ad587] to-transparent"
                  style={{ animation: 'map-loader-slide 1.2s linear infinite' }}
                />
              </div>
              <span className="text-white/50 text-sm">Loading map...</span>
            </div>
          </div>
        )}
        {mapError && (
          <div className="h-full flex items-center justify-center bg-black">
            <div className="text-center">
              <div className="text-3xl mb-2 opacity-30">🗺️</div>
              <p className="text-white/50 text-sm">Map unavailable</p>
            </div>
          </div>
        )}
      </div>
      {(loading || clickLoading) && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10 pointer-events-none">
          <div className="rounded-2xl px-6 py-5 flex flex-col items-center gap-3 animate-fade-in">
            <TetrisLoading size="sm" speed="fast" loadingText="Scoring this location..." />
          </div>
        </div>
      )}
    </div>
  );
}
