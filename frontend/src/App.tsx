import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Share2, Download, MapPin, Shield, Compass, Database, LogOut, Newspaper } from 'lucide-react';
import NeighborhoodMap from './components/Map';
import MapSidebar from './components/MapSidebar';
import CategoryChips from './components/CategoryChips';
import VerifyClaims from './components/VerifyClaims';
import CompareMode from './components/CompareMode';
import DataSources from './components/DataSources';
import ScoreRing from './components/ScoreRing';
import ScoreCard from './components/ScoreCard';
import SearchAutocomplete from './components/SearchAutocomplete';
import LoginPage from './components/LoginPage';
import CityDashboard from './components/CityDashboard';
import ErrorBoundary from './components/ErrorBoundary';
import { generateReport } from './utils/generateReport';
import { generateComprehensiveReport } from './utils/generateComprehensiveReport';
import { getFreshnessForDimension, type FreshnessData } from './utils/freshnessMap';
import { apiUrl, apiFetch } from './lib/api';
import type { NeighborhoodScoreResponse, FeaturedNeighborhood } from './types';
import defaultScores from './data/defaultScores.json';

import { BeamsBackground } from '@/components/ui/beams-background';
import { FloatingPaths } from '@/components/ui/background-paths';
import { MorphPanel } from '@/components/ui/ai-input';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';

type AppMode = 'score' | 'update' | 'verify' | 'compare' | 'sources';


const MODE_TAB_GRADIENTS: Record<string, { from: string; to: string }> = {
  score: { from: '#005075', to: '#2ad587' },
  update: { from: '#a09888', to: '#1a1a1a' },
  compare: { from: '#4f46e5', to: '#818cf8' },
  verify: { from: '#b91c1c', to: '#d0c8b8' },
  sources: { from: '#1a1a1a', to: '#4a4a4a' },
};

const SECTION_IDS: Record<AppMode, string> = {
  score: 'explore-section',
  update: 'city-pulse-section',
  verify: 'verify-section',
  compare: 'compare-section',
  sources: 'sources-section',
};

function ModeTabs({ mode, onChange, onNavigate }: { mode: AppMode; onChange: (m: AppMode) => void; onNavigate?: () => void }) {
  const tabs = [
    { id: 'score' as const, label: 'Dad', icon: Compass },
    { id: 'update' as const, label: 'Boss', icon: Newspaper },
    { id: 'compare' as const, label: 'Mom', icon: MapPin },
    { id: 'verify' as const, label: 'Kids', icon: Shield },
    { id: 'sources' as const, label: 'Seniors', icon: Database },
  ];

  const handleTabClick = (id: AppMode) => {
    onNavigate?.();
    onChange(id);
    document.getElementById(SECTION_IDS[id])?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="flex items-center gap-1 rounded-lg border border-white/[0.06] bg-white/[0.03] p-0.5">
      {tabs.map((tab) => {
        const isActive = mode === tab.id;
        const grad = MODE_TAB_GRADIENTS[tab.id];
        const Icon = tab.icon;
        return (
          <button
            key={tab.id}
            onClick={() => handleTabClick(tab.id)}
            className={cn(
              'gradient-menu-item relative z-10 h-8 px-1.5 text-xs font-medium transition-all duration-500 rounded-md',
              isActive ? 'w-[90px]' : 'w-8 hover:w-[90px]'
            )}
            style={{
              background: isActive
                ? `linear-gradient(45deg, ${grad.from}, ${grad.to})`
                : undefined,
            }}
          >
            {/* Gradient bg on hover for inactive */}
            {!isActive && (
              <span
                className="absolute inset-0 rounded-md opacity-0 hover:opacity-100 transition-opacity duration-300"
                style={{ background: `linear-gradient(45deg, ${grad.from}, ${grad.to})` }}
              />
            )}
            {/* Blur glow */}
            {isActive && (
              <span
                className="absolute inset-0 rounded-md blur-[10px] opacity-40"
                style={{ background: `linear-gradient(45deg, ${grad.from}, ${grad.to})` }}
              />
            )}
            <span className="relative flex items-center justify-center gap-1.5 w-full">
              <Icon
                size={14}
                className={cn(
                  'flex-shrink-0 transition-all duration-300',
                  isActive ? 'text-white scale-90' : 'text-white/50'
                )}
              />
              <span
                className={cn(
                  'transition-all duration-300 overflow-hidden whitespace-nowrap',
                  isActive ? 'max-w-[60px] opacity-100 text-white' : 'max-w-0 opacity-0'
                )}
              >
                {tab.label}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

function readableAddress(addr: string): string {
  return addr.split(',').map(p => p.trim()).filter(p => !/^[A-Z0-9+]{4,}\+/.test(p) && !/^\d+[A-Z]?$/.test(p)).join(', ') || addr;
}

function CompactSearch({ onSearch, loading, address }: {
  onSearch: (q: { address?: string; builder_name?: string }) => void;
  loading: boolean;
  address: string;
}) {
  return (
    <SearchAutocomplete
      onSearch={onSearch}
      loading={loading}
      address={address}
      className="max-w-md"
    />
  );
}


function LandingHero() {
  return (
    <div className="h-screen relative flex flex-col overflow-hidden">
      {/* Animated background paths */}
      <div className="absolute inset-0 z-0">
        <FloatingPaths position={1} />
        <FloatingPaths position={-1} />
      </div>

      {/* Marketing text — top-left, matching section heading style */}
      <div className="absolute top-0 left-0 z-[1] px-8 lg:px-12 pt-10">
        <h1 className="text-[48px] sm:text-[64px] lg:text-[80px] font-bold leading-[0.92] tracking-tight text-white uppercase">
          Know Your<br />Neighborhood
        </h1>
        <p className="text-white/50 text-sm mt-2 font-mono">
          <span className="gradient-text sparkle-text font-bold">Before You Invest</span>
        </p>
      </div>

      {/* Spline 3D scene — in front of text (z-[5]), transparent background */}
      <div className="absolute inset-0 z-[5]" style={{ pointerEvents: 'none' }}>
        {/* @ts-expect-error - spline-viewer is a web component */}
        <spline-viewer
          url="https://prod.spline.design/ByjNvDd9duLiRPQb/scene.splinecode"
          loading-anim-type="none"
          style={{ width: '100%', height: '100%', background: 'transparent' }}
        />
      </div>
      {/* Force Spline canvas to be transparent */}
      <style>{`
        spline-viewer canvas {
          background: transparent !important;
        }
        spline-viewer #spline-container,
        spline-viewer > div {
          background: transparent !important;
        }
      `}</style>

      {/* Scroll indicator */}
      <motion.div
        className="absolute bottom-8 left-1/2 -translate-x-1/2 z-[10] flex flex-col items-center gap-2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
      >
        <span className="text-white/40 text-xs tracking-wider uppercase">Scroll</span>
        <motion.div
          className="w-5 h-8 rounded-full border border-white/20 flex justify-center pt-1.5"
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ repeat: Infinity, duration: 2 }}
        >
          <motion.div
            className="w-1 h-2 rounded-full bg-white/60"
            animate={{ y: [0, 8, 0] }}
            transition={{ repeat: Infinity, duration: 2 }}
          />
        </motion.div>
      </motion.div>
    </div>
  );
}

function SidebarSkeleton() {
  return (
    <div className="h-full overflow-y-auto px-4 pt-4 space-y-4 animate-pulse">
      <div className="flex items-center gap-3">
        <div className="w-16 h-16 rounded-full bg-white/[0.06]" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-32 rounded bg-white/[0.06]" />
          <div className="h-3 w-20 rounded bg-white/[0.04]" />
        </div>
      </div>
      <div className="flex gap-2">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="h-8 flex-1 rounded-full bg-white/[0.06]" />
        ))}
      </div>
      <div className="h-px bg-white/[0.06]" />
      <div className="rounded-xl border border-white/[0.06] p-4 space-y-3">
        <div className="h-3 w-28 rounded bg-white/[0.06]" />
        <div className="h-4 w-full rounded bg-white/[0.04]" />
        <div className="h-4 w-3/4 rounded bg-white/[0.04]" />
      </div>
      {[1, 2, 3, 4, 5, 6].map(i => (
        <div key={i} className="rounded-xl border border-white/[0.06] p-3 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-white/[0.06]" />
          <div className="flex-1 space-y-1.5">
            <div className="h-3 w-24 rounded bg-white/[0.06]" />
            <div className="h-2.5 w-16 rounded bg-white/[0.04]" />
          </div>
          <div className="w-10 h-10 rounded-full bg-white/[0.06]" />
        </div>
      ))}
    </div>
  );
}

function LoadingProgressBar() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="absolute top-0 left-0 right-0 z-30 h-0.5"
    >
      <motion.div
        className="h-full bg-gradient-to-r from-brand-1 via-brand-9 to-brand-1"
        initial={{ x: '-100%' }}
        animate={{ x: '100%' }}
        transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}
      />
    </motion.div>
  );
}

function MobileBottomSheet({ data, activeCategories, onToggleCategory, freshness }: {
  data: NeighborhoodScoreResponse;
  activeCategories: Set<string>;
  onToggleCategory: (id: string) => void;
  freshness: FreshnessData;
}) {
  const [sheetState, setSheetState] = useState<'collapsed' | 'half' | 'full'>('collapsed');
  const sheetHeight = sheetState === 'collapsed' ? '120px' : sheetState === 'half' ? '55vh' : '85vh';

  const handleDragEnd = (_: unknown, info: { velocity: { y: number }; offset: { y: number } }) => {
    if (info.velocity.y > 300 || info.offset.y > 100) {
      setSheetState(prev => prev === 'full' ? 'half' : 'collapsed');
    } else if (info.velocity.y < -300 || info.offset.y < -100) {
      setSheetState(prev => prev === 'collapsed' ? 'half' : 'full');
    }
  };

  return (
    <motion.div
      className="fixed bottom-0 left-0 right-0 z-30 rounded-t-2xl bg-card border-t border-border shadow-xl lg:hidden overflow-hidden"
      animate={{ height: sheetHeight }}
      transition={{ type: 'spring', damping: 30, stiffness: 350 }}
    >
      <motion.div
        className="flex justify-center py-2 cursor-grab active:cursor-grabbing touch-none"
        drag="y"
        dragConstraints={{ top: 0, bottom: 0 }}
        dragElastic={0.2}
        onDragEnd={handleDragEnd}
        onClick={() => setSheetState(prev => prev === 'collapsed' ? 'half' : prev === 'half' ? 'full' : 'collapsed')}
      >
        <div className="w-10 h-1 rounded-full bg-muted-foreground/30" />
      </motion.div>

      <div className="px-4 pb-2 flex items-center gap-3">
        <ScoreRing score={data.composite_score} size={44} strokeWidth={3.5} animated={false} />
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-bold text-foreground truncate">{readableAddress(data.address).split(',')[0]}</h3>
          <p className="text-[10px] text-muted-foreground">{data.composite_label}</p>
        </div>
      </div>

      {sheetState !== 'collapsed' && (
        <div className="px-4 pb-4 overflow-y-auto scrollbar-thin" style={{ maxHeight: 'calc(100% - 80px)' }}>
          <div className="mb-3">
            <CategoryChips activeCategories={activeCategories} onToggle={onToggleCategory} data={data} />
          </div>

          {data.ai_verification?.verdict && (
            <div className="rounded-xl bg-secondary/50 border border-border p-3 mb-3">
              <p className="text-xs font-semibold text-foreground mb-1">Should you buy here?</p>
              <p className="text-[10px] text-muted-foreground leading-relaxed">{data.ai_verification.verdict}</p>
            </div>
          )}

          <div className="space-y-2">
            <ScoreCard title="Walkability" icon="walk" result={data.walkability} freshness={getFreshnessForDimension('walkability', freshness)} compact />
            <ScoreCard title="Safety" icon="shield" result={data.safety} freshness={getFreshnessForDimension('safety', freshness)} compact ringColor={data.safety.score >= 90 ? '#ec4899' : undefined} />
            <ScoreCard title="Transit" icon="train" result={data.transit_access} freshness={getFreshnessForDimension('transit_access', freshness)} compact />
            <ScoreCard title="Hospitals" icon="hospital" result={data.hospital_access} freshness={getFreshnessForDimension('hospital_access', freshness)} compact />
            <ScoreCard title="Schools" icon="school" result={data.school_access} freshness={getFreshnessForDimension('school_access', freshness)} compact />
            <ScoreCard title="Air Quality" icon="wind" result={data.air_quality} freshness={getFreshnessForDimension('air_quality', freshness)} compact />
            <ScoreCard title="Water" icon="droplets" result={data.water_supply} freshness={getFreshnessForDimension('water_supply', freshness)} compact />
            <ScoreCard title="Power" icon="zap" result={data.power_reliability} freshness={getFreshnessForDimension('power_reliability', freshness)} compact />
            {data.flood_risk && <ScoreCard title="Flood Risk" icon="waves" result={data.flood_risk} freshness={getFreshnessForDimension('flood_risk', freshness)} compact />}
            {data.commute && <ScoreCard title="Commute" icon="car" result={data.commute} freshness={getFreshnessForDimension('commute', freshness)} compact />}
            <ScoreCard title="Builders" icon="building" result={data.builder_reputation} freshness={getFreshnessForDimension('builder_reputation', freshness)} compact />
            <ScoreCard title="Future Infra" icon="construction" result={data.future_infrastructure} freshness={getFreshnessForDimension('future_infrastructure', freshness)} compact />
            <ScoreCard title="Property" icon="trending" result={data.property_prices} freshness={getFreshnessForDimension('property_prices', freshness)} compact />
          </div>
        </div>
      )}
    </motion.div>
  );
}

function App() {
  const [data, setData] = useState<NeighborhoodScoreResponse | null>(defaultScores as unknown as NeighborhoodScoreResponse);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [appMode, setAppMode] = useState<AppMode>('score');
  const [freshness, setFreshness] = useState<FreshnessData>({});
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [activeCategories, setActiveCategories] = useState<Set<string>>(new Set());
  const [featuredNeighborhoods, setFeaturedNeighborhoods] = useState<FeaturedNeighborhood[]>([]);

  const isScrollingRef = useRef(false);
  const { isAuthenticated, loading: authLoading, logout } = useAuth();

  useEffect(() => {
    document.documentElement.classList.add('dark');
  }, []);

  // Scroll to top when user logs in
  useEffect(() => {
    if (isAuthenticated) {
      window.scrollTo(0, 0);
    }
  }, [isAuthenticated]);

  // Intersection observer — only when authenticated (sections are in DOM)
  useEffect(() => {
    if (!isAuthenticated) return;

    const entries: Record<string, boolean> = {};
    const order: AppMode[] = ['score', 'update', 'compare', 'verify', 'sources'];

    const observer = new IntersectionObserver(
      (observed) => {
        observed.forEach((entry) => {
          entries[entry.target.id] = entry.isIntersecting;
        });
        if (isScrollingRef.current) return;
        const active = order.findLast((mode) => entries[SECTION_IDS[mode]]);
        if (active) setAppMode(active);
      },
      { threshold: 0.1 }
    );

    // Small delay to ensure sections are rendered
    const timer = setTimeout(() => {
      Object.values(SECTION_IDS).forEach((id) => {
        const el = document.getElementById(id);
        if (el) observer.observe(el);
      });
    }, 100);

    return () => {
      clearTimeout(timer);
      observer.disconnect();
    };
  }, [isAuthenticated]);

  // Fetch data — only when authenticated
  useEffect(() => {
    if (!isAuthenticated) return;

    fetch(apiUrl('/api/prefetch'))
      .then(r => r.json())
      .then(d => { if (d.neighborhoods) setFeaturedNeighborhoods(d.neighborhoods); })
      .catch(() => {});
    fetch(apiUrl('/api/data-freshness')).then(r => r.json()).then(setFreshness).catch(() => {});

    const params = new URLSearchParams(window.location.search);
    const lat = params.get('lat');
    const lon = params.get('lon');
    const demo = params.get('demo');

    const DEMO_PRESETS: Record<string, string> = {
      koramangala: 'Koramangala, Bangalore',
      indiranagar: 'Indiranagar, Bangalore',
      whitefield: 'Whitefield, Bangalore',
      hsr: 'HSR Layout, Bangalore',
      jayanagar: 'Jayanagar, Bangalore',
      electronic_city: 'Electronic City, Bangalore',
    };

    if (lat && lon) {
      handleSearch({ latitude: parseFloat(lat), longitude: parseFloat(lon) }, { scroll: false });
    } else if (demo) {
      const addr = DEMO_PRESETS[demo.toLowerCase()] || `${demo}, Bangalore`;
      handleSearch({ address: addr }, { scroll: false });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  const handleSearch = useCallback(async (query: { address?: string; latitude?: number; longitude?: number; builder_name?: string }, { scroll = true } = {}) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await apiFetch('/api/scores', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(query),
      });
      if (!resp.ok) {
        const err = await resp.json();
        let detail = 'Failed to compute scores';
        if (typeof err.detail === 'string') {
          detail = err.detail;
        } else if (Array.isArray(err.detail)) {
          detail = 'This location is outside the supported area';
        }
        throw new Error(detail);
      }
      const result = await resp.json();
      setData(result);
      setActiveCategories(new Set());
      setFeaturedNeighborhoods(prev => prev.map(n => {
        const dlat = n.latitude - result.latitude;
        const dlon = n.longitude - result.longitude;
        if (Math.sqrt(dlat * dlat + dlon * dlon) * 111 < 1.0) {
          return { ...n, score: result.composite_score, label: result.composite_label };
        }
        return n;
      }));
      if (scroll) {
        document.getElementById('explore-section')?.scrollIntoView({ behavior: 'smooth' });
      }
      const u = new URL(window.location.href);
      u.searchParams.set('lat', String(result.latitude));
      u.searchParams.set('lon', String(result.longitude));
      u.searchParams.delete('demo');
      window.history.replaceState(null, '', u.toString());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleMapClick = useCallback((lat: number, lon: number, address?: string) => {
    if (address) {
      handleSearch({ address, latitude: lat, longitude: lon });
    } else {
      handleSearch({ latitude: lat, longitude: lon });
    }
  }, [handleSearch]);

  const handleToggleCategory = useCallback((id: string) => {
    setActiveCategories(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleDownloadPdf = async () => {
    if (!data || downloadingPdf) return;
    setDownloadingPdf(true);
    try {
      await generateComprehensiveReport(data);
    } catch {
      try {
        await generateReport(data);
      } catch {
        setError('Report download failed. Please try again.');
      }
    } finally {
      setDownloadingPdf(false);
    }
  };

  const [linkCopied, setLinkCopied] = useState(false);
  const handleShareUrl = async () => {
    if (!data) return;
    try {
      await navigator.clipboard.writeText(window.location.href);
    } catch {
      // Fallback for non-secure contexts
      const ta = document.createElement('textarea');
      ta.value = window.location.href;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
    setLinkCopied(true);
    setTimeout(() => setLinkCopied(false), 2000);
  };

  // Single persistent shell — background never unmounts, no white flash
  return (
    <ErrorBoundary>
    <div className="min-h-screen w-screen relative grain-overlay">
      {/* Global background layers — always mounted */}
      <div className="fixed inset-0 z-0">
        <BeamsBackground className="absolute inset-0 w-full h-full" intensity="medium" />
      </div>

      {/* Auth loading spinner */}
      <AnimatePresence mode="wait">
        {authLoading && (
          <motion.div
            key="auth-loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, transition: { duration: 0.2 } }}
            className="fixed inset-0 z-50 flex items-center justify-center"
          >
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-2 border-white/20 border-t-[#2ad587] rounded-full animate-spin" />
              <span className="text-white/40 text-sm">Loading...</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Unauthenticated: hero + login */}
      <AnimatePresence mode="wait">
        {!authLoading && !isAuthenticated && (
          <motion.div
            key="unauth"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, transition: { duration: 0.3 } }}
          >
            <LandingHero />
            <LoginPage />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Authenticated: main app — fades in */}
      <AnimatePresence mode="wait">
        {!authLoading && isAuthenticated && (
          <motion.div
            key="auth"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1, transition: { duration: 0.4, delay: 0.1 } }}
          >


      {/* Bottom floating nav (Framer University style) */}
      <motion.nav
        className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2"
        initial={{ y: 100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ type: 'spring', damping: 25, stiffness: 200, delay: 0.3 }}
      >
        <div className="flex items-center gap-1 rounded-full bg-black/90 backdrop-blur-xl border border-white/10 px-2 py-2 shadow-2xl">
          <ModeTabs mode={appMode} onChange={setAppMode} onNavigate={() => {
            isScrollingRef.current = true;
            setTimeout(() => { isScrollingRef.current = false; }, 1000);
          }} />

          {data && (
            <>
              <button onClick={handleShareUrl} className="flex items-center justify-center w-9 h-9 rounded-full text-white/40 hover:text-white/70 transition-colors" title="Copy URL">
                {linkCopied ? <span className="text-[9px] font-mono text-brand-9">OK</span> : <Share2 size={14} />}
              </button>
              <button
                onClick={handleDownloadPdf}
                disabled={downloadingPdf}
                className="flex items-center justify-center w-9 h-9 rounded-full text-white/40 hover:text-white/70 transition-colors disabled:opacity-30"
                title={downloadingPdf ? 'Generating AI report...' : 'Download Report'}
              >
                <Download size={14} />
              </button>
            </>
          )}

          <button
            onClick={logout}
            className="flex items-center justify-center w-9 h-9 rounded-full bg-brand-9 text-white hover:bg-brand-8 transition-colors"
            title="Log Out"
          >
            <LogOut size={14} />
          </button>
        </div>
      </motion.nav>

      {/* Error toast */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ y: -20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -20, opacity: 0 }}
            className="fixed top-16 left-1/2 -translate-x-1/2 z-50 rounded-xl bg-black/70 backdrop-blur-md border border-white/10 text-white px-5 py-3 text-sm font-medium shadow-xl"
          >
            {error}
            <button onClick={() => setError(null)} className="ml-3 text-white/50 hover:text-white transition">✕</button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Explore */}
      <section id="explore-section" className="h-screen relative z-10 flex flex-col" style={{ background: 'linear-gradient(180deg, #050a08 0%, #040d0b 50%, #060b0f 100%)' }}>
        {/* Section ambient — emerald glow */}
        <div className="absolute inset-0 pointer-events-none z-0">
          <div className="absolute top-0 left-0 w-[600px] h-[600px] rounded-full" style={{ background: 'radial-gradient(circle, rgba(42,213,135,0.05), transparent 70%)' }} />
          <div className="absolute bottom-0 right-0 w-[500px] h-[500px] rounded-full" style={{ background: 'radial-gradient(circle, rgba(0,80,117,0.05), transparent 70%)' }} />
        </div>

        <AnimatePresence>
          {loading && <LoadingProgressBar />}
        </AnimatePresence>

        {/* Big page header (Framer University style) */}
        <div className="px-8 lg:px-12 pt-10 pb-4 flex flex-col lg:flex-row lg:items-end justify-between gap-4 relative z-10">
          <div>
            <h1 className="text-[48px] sm:text-[64px] lg:text-[80px] font-bold leading-[0.92] tracking-tight section-heading-explore">
              EXPLORE
            </h1>
            <p className="text-brand-9 text-sm mt-2 font-mono">
              17 dimensions · 126 neighborhoods · real government data
            </p>
          </div>
          <div className="flex-shrink-0 flex items-center gap-3 pb-1">
            <div className="w-full max-w-md">
              <CompactSearch onSearch={handleSearch} loading={loading} address={data?.address || ''} />
            </div>
            <MorphPanel neighborhoodName={data ? readableAddress(data.address).split(',')[0] : undefined} />
          </div>
        </div>

        {/* Map + sidebar: 65/35 split */}
        <div className="flex-1 flex overflow-hidden max-lg:hidden px-8 lg:px-12 pb-20 gap-4">
          <div className="w-[65%] relative rounded-2xl overflow-hidden border border-white/[0.08]">
            <NeighborhoodMap data={data} onMapClick={handleMapClick} loading={loading} featuredNeighborhoods={featuredNeighborhoods} />
          </div>
          <div className={cn("w-[35%] h-full overflow-y-auto flex-shrink-0 rounded-2xl border border-white/[0.08] transition-opacity duration-300", loading && data && "opacity-80 pointer-events-none")}>
            {data ? (
              <MapSidebar data={data} freshness={freshness} />
            ) : (
              <SidebarSkeleton />
            )}
          </div>
        </div>

        <div className="flex-1 lg:hidden relative">
          <NeighborhoodMap data={data} onMapClick={handleMapClick} loading={loading} featuredNeighborhoods={featuredNeighborhoods} />
        </div>

        {data && (
          <MobileBottomSheet
            data={data}
            activeCategories={activeCategories}
            onToggleCategory={handleToggleCategory}
            freshness={freshness}
          />
        )}
      </section>

      {/* City Pulse — newspaper: white bg, black ink */}
      <section id="city-pulse-section" className="min-h-screen relative z-10" style={{ background: '#f5f0e8' }}>
        <div className="px-8 lg:px-12 pt-10 relative z-10">
          <h1 className="text-[48px] sm:text-[64px] lg:text-[80px] font-bold leading-[0.92] tracking-tight text-neutral-900">
            UPDATE
          </h1>
          <p className="text-neutral-500 text-sm mt-2 font-mono">
            Live weather &amp; local news
          </p>
        </div>
        <div className="px-8 lg:px-12 pt-4 pb-20 relative z-10">
          <CityDashboard />
        </div>
      </section>

      {/* Compare */}
      <section id="compare-section" className="min-h-screen relative z-10" style={{ background: 'linear-gradient(180deg, #06060e 0%, #080712 50%, #0a0610 100%)' }}>
        {/* Section ambient — indigo/blue analytical feel */}
        <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
          <div className="absolute top-10 left-[15%] w-[600px] h-[600px] rounded-full" style={{ background: 'radial-gradient(circle, rgba(99,102,241,0.05), transparent 65%)' }} />
          <div className="absolute bottom-10 right-[10%] w-[500px] h-[500px] rounded-full" style={{ background: 'radial-gradient(circle, rgba(59,130,246,0.04), transparent 65%)' }} />
          <div className="absolute top-0 left-0 right-0 h-px" style={{ background: 'linear-gradient(to right, transparent, rgba(99,102,241,0.15), rgba(59,130,246,0.1), transparent)' }} />
        </div>

        <div className="px-8 lg:px-12 pt-10 pb-4 relative z-10">
          <h1 className="text-[48px] sm:text-[64px] lg:text-[80px] font-bold leading-[0.92] tracking-tight section-heading-compare">
            COMPARE
          </h1>
          <p className="text-indigo-400/70 text-sm mt-2 font-mono">
            Side-by-side neighborhood analysis
          </p>
        </div>
        <div className="max-w-7xl mx-auto px-6 pb-8 relative z-10">
          <CompareMode />
        </div>
      </section>

      {/* Verify */}
      <section id="verify-section" className="min-h-screen relative z-10 overflow-hidden" style={{ background: '#f5f0e8' }}>
        <div className="sticky top-0 z-20 px-8 lg:px-12 pt-10 pb-4" style={{ background: '#f5f0e8' }}>
          <h1 className="text-[48px] sm:text-[64px] lg:text-[80px] font-bold leading-[0.92] tracking-tight text-neutral-900">
            VERIFY
          </h1>
          <p className="text-sm mt-2 font-mono" style={{ color: '#8a8a8a' }}>
            AI-powered property claim verification
          </p>
        </div>
        <div className="max-w-7xl mx-auto px-6 pb-8 relative z-10">
          <VerifyClaims />
        </div>
      </section>

      {/* Sources */}
      <section id="sources-section" className="min-h-screen relative z-10" style={{ background: 'linear-gradient(180deg, #050a0a 0%, #04090c 50%, #060a0b 100%)' }}>
        {/* Section ambient — calm teal/cyan scholarly feel */}
        <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
          <div className="absolute top-10 left-[10%] w-[500px] h-[500px] rounded-full" style={{ background: 'radial-gradient(circle, rgba(20,184,166,0.045), transparent 65%)' }} />
          <div className="absolute bottom-10 right-[15%] w-[600px] h-[600px] rounded-full" style={{ background: 'radial-gradient(circle, rgba(6,182,212,0.035), transparent 65%)' }} />
          <div className="absolute top-0 left-0 right-0 h-px" style={{ background: 'linear-gradient(to right, transparent, rgba(20,184,166,0.15), rgba(6,182,212,0.1), transparent)' }} />
        </div>

        <div className="px-8 lg:px-12 pt-10 pb-4 relative z-10">
          <h1 className="text-[48px] sm:text-[64px] lg:text-[80px] font-bold leading-[0.92] tracking-tight section-heading-sources">
            SOURCES
          </h1>
          <p className="text-teal-400/70 text-sm mt-2 font-mono">
            Government data &amp; methodology
          </p>
        </div>
        <div className="max-w-7xl mx-auto px-6 pb-8 relative z-10">
          <DataSources />
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 py-8 text-center">
        <div className="mx-auto w-48 h-px mb-6" style={{ background: 'linear-gradient(to right, transparent, rgba(255,255,255,0.1), transparent)' }} />
        <p className="text-xs text-white/30">© {new Date().getFullYear()} @DhPhahS</p>
      </footer>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
    </ErrorBoundary>
  );
}

export default App;
