import { useState, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import { ChevronDown, TrendingUp, Droplets, AlertTriangle, Star, Ban, LayoutDashboard, Heart, Route, MapPin, Users, Sparkles } from 'lucide-react';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { cn } from '@/lib/utils';
import ScoreRing from './ScoreRing';
import ScoreCard from './ScoreCard';
import { Badge } from '@/components/ui/badge';
import { SidebarAurora } from '@/components/ui/sidebar-aurora';
import { LiquidGlassCard } from '@/components/kokonutui/liquid-glass-card';

import type { NeighborhoodScoreResponse } from '../types';
import type { FreshnessData } from '../utils/freshnessMap';

interface Props {
  data: NeighborhoodScoreResponse;
  freshness: FreshnessData;
}

function readableAddress(address: string): string {
  return address.split(',').map(p => p.trim()).filter(p => !/^[A-Z0-9+]{4,}\+/.test(p) && !/^\d+[A-Z]?$/.test(p)).join(', ') || address;
}
function fmtPrice(lakh: unknown): string {
  if (lakh == null) return '—';
  const n = Number(lakh);
  if (isNaN(n)) return String(lakh);
  if (n >= 100) return `₹${(n / 100).toFixed(1)}Cr`;
  return `₹${n}L`;
}

function fmt(val: unknown): string {
  if (val == null) return '—';
  const n = Number(val);
  if (isNaN(n)) return String(val);
  return n % 1 === 0 ? String(n) : n.toFixed(1);
}

function scoreBadgeVariant(score: number): "success" | "info" | "warning" | "destructive" | "mono" {
  if (score >= 75) return 'success';
  if (score >= 60) return 'info';
  if (score >= 40) return 'warning';
  if (score >= 25) return 'destructive';
  return 'destructive';
}

function labelBadgeVariant(label: string, score: number): "success" | "info" | "warning" | "destructive" | "mono" {
  const lower = label.toLowerCase();
  if (lower.includes('severely') || lower.includes('poor') || lower.includes('unaffordable') || lower.includes('dangerous'))
    return 'destructive';
  if (lower.includes('below') || lower.includes('weak') || lower.includes('expensive'))
    return 'warning';
  return scoreBadgeVariant(score);
}

const SECTION_NAV = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard, from: '#002c7c', to: '#005075' },
  { id: 'livability', label: 'Livability', icon: Heart, from: '#005075', to: '#007260' },
  { id: 'connectivity', label: 'Connectivity', icon: Route, from: '#007260', to: '#00943d' },
  { id: 'investment', label: 'Investment', icon: TrendingUp, from: '#00943d', to: '#2ad587' },
];

function TiltCard({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [glowPos, setGlowPos] = useState({ x: 50, y: 50 });

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    setTilt({ x: (y - 0.5) * -6, y: (x - 0.5) * 6 });
    setGlowPos({ x: x * 100, y: y * 100 });
  }, []);

  const handleMouseLeave = useCallback(() => {
    setTilt({ x: 0, y: 0 });
  }, []);

  return (
    <motion.div
      ref={ref}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      animate={{ rotateX: tilt.x, rotateY: tilt.y }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      style={{ transformStyle: 'preserve-3d', perspective: '800px' }}
      className={`relative overflow-hidden ${className}`}
    >
      <div
        className="absolute inset-0 pointer-events-none transition-opacity duration-300"
        style={{
          background: `radial-gradient(circle at ${glowPos.x}% ${glowPos.y}%, rgba(42,213,135,0.08), transparent 60%)`,
          opacity: tilt.x !== 0 || tilt.y !== 0 ? 1 : 0,
        }}
      />
      <div className="relative" style={{ transform: 'translateZ(5px)' }}>
        {children}
      </div>
    </motion.div>
  );
}

function Section({ title, children, defaultOpen = false, id }: { title: string; children: React.ReactNode; defaultOpen?: boolean; id?: string }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <div id={id} className="border-b border-white/[0.08] pb-3">
        <CollapsibleTrigger asChild>
          <button className="w-full flex items-center justify-between py-2 group">
            <h3 className="text-xs font-semibold gradient-text uppercase tracking-widest group-hover:opacity-80 transition-opacity">{title}</h3>
            <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }}>
              <ChevronDown size={12} className="text-brand-9" />
            </motion.div>
          </button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="space-y-1.5 mt-1">
            {children}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
}

function AiBriefCard({ ai }: { ai: NonNullable<NeighborhoodScoreResponse['ai_verification']> }) {
  const [expanded, setExpanded] = useState(false);
  const color = '#2ad587';
  const hasDetails = !!(ai.best_for || ai.avoid_if || (ai.pros?.length ?? 0) > 0 || (ai.cons?.length ?? 0) > 0);

  return (
    <Collapsible open={expanded} onOpenChange={setExpanded}>
      <div className="rounded-xl bg-white/[0.04] hover:bg-white/[0.07] border border-white/[0.10] hover:border-brand-9/20 transition-colors duration-300 overflow-hidden relative">
        <div className="px-4 py-3.5 space-y-2.5">
          <div className="flex items-center gap-3">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{ backgroundColor: color + '20' }}
            >
              <Sparkles size={15} style={{ color }} />
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-semibold text-white">Should you buy here?</h4>
              <Badge variant="info" className="text-[10px] mt-0.5">
                {ai.confidence}% coverage
              </Badge>
            </div>
            {hasDetails && (
              <CollapsibleTrigger asChild>
                <button className="flex items-center gap-1 text-brand-9 cursor-pointer">
                  <span className="text-[11px]">{expanded ? '' : 'Details'}</span>
                  <motion.div animate={{ rotate: expanded ? 180 : 0 }} transition={{ duration: 0.2 }}>
                    <ChevronDown size={13} />
                  </motion.div>
                </button>
              </CollapsibleTrigger>
            )}
          </div>
          <p className="text-sm text-white/90 leading-relaxed">
            {ai.verdict || ai.narrative}
          </p>
        </div>

        {hasDetails && (
          <CollapsibleContent>
            <div className="px-4 pb-4 border-t border-white/[0.08] pt-3 space-y-3">
              {ai.best_for && (
                <div className="rounded-lg bg-brand-9/5 border border-brand-9/15 px-3 py-2.5">
                  <span className="text-brand-9 font-bold text-[10px] uppercase tracking-widest">Best for</span>
                  <p className="text-sm text-white/90 mt-1 leading-relaxed">{ai.best_for}</p>
                </div>
              )}
              {ai.avoid_if && (
                <div className="rounded-lg bg-red-400/5 border border-red-400/15 px-3 py-2.5">
                  <span className="text-red-400 font-bold text-[10px] uppercase tracking-widest">Avoid if</span>
                  <p className="text-sm text-white/90 mt-1 leading-relaxed">{ai.avoid_if}</p>
                </div>
              )}
              {((ai.pros?.length ?? 0) > 0 || (ai.cons?.length ?? 0) > 0) && (
                <div className="space-y-2.5">
                  {(ai.pros?.length ?? 0) > 0 && (
                    <div className="space-y-1">
                      <span className="text-[10px] font-bold text-brand-9 uppercase tracking-widest">Pros</span>
                      {ai.pros.map((p: string, i: number) => (
                        <p key={i} className="text-sm text-white/80 leading-relaxed pl-3 border-l border-brand-9/30">{p}</p>
                      ))}
                    </div>
                  )}
                  {(ai.cons?.length ?? 0) > 0 && (
                    <div className="space-y-1">
                      <span className="text-[10px] font-bold text-red-400 uppercase tracking-widest">Cons</span>
                      {ai.cons.map((c: string, i: number) => (
                        <p key={i} className="text-sm text-white/80 leading-relaxed pl-3 border-l border-red-400/30">{c}</p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </CollapsibleContent>
        )}
      </div>
    </Collapsible>
  );
}

function StatBox({ label, value, color = 'text-white' }: { label: string; value: string; color?: string }) {
  const [hovered, setHovered] = useState(false);
  return (
    <motion.div
      onHoverStart={() => setHovered(true)}
      onHoverEnd={() => setHovered(false)}
      animate={{ scale: hovered ? 1.03 : 1, y: hovered ? -2 : 0 }}
      transition={{ type: 'spring', stiffness: 400, damping: 20 }}
    >
      <LiquidGlassCard glassSize="sm" className="!p-3 text-center rounded-lg border-white/[0.08] dark:border-white/[0.08] dark:from-white/[0.02] dark:to-transparent">
        <div className="text-[11px] text-white/70 uppercase tracking-wider">{label}</div>
        <div className={cn("font-semibold text-sm mt-0.5 font-mono", color)}>{value}</div>
      </LiquidGlassCard>
    </motion.div>
  );
}

function ListRow({ label, value, icon, color }: { label: string; value: string | number; icon?: React.ReactNode; color?: string }) {
  const numVal = typeof value === 'number' ? value : parseFloat(String(value));
  const badgeVariant = !isNaN(numVal) ? scoreBadgeVariant(numVal) : (color?.includes('red') ? 'destructive' as const : 'success' as const);
  return (
    <motion.div
      whileHover={{ x: 4, backgroundColor: 'rgba(255,255,255,0.03)' }}
      transition={{ type: 'spring', stiffness: 400, damping: 25 }}
      className="flex items-center justify-between py-1.5 px-1 rounded-md -mx-1"
    >
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-sm text-white/90">{label}</span>
      </div>
      <Badge variant={badgeVariant} className="font-mono text-[10px]">{value}</Badge>
    </motion.div>
  );
}

export default function MapSidebar({ data, freshness: _freshness }: Props) {
  const [activeNav, setActiveNav] = useState('overview');

  const scrollToSection = (id: string) => {
    setActiveNav(id);
    document.getElementById(`sidebar-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const priceLabel = data.property_prices?.label || '';

  return (
    <aside
      className="h-full bg-black/25 flex flex-col relative"
      style={{ perspective: '1200px' }}
    >
      <SidebarAurora />

      {/* Sticky header */}
      <div className="flex-shrink-0 border-b border-white/[0.08] relative z-10">
        <div id="sidebar-overview" className="px-4 pt-3 pb-2 flex items-center gap-4">
          <motion.div className="float-animation" whileHover={{ scale: 1.1, rotate: 5 }}
            transition={{ type: 'spring', stiffness: 400, damping: 15 }}
          >
            <ScoreRing score={data.composite_score} size={64} strokeWidth={5} />
          </motion.div>
          <div className="flex-1 min-w-0">
            <h2 className="text-base font-semibold text-white truncate leading-tight">
              {readableAddress(data.address).split(',')[0]}
            </h2>
            <Badge variant={labelBadgeVariant(data.composite_label, data.composite_score)} className="mt-0.5 text-[10px] uppercase tracking-wider">
              {data.composite_label}
            </Badge>
          </div>
        </div>

        {/* Gradient menu nav */}
        <div className="flex gap-1 px-4 pb-2">
          {SECTION_NAV.map((s, i) => {
            const isActive = activeNav === s.id;
            const Icon = s.icon;
            return (
              <motion.button
                key={s.id}
                onClick={() => scrollToSection(s.id)}
                whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                className={cn(
                  'gradient-menu-item h-8 px-1.5 text-xs font-medium transition-all duration-500',
                  isActive ? 'w-[110px]' : 'w-8 hover:w-[110px]'
                )}
                style={{ background: isActive ? `linear-gradient(45deg, ${s.from}, ${s.to})` : undefined }}
              >
                {!isActive && <span className="absolute inset-0 rounded-full opacity-0 hover:opacity-100 transition-opacity duration-300" style={{ background: `linear-gradient(45deg, ${s.from}, ${s.to})` }} />}
                {isActive && <span className="absolute inset-0 rounded-full blur-[10px] opacity-40" style={{ background: `linear-gradient(45deg, ${s.from}, ${s.to})` }} />}
                <span className="relative flex items-center justify-center gap-1.5 w-full">
                  <Icon size={13} className={cn('flex-shrink-0 transition-all duration-300', isActive ? 'text-white scale-90' : 'text-white/50')} />
                  <span className={cn('transition-all duration-300 overflow-hidden whitespace-nowrap', isActive ? 'max-w-[80px] opacity-100 text-white' : 'max-w-0 opacity-0')}>
                    {s.label}
                  </span>
                </span>
              </motion.button>
            );
          })}
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto scrollbar-thin px-4 pb-8 space-y-5 pt-4 relative z-10">

        {/* AI Brief */}
        {data.ai_verification && (data.ai_verification.verdict || data.ai_verification.narrative) && (
          <AiBriefCard ai={data.ai_verification} />
        )}

        <div className="divider" />

        {/* Ward Information */}
        {(data.wards_covered?.length ?? 0) > 0 && (
          <LiquidGlassCard glassSize="sm" className="rounded-xl border-white/[0.08] dark:border-white/[0.08] dark:from-white/[0.02] dark:to-transparent">
              <div className="flex items-center gap-2 mb-2">
                <MapPin size={13} className="text-brand-9" />
                <span className="text-xs font-bold gradient-text uppercase tracking-widest">Wards Covered</span>
                {data.wards_total_population && (
                  <Badge variant="mono" className="ml-auto text-[10px]">
                    <Users size={10} />
                    {data.wards_total_population.toLocaleString('en-IN')} pop
                  </Badge>
                )}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {data.wards_covered!.map((w) => (
                  <motion.div key={w.name} whileHover={{ scale: 1.05 }}>
                    <Badge
                      variant="mono"
                      className="cursor-default text-[10px] hover:text-brand-9 hover:border-brand-9/20 transition-colors"
                      title={`${w.corporation}${w.population ? ` · Pop: ${w.population.toLocaleString('en-IN')}` : ''}${w.distance_km ? ` · ${w.distance_km} km` : ''}`}
                    >
                      {w.name}
                      {w.distance_km != null && (
                        <span className="text-white/40 ml-1">{w.distance_km}km</span>
                      )}
                    </Badge>
                  </motion.div>
                ))}
              </div>
            </LiquidGlassCard>
        )}

        {/* Property Prices — LiquidGlassCard with score-aware label color */}
        {data.property_prices && (
          <TiltCard>
            <LiquidGlassCard glassSize="sm" className="rounded-xl border-white/[0.08] dark:border-white/[0.08] dark:from-white/[0.02] dark:to-transparent space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <TrendingUp size={13} className="text-brand-9" />
                  <span className="text-xs font-bold gradient-text uppercase tracking-widest">Property Prices</span>
                </div>
                <Badge variant={labelBadgeVariant(priceLabel, data.property_prices?.score ?? 50)} className="font-mono text-[10px]">
                  {priceLabel}
                </Badge>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {data.property_prices.breakdown.avg_2bhk_price_lakh != null && (
                  <StatBox label="Avg 2BHK" value={`~${fmtPrice(data.property_prices.breakdown.avg_2bhk_price_lakh)}`} color="text-white" />
                )}
                {data.property_prices.breakdown.avg_2bhk_rent != null && (
                  <StatBox label="Avg Rent" value={`₹${Number(data.property_prices.breakdown.avg_2bhk_rent).toLocaleString()}`} color="text-brand-9" />
                )}
                {data.property_prices.breakdown.yoy_growth_pct != null && (
                  <StatBox label="Avg YoY Growth" value={`+${fmt(data.property_prices.breakdown.yoy_growth_pct)}%`} color="text-brand-8" />
                )}
                {data.property_prices.breakdown.rental_yield_pct != null && (
                  <StatBox label="Avg Yield" value={`${fmt(data.property_prices.breakdown.rental_yield_pct)}%`} color="text-brand-9" />
                )}
              </div>
              {data.property_prices.breakdown.rental_recommendation != null && (
                <div className="flex items-center justify-between rounded-lg bg-white/[0.03] backdrop-blur-sm border border-white/[0.08] px-3 py-2.5">
                  <span className="text-xs text-white/80">Rent vs Buy</span>
                <Badge variant={String(data.property_prices.breakdown.rental_recommendation).includes('Buy') ? 'success' : 'info'} className="text-[10px]">
                  {String(data.property_prices.breakdown.rental_recommendation)}
                </Badge>
                </div>
              )}

              {data.builder_reputation?.recommended_builders?.length > 0 && (
                <Collapsible>
                  <CollapsibleTrigger asChild>
                    <button className="w-full flex items-center justify-between py-1.5 group">
                      <span className="text-[11px] text-white/60 uppercase tracking-widest font-semibold group-hover:text-white/80 transition-colors">Recommended Builders</span>
                      <ChevronDown size={12} className="text-brand-9" />
                    </button>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <div className="space-y-1 pb-1">
                      {data.builder_reputation.recommended_builders.map((b) => (
                        <ListRow key={b.name} label={b.name} value={b.score} color="text-brand-9" />
                      ))}
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              )}

              {data.builder_reputation?.builders_to_avoid?.length > 0 && (
                <Collapsible>
                  <CollapsibleTrigger asChild>
                    <button className="w-full flex items-center justify-between py-1.5 group">
                      <span className="text-[11px] text-white/60 uppercase tracking-widest font-semibold group-hover:text-white/80 transition-colors">Builders to Avoid</span>
                      <ChevronDown size={12} className="text-brand-9" />
                    </button>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <div className="space-y-1 pb-1">
                      {data.builder_reputation.builders_to_avoid.map((b) => (
                        <div key={b.name}>
                          <ListRow label={b.name} value={b.score} icon={<Ban size={12} className="text-red-400" />} color="text-red-400" />
                          {b.avoid_reason && <p className="text-xs text-red-400/70 pl-5 -mt-1 pb-1">{b.avoid_reason}</p>}
                        </div>
                      ))}
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              )}

              {(data.recommended_neighborhoods?.length ?? 0) > 0 && (
                <Collapsible>
                  <CollapsibleTrigger asChild>
                    <button className="w-full flex items-center justify-between py-1.5 group">
                      <span className="text-[11px] text-white/60 uppercase tracking-widest font-semibold group-hover:text-white/80 transition-colors">Top Rated Neighbourhoods</span>
                      <ChevronDown size={12} className="text-brand-9" />
                    </button>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <div className="space-y-1 pb-1">
                      {data.recommended_neighborhoods?.map((n) => (
                        <ListRow key={n.name} label={n.name} value={n.score} icon={<Star size={12} className="text-brand-9" />} color="text-brand-9" />
                      ))}
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              )}

              {(data.neighborhoods_to_avoid?.length ?? 0) > 0 && (
                <Collapsible>
                  <CollapsibleTrigger asChild>
                    <button className="w-full flex items-center justify-between py-1.5 group">
                      <span className="text-[11px] text-white/60 uppercase tracking-widest font-semibold group-hover:text-white/80 transition-colors">Neighbourhoods to Avoid</span>
                      <ChevronDown size={12} className="text-brand-9" />
                    </button>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <div className="space-y-1 pb-1">
                      {data.neighborhoods_to_avoid?.map((n) => (
                        <ListRow key={n.name} label={n.name} value={n.score} icon={<AlertTriangle size={12} className="text-red-400" />} color="text-red-400" />
                      ))}
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              )}
            </LiquidGlassCard>
          </TiltCard>
        )}

        {/* Flood Risk Warning */}
        {data.flood_risk && data.flood_risk.score < 50 && (
          <motion.div whileHover={{ scale: 1.02 }}
            className="flex items-center gap-2 rounded-lg bg-red-500/10 border border-red-500/20 hover:border-red-500/40 px-3 py-2.5 transition-colors cursor-default"
          >
            <Droplets size={14} className="text-red-400" />
            <Badge variant="destructive" className="text-[10px]">Flood Risk</Badge>
            <Badge variant="destructive" className="ml-auto font-mono text-[10px]">{data.flood_risk.label}</Badge>
          </motion.div>
        )}

        <div className="divider" />

        <Section title="Livability & Safety" defaultOpen={true} id="sidebar-livability">
          <ScoreCard title="Walkability" icon="walk" result={data.walkability} compact />
          <ScoreCard title="Safety" icon="shield" result={data.safety} compact />
          {data.noise && <ScoreCard title="Noise Level" icon="volume" result={data.noise} compact />}
          {data.cleanliness && <ScoreCard title="Cleanliness" icon="sparkles" result={data.cleanliness} compact />}
        </Section>

        <Section title="Health & Education" defaultOpen={true}>
          <ScoreCard title="Hospital Access" icon="hospital" result={data.hospital_access} compact />
          <ScoreCard title="School Access" icon="school" result={data.school_access} compact />
        </Section>

        <Section title="Connectivity & Commute" defaultOpen={true} id="sidebar-connectivity">
          <ScoreCard title="Transit Access" icon="train" result={data.transit_access} compact />
          {data.commute && <ScoreCard title="Commute" icon="car" result={data.commute} compact />}
          {data.delivery_coverage && <ScoreCard title="Delivery" icon="package" result={data.delivery_coverage} compact />}
        </Section>

        <Section title="Environment & Utilities">
          <ScoreCard title="Air Quality" icon="wind" result={data.air_quality} compact />
          <ScoreCard title="Water Supply" icon="droplets" result={data.water_supply} compact />
          <ScoreCard title="Power" icon="zap" result={data.power_reliability} compact />
          {data.flood_risk && <ScoreCard title="Flood Risk" icon="waves" result={data.flood_risk} compact />}
        </Section>

        <Section title="Investment & Development" id="sidebar-investment">
          <ScoreCard title="Builder Rep." icon="building" result={data.builder_reputation} compact />
          <ScoreCard title="Future Infra" icon="construction" result={data.future_infrastructure} compact />
          <ScoreCard title="Property Prices" icon="trending" result={data.property_prices} compact />
          {data.business_opportunity && <ScoreCard title="Business" icon="briefcase" result={data.business_opportunity} compact />}
        </Section>

        <div className="divider" />

        <div className="pt-2 pb-2 space-y-2">
          <p className="text-[11px] text-white/70 leading-relaxed">
            Data sourced from 8+ government agencies.
            Some datasets may not reflect real-time conditions. Last updated March 2025.
          </p>
          <p className="text-[10px] text-white/50">
            Scores are indicative and should not be the sole basis for investment decisions.
          </p>
        </div>
      </div>
    </aside>
  );
}
