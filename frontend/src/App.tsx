import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence, useSpring, useScroll, useTransform } from 'framer-motion';
import { Share2, Download, MapPin, Shield, Compass, Database, LogOut } from 'lucide-react';
import NeighborhoodMap from './components/Map';
import MapSidebar from './components/MapSidebar';
import CategoryChips from './components/CategoryChips';
import VerifyClaims from './components/VerifyClaims';
import CompareMode from './components/CompareMode';
import DataSources from './components/DataSources';
import Section3DHeading from './components/Section3DHeading';
import ScoreRing from './components/ScoreRing';
import ScoreCard from './components/ScoreCard';
import SearchAutocomplete from './components/SearchAutocomplete';
import LoginPage from './components/LoginPage';
import Perspective3DContainer from './components/Perspective3DContainer';
import { generateReport } from './utils/generateReport';
import { generateComprehensiveReport } from './utils/generateComprehensiveReport';
import { getFreshnessForDimension, type FreshnessData } from './utils/freshnessMap';
import type { NeighborhoodScoreResponse, FeaturedNeighborhood } from './types';
import defaultScores from './data/defaultScores.json';

import { AnimatedShaderBackground } from '@/components/ui/animated-shader-background';
import { MorphPanel } from '@/components/ui/ai-input';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';

type AppMode = 'score' | 'verify' | 'compare' | 'sources';

function Logo({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center flex-shrink-0", className)}>
      <span className="text-base font-bold tracking-tight">
        <span className="text-foreground">Neighborhood</span>{' '}
        <span className="text-brand-9">Score</span>
      </span>
    </div>
  );
}

const MODE_TAB_GRADIENTS: Record<string, { from: string; to: string }> = {
  score: { from: '#002c7c', to: '#007260' },
  verify: { from: '#005075', to: '#00943d' },
  compare: { from: '#007260', to: '#2ad587' },
  sources: { from: '#005075', to: '#002c7c' },
};

const SECTION_IDS: Record<AppMode, string> = {
  score: 'explore-section',
  verify: 'verify-section',
  compare: 'compare-section',
  sources: 'sources-section',
};

function ModeTabs({ mode, onChange, onNavigate }: { mode: AppMode; onChange: (m: AppMode) => void; onNavigate?: () => void }) {
  const tabs = [
    { id: 'score' as const, label: 'Dad', icon: Compass },
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
  // Spring-based mouse tracking (Emil: useSpring for decorative mouse interactions)
  const rotateX = useSpring(0, { stiffness: 100, damping: 20 });
  const rotateY = useSpring(0, { stiffness: 100, damping: 20 });

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    rotateY.set(x * 15);
    rotateX.set(-y * 15);
  }, [rotateX, rotateY]);

  const handleMouseLeave = useCallback(() => {
    rotateX.set(0);
    rotateY.set(0);
  }, [rotateX, rotateY]);

  return (
    <div
      className="h-screen relative flex flex-col overflow-hidden"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{ perspective: '800px' }}
    >
      {/* Marketing text — behind the 3D scene (z-[1]), with text shadow for visibility */}
      <div
        className="absolute inset-0 z-[1] flex items-start justify-center p-4 pt-[9vh]"
        style={{ transformStyle: 'preserve-3d' }}
      >
        {/* Main 3D card — tilts with mouse via springs */}
        <motion.div
          className="max-w-4xl w-full text-center relative"
          style={{
            rotateX,
            rotateY,
            transformStyle: 'preserve-3d',
          }}
        >
          {/* Heading — newspaper headline style */}
          <div style={{ transform: 'translateZ(30px)' }}>
            {/* Top rule */}
            <motion.div
              initial={{ scaleX: 0, opacity: 0 }}
              animate={{ scaleX: 1, opacity: 1 }}
              transition={{ delay: 0.05, duration: 0.6 }}
              className="h-px w-48 mx-auto mb-5 bg-gradient-to-r from-transparent via-white/30 to-transparent"
            />
            <h1
              className="text-center uppercase"
              style={{
                fontFamily: 'var(--font-display)',
                textShadow: '0 0 40px rgba(0,0,0,0.8), 0 0 80px rgba(0,0,0,0.5)',
                lineHeight: 1.1,
              }}
            >
              {/* Line 1: Know Your Neighborhood */}
              <span className="block whitespace-nowrap">
                {['Know', 'Your', 'Neighborhood'].map((word, i) => (
                  <motion.span
                    key={word}
                    initial={{ y: 40, opacity: 0, filter: 'blur(8px)' }}
                    animate={{ y: 0, opacity: 1, filter: 'blur(0px)' }}
                    transition={{ delay: 0.1 + i * 0.08, type: 'spring', duration: 0.6, bounce: 0.1 }}
                    className={`inline-block mr-[0.3em] text-white ${
                      word === 'Neighborhood'
                        ? 'text-5xl sm:text-7xl font-bold tracking-[-0.02em]'
                        : 'text-3xl sm:text-5xl font-medium tracking-[0.04em]'
                    }`}
                  >
                    {word}
                  </motion.span>
                ))}
              </span>
              {/* Line 2: Before You Invest */}
              <span className="block whitespace-nowrap">
                {['Before', 'You', 'Invest'].map((word, i) => (
                  <motion.span
                    key={word}
                    initial={{ y: 40, opacity: 0, filter: 'blur(8px)' }}
                    animate={{ y: 0, opacity: 1, filter: 'blur(0px)' }}
                    transition={{ delay: 0.34 + i * 0.08, type: 'spring', duration: 0.6, bounce: 0.1 }}
                    className={`inline-block mr-[0.3em] ${
                      word === 'Invest'
                        ? 'text-5xl sm:text-7xl font-bold tracking-[-0.02em] gradient-text sparkle-text'
                        : 'text-3xl sm:text-5xl font-medium tracking-[0.04em] text-white/50'
                    }`}
                  >
                    {word}
                  </motion.span>
                ))}
              </span>
            </h1>
            {/* Bottom rule */}
            <motion.div
              initial={{ scaleX: 0, opacity: 0 }}
              animate={{ scaleX: 1, opacity: 1 }}
              transition={{ delay: 0.6, duration: 0.6 }}
              className="h-px w-48 mx-auto mt-5 bg-gradient-to-r from-transparent via-white/30 to-transparent"
            />
          </div>

        </motion.div>
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
    <div className="h-full bg-black/40 overflow-y-auto px-4 pt-4 space-y-4 animate-pulse">
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
  const { isAuthenticated, logout } = useAuth();

  // Scroll-driven header glass effect
  const { scrollY } = useScroll();
  const headerBlur = useTransform(scrollY, [0, 200], [12, 24]);
  const headerBorderOpacity = useTransform(scrollY, [0, 200], [0.06, 0.15]);
  const headerBackdropFilter = useTransform(headerBlur, (v) => `blur(${v}px)`);
  const headerBorderBottom = useTransform(headerBorderOpacity, (v) => `1px solid rgba(255,255,255,${v})`);

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
    const order: AppMode[] = ['score', 'compare', 'verify', 'sources'];

    const observer = new IntersectionObserver(
      (observed) => {
        observed.forEach((entry) => {
          entries[entry.target.id] = entry.isIntersecting;
        });
        if (isScrollingRef.current) return;
        const active = order.find((mode) => entries[SECTION_IDS[mode]]);
        if (active) setAppMode(active);
      },
      { threshold: 0.3 }
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

    fetch('/api/prefetch')
      .then(r => r.json())
      .then(d => { if (d.neighborhoods) setFeaturedNeighborhoods(d.neighborhoods); })
      .catch(() => {});
    fetch('/api/data-freshness').then(r => r.json()).then(setFreshness).catch(() => {});

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
      const resp = await fetch('/api/scores', {
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

  // Unauthenticated: show hero + login page
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen w-screen relative">
        <div className="fixed inset-0 z-0">
          <AnimatedShaderBackground className="absolute inset-0 w-full h-full" />
        </div>
        <LandingHero />
        <LoginPage />
      </div>
    );
  }

  // Authenticated: show header + main app
  return (
    <div className="min-h-screen w-screen relative">
      {/* Global shader background */}
      <div className="fixed inset-0 z-0">
        <AnimatedShaderBackground className="absolute inset-0 w-full h-full" />
      </div>

      {/* Header */}
      <motion.header
        className="sticky top-0 z-40 bg-black/70"
        style={{
          backdropFilter: headerBackdropFilter,
          borderBottom: headerBorderBottom,
        }}
      >
        <div className="flex items-center gap-3 px-4 py-2">
          <Logo />

          <div className="flex-1 max-w-md mx-auto">
            <CompactSearch onSearch={handleSearch} loading={loading} address={data?.address || ''} />
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <MorphPanel neighborhoodName={data ? readableAddress(data.address).split(',')[0] : undefined} />
            <ModeTabs mode={appMode} onChange={setAppMode} onNavigate={() => {
              isScrollingRef.current = true;
              setTimeout(() => { isScrollingRef.current = false; }, 1000);
            }} />

            {data && (
              <>
                <button onClick={handleShareUrl} className="p-2 rounded-lg border border-brand-9/30 hover:bg-brand-9/10 transition" title="Copy URL">
                  {linkCopied ? <span className="text-xs text-brand-9 px-1">Copied!</span> : <Share2 size={14} className="text-brand-9" />}
                </button>
                <button
                  onClick={handleDownloadPdf}
                  disabled={downloadingPdf}
                  className="p-2 rounded-lg border border-brand-9/30 hover:bg-brand-9/10 transition disabled:opacity-50"
                  title={downloadingPdf ? 'Generating AI report...' : 'Download Comprehensive Report'}
                >
                  <Download size={14} className="text-brand-9" />
                </button>
              </>
            )}

            <button
              onClick={logout}
              className="p-2 rounded-lg border border-white/10 hover:bg-white/[0.06] transition"
              title="Log Out"
            >
              <LogOut size={14} className="text-brand-9" />
            </button>
          </div>
        </div>
      </motion.header>

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
      <section id="explore-section" className="h-[calc(100vh-48px)] relative z-10 flex flex-col">
        <AnimatePresence>
          {loading && <LoadingProgressBar />}
        </AnimatePresence>

        <Section3DHeading title="Explore Neighborhoods" className="pt-5 pb-4" />

        <div className="flex-1 flex overflow-hidden max-lg:hidden">
          <div className="w-[55%] relative">
            <NeighborhoodMap data={data} onMapClick={handleMapClick} loading={loading} featuredNeighborhoods={featuredNeighborhoods} />
          </div>
          <div className={cn("w-[45%] h-full overflow-hidden flex-shrink-0 transition-opacity duration-300", loading && data && "opacity-80 pointer-events-none")}>
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

      {/* Compare */}
      <section id="compare-section" className="min-h-[calc(100vh-48px)] relative z-10 bg-black/40">
        <Perspective3DContainer maxRotation={2} className="max-w-7xl mx-auto px-6 py-8">
          <CompareMode />
        </Perspective3DContainer>
      </section>

      {/* Verify */}
      <section id="verify-section" className="min-h-[calc(100vh-48px)] relative z-10 bg-black/40">
        <Perspective3DContainer maxRotation={2} className="max-w-7xl mx-auto px-6 py-8">
          <VerifyClaims />
        </Perspective3DContainer>
      </section>

      {/* Sources */}
      <section id="sources-section" className="min-h-[calc(100vh-48px)] relative z-10 bg-black/40">
        <Perspective3DContainer maxRotation={3} className="max-w-7xl mx-auto px-6 py-8">
          <DataSources />
        </Perspective3DContainer>
      </section>
    </div>
  );
}

export default App;
