import { useState } from 'react';
import { motion } from 'framer-motion';
import ScrollReveal3D from './ScrollReveal3D';
import { ChevronDown, TrendingUp, Droplets, LayoutDashboard, Heart, Route, MapPin, Users, Sparkles, UtensilsCrossed, Wine, Baby, Trophy, ShieldCheck, Trees, ShoppingBag, Palette, Dumbbell } from 'lucide-react';
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

function scoreBadgeVariant(score: number): "success" | "info" | "warning" | "destructive" | "mono" {
  if (score >= 68) return 'info';
  if (score >= 60) return 'success';
  if (score >= 52) return 'warning';
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

const LIFESTYLE_TAG_CONFIG: Record<string, { icon: typeof Sparkles; color: string }> = {
  food: { icon: UtensilsCrossed, color: '#22c55e' },
  nightlife: { icon: Wine, color: '#a855f7' },
  kids: { icon: Baby, color: '#3b82f6' },
  seniors: { icon: Heart, color: '#f59e0b' },
  sports: { icon: Trophy, color: '#f97316' },
  woman_safety: { icon: ShieldCheck, color: '#ec4899' },
  nature: { icon: Trees, color: '#10b981' },
  shopping: { icon: ShoppingBag, color: '#06b6d4' },
  culture: { icon: Palette, color: '#8b5cf6' },
  fitness: { icon: Dumbbell, color: '#ef4444' },
};

function AiBriefCard({ ai }: { ai: NonNullable<NeighborhoodScoreResponse['ai_verification']> }) {
  const [expanded, setExpanded] = useState(false);
  const [expandedTag, setExpandedTag] = useState<string | null>(null);
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

          {(ai.lifestyle_tags?.length ?? 0) > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {ai.lifestyle_tags!.map((tag) => {
                const config = LIFESTYLE_TAG_CONFIG[tag.category] || { icon: Sparkles, color: '#2ad587' };
                const TagIcon = config.icon;
                const isExpanded = expandedTag === tag.label;
                return (
                  <button
                    key={tag.label}
                    onClick={() => setExpandedTag(isExpanded ? null : tag.label)}
                    className="flex items-center gap-1 rounded-full px-2.5 py-1 text-[10px] font-semibold transition-all hover:scale-105"
                    style={{
                      backgroundColor: config.color + '20',
                      color: config.color,
                      border: `1px solid ${config.color}40`,
                    }}
                  >
                    <TagIcon size={11} />
                    {tag.label}
                  </button>
                );
              })}
            </div>
          )}

          {expandedTag && ai.lifestyle_tags?.find(t => t.label === expandedTag) && (
            <div
              className="rounded-lg px-3 py-2 text-xs text-white/90 leading-relaxed"
              style={{
                backgroundColor: (LIFESTYLE_TAG_CONFIG[ai.lifestyle_tags!.find(t => t.label === expandedTag)!.category]?.color || '#2ad587') + '10',
                borderLeft: `2px solid ${LIFESTYLE_TAG_CONFIG[ai.lifestyle_tags!.find(t => t.label === expandedTag)!.category]?.color || '#2ad587'}`,
              }}
            >
              {ai.lifestyle_tags!.find(t => t.label === expandedTag)!.detail}
            </div>
          )}
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
                        <p key={i} className="text-sm text-white/95 leading-relaxed pl-3 border-l border-brand-9/30">{p}</p>
                      ))}
                    </div>
                  )}
                  {(ai.cons?.length ?? 0) > 0 && (
                    <div className="space-y-1">
                      <span className="text-[10px] font-bold text-red-400 uppercase tracking-widest">Cons</span>
                      {ai.cons.map((c: string, i: number) => (
                        <p key={i} className="text-sm text-white/95 leading-relaxed pl-3 border-l border-red-400/30">{c}</p>
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


export default function MapSidebar({ data }: Props) {
  const [activeNav, setActiveNav] = useState('overview');

  const scrollToSection = (id: string) => {
    setActiveNav(id);
    document.getElementById(`sidebar-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };


  return (
    <aside
      className="h-full bg-black/25 flex flex-col relative"
      style={{ perspective: '1200px' }}
    >
      <SidebarAurora />

      {/* Sticky header */}
      <div className="flex-shrink-0 border-b border-white/[0.08] relative z-10">
        <ScrollReveal3D rotateX={-6} delay={0.05}>
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
        </ScrollReveal3D>

        {/* Gradient menu nav */}
        <div className="flex gap-1 px-4 pb-2">
          {SECTION_NAV.map((s) => {
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
                  <Icon size={13} className={cn('flex-shrink-0 transition-all duration-300', isActive ? 'text-white scale-90' : 'text-white/80')} />
                  <span className={cn('transition-all duration-300 overflow-hidden whitespace-nowrap', isActive ? 'max-w-[80px] opacity-100 text-white' : 'max-w-0 opacity-0')}>
                    {s.label}
                  </span>
                </span>
              </motion.button>
            );
          })}
        </div>
      </div>

      {/* Pinned AI Brief */}
      {data.ai_verification && (data.ai_verification.verdict || data.ai_verification.narrative) && (
        <div className="flex-shrink-0 px-4 pt-3 pb-2 border-b border-white/[0.08] relative z-10">
          <AiBriefCard ai={data.ai_verification} />
        </div>
      )}

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto scrollbar-thin px-4 pb-8 space-y-5 pt-4 relative z-10">

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
                        <span className="text-white/70 ml-1">{w.distance_km}km</span>
                      )}
                    </Badge>
                  </motion.div>
                ))}
              </div>
            </LiquidGlassCard>
        )}

        {/* Property Prices */}
        {data.property_prices && (
          <ScoreCard title="Property" icon="trending" result={data.property_prices} compact />
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
          <ScoreCard title="Safety" icon="shield" result={data.safety} compact ringColor={data.safety.score >= 90 ? '#ec4899' : undefined} />
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
          {data.business_opportunity && <ScoreCard title="Business" icon="briefcase" result={data.business_opportunity} compact />}
        </Section>

        <div className="divider" />

        <div className="pt-2 pb-2 space-y-2">
          <p className="text-[11px] text-white/90 leading-relaxed">
            Data sourced from 8+ government agencies.
            Some datasets may not reflect real-time conditions. Last updated March 2025.
          </p>
          <p className="text-[10px] text-white/75">
            Scores are indicative and should not be the sole basis for investment decisions.
          </p>
        </div>
      </div>
    </aside>
  );
}
