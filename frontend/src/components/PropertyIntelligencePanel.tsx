import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Building2, MapPin, AlertTriangle, Sparkles, ChevronLeft, ExternalLink, Star, Loader2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import BuilderCard from './BuilderCard';
import RedFlagAlert from './RedFlagAlert';
import MetricCard from './MetricCard';
import InfraTimeline from './InfraTimeline';
import TrustScoreCircle from './TrustScoreCircle';
import TrustBreakdownChart from './TrustBreakdownChart';
import type {
  ClaimVerification,
  BuilderSummary,
  BuilderProfile,
  BuildersResponse,
  AreaResponse,
  IntelligenceBrief,
  RiskFlag,
} from '@/types';

type TabId = 'claims' | 'builders' | 'area' | 'brief';

const TABS: { id: TabId; label: string; Icon: typeof Shield }[] = [
  { id: 'claims', label: 'Claims', Icon: Shield },
  { id: 'builders', label: 'Builders', Icon: Building2 },
  { id: 'area', label: 'Area Intel', Icon: MapPin },
  { id: 'brief', label: 'AI Brief', Icon: Sparkles },
];

const TAB_GRADIENTS: Record<TabId, { from: string; to: string }> = {
  claims: { from: '#005075', to: '#00943d' },
  builders: { from: '#002c7c', to: '#005075' },
  area: { from: '#007260', to: '#2ad587' },
  brief: { from: '#8b5cf6', to: '#2ad587' },
};

interface Props {
  address: string;
  latitude: number;
  longitude: number;
  claimResults: ClaimVerification[];
  summary: string;
  narrative?: string;
}

function BuilderDetailView({ slug, onBack }: { slug: string; onBack: () => void }) {
  const [profile, setProfile] = useState<BuilderProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/builder/${slug}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (!cancelled && d) setProfile(d); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [slug]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 size={20} className="animate-spin text-brand-9" />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-white/50">Builder not found</p>
        <button onClick={onBack} className="text-brand-9 text-sm mt-2 hover:underline">Go back</button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Back button */}
      <button onClick={onBack} className="flex items-center gap-1 text-sm text-brand-9 hover:underline">
        <ChevronLeft size={14} /> All builders
      </button>

      {/* Header */}
      <div className="flex items-center gap-4">
        <TrustScoreCircle score={profile.trust_score ?? 0} size={80} strokeWidth={5} />
        <div className="flex-1 min-w-0">
          <h3 className="text-xl font-semibold text-white" style={{ fontFamily: 'var(--font-display)' }}>
            {profile.name}
          </h3>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant={profile.trust_tier === 'trusted' ? 'success' : profile.trust_tier === 'emerging' ? 'info' : profile.trust_tier === 'cautious' ? 'warning' : 'destructive'}>
              {profile.trust_tier || 'unscored'}
            </Badge>
            {profile.segment && <Badge variant="mono">{profile.segment}</Badge>}
            {profile.avg_rating != null && (
              <span className="flex items-center gap-0.5 text-xs text-amber-400">
                <Star size={11} fill="currentColor" /> {profile.avg_rating.toFixed(1)}
              </span>
            )}
          </div>
          {profile.website && (
            <a href={profile.website} target="_blank" rel="noopener noreferrer" className="text-xs text-brand-9/70 hover:text-brand-9 flex items-center gap-1 mt-1">
              <ExternalLink size={10} /> Website
            </a>
          )}
        </div>
      </div>

      {/* Trust breakdown */}
      {profile.trust_score_breakdown && (
        <div className="rounded-xl bg-white/[0.03] p-4">
          <h4 className="text-xs font-bold gradient-text uppercase tracking-widest mb-3">Trust Breakdown</h4>
          <TrustBreakdownChart breakdown={profile.trust_score_breakdown} />
        </div>
      )}

      {/* Risk flags */}
      {profile.risk_flags.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-bold text-red-400 uppercase tracking-widest">Risk Flags</h4>
          {profile.risk_flags.map((flag, i) => (
            <RedFlagAlert key={i} flag={flag as RiskFlag} />
          ))}
        </div>
      )}

      {/* Description */}
      {profile.description && (
        <div className="rounded-xl bg-white/[0.03] p-4">
          <p className="text-sm text-white/80 leading-relaxed">{profile.description}</p>
        </div>
      )}

      {/* Projects */}
      {profile.projects.length > 0 && (
        <div>
          <h4 className="text-xs font-bold gradient-text uppercase tracking-widest mb-2">Projects ({profile.projects.length})</h4>
          <div className="rounded-xl bg-white/[0.03] overflow-hidden">
            <div className="grid grid-cols-[1fr_auto_auto_auto] gap-x-3 gap-y-0 text-[10px] text-white/40 uppercase tracking-wider px-3 py-2 border-b border-white/[0.06]">
              <span>Project</span><span>Area</span><span>Status</span><span>RERA</span>
            </div>
            {profile.projects.map((p, i) => (
              <div key={i} className="grid grid-cols-[1fr_auto_auto_auto] gap-x-3 gap-y-0 items-center px-3 py-2 border-b border-white/[0.04] last:border-0 hover:bg-white/[0.02] transition-colors">
                <span className="text-xs text-white/80 truncate">{p.project_name}</span>
                <span className="text-[10px] text-white/50">{p.location_area || '—'}</span>
                <Badge variant={p.status === 'completed' ? 'success' : p.status === 'ongoing' ? 'info' : 'warning'} className="text-[8px]">
                  {p.status}
                </Badge>
                <span className="text-[9px] text-white/30 font-mono">{p.rera_number || '—'}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Review sentiment */}
      {(profile.common_complaints.length > 0 || profile.common_praise.length > 0) && (
        <div className="rounded-xl bg-white/[0.03] p-4 space-y-3">
          <h4 className="text-xs font-bold gradient-text uppercase tracking-widest">Reviews</h4>
          {profile.common_praise.length > 0 && (
            <div>
              <span className="text-[10px] text-brand-9 font-bold uppercase tracking-widest">Praise</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {profile.common_praise.map(p => <Badge key={p} variant="success" className="text-[9px]">{p}</Badge>)}
              </div>
            </div>
          )}
          {profile.common_complaints.length > 0 && (
            <div>
              <span className="text-[10px] text-red-400 font-bold uppercase tracking-widest">Complaints</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {profile.common_complaints.map(c => <Badge key={c} variant="destructive" className="text-[9px]">{c}</Badge>)}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-2">
        <MetricCard label="On-Time" value={`${profile.on_time_delivery_pct}%`} />
        <MetricCard label="Complaints" value={String(profile.complaints)} color={profile.complaints > 15 ? 'text-red-400' : 'text-white'} />
        <MetricCard label="Projects" value={String(profile.rera_projects)} />
      </div>
    </div>
  );
}

export default function PropertyIntelligencePanel({ address, latitude, longitude, claimResults, summary, narrative }: Props) {
  const [activeTab, setActiveTab] = useState<TabId>('claims');
  const [buildersData, setBuildersData] = useState<BuildersResponse | null>(null);
  const [areaData, setAreaData] = useState<AreaResponse | null>(null);
  const [briefData, setBriefData] = useState<IntelligenceBrief | null>(null);
  const [loadingTab, setLoadingTab] = useState<string | null>(null);
  const [selectedBuilderSlug, setSelectedBuilderSlug] = useState<string | null>(null);

  const areaName = (() => {
    const parts = address.split(',').map(p => p.trim());
    const skipWords = /\b(bangalore|bengaluru|karnataka|india)\b/i;
    const pincode = /^\d{5,6}$/;
    const roadSuffix = /\s+(road|rd|main road|cross|street|st)$/i;

    // Extract meaningful area segments from all parts
    const candidates: string[] = [];
    for (const part of parts) {
      if (skipWords.test(part) || pincode.test(part) || part.length <= 2) continue;
      // Split by " - " to separate project name from area
      const subParts = part.split(/\s*[-–—]\s*/);
      for (const sp of subParts) {
        const cleaned = sp.trim();
        if (cleaned && !skipWords.test(cleaned) && !pincode.test(cleaned) && cleaned.length > 2) {
          candidates.push(cleaned);
        }
      }
    }

    // Strip "Road" suffix for matching
    const cleaned = candidates.map(c => c.replace(roadSuffix, '').trim()).filter(c => c.length >= 3);

    // If we have multiple candidates, the first is usually the project name,
    // later ones are area names. Prefer candidate at index 1+ that's short (area-like).
    if (cleaned.length > 1) {
      for (let i = 1; i < cleaned.length; i++) {
        if (cleaned[i].length >= 3 && cleaned[i].length <= 25) {
          return cleaned[i];
        }
      }
    }

    return cleaned[0] || candidates[0] || parts[0];
  })();
  const areaSlug = areaName.toLowerCase().replace(/\s+/g, '-');

  useEffect(() => {
    if (activeTab === 'builders' && !buildersData) {
      fetch(`/api/builders?area=${encodeURIComponent(areaSlug)}`)
        .then(r => r.ok ? r.json() : null)
        .then(d => { if (d) setBuildersData(d); })
        .catch(() => {})
        .finally(() => setLoadingTab(null));
    } else if (activeTab === 'area' && !areaData) {
      fetch(`/api/area/${encodeURIComponent(areaSlug)}`)
        .then(r => r.ok ? r.json() : null)
        .then(d => { if (d) setAreaData(d); })
        .catch(() => {})
        .finally(() => setLoadingTab(null));
    } else if (activeTab === 'brief' && !briefData) {
      fetch('/api/intelligence-brief', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address, latitude, longitude }),
      })
        .then(r => r.ok ? r.json() : null)
        .then(d => { if (d) setBriefData(d); })
        .catch(() => {})
        .finally(() => setLoadingTab(null));
    } else {
      setLoadingTab(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  const allRedFlags: RiskFlag[] = [];
  if (buildersData) {
    const allBuilders = Object.values(buildersData.builders).flat();
    allBuilders.forEach(b => {
      if (b.complaints > 15) {
        allRedFlags.push({ severity: 'warning', title: `${b.name}: ${b.complaints} RERA complaints`, detail: `High complaint count relative to ${b.rera_projects} projects (ratio: ${b.complaints_ratio.toFixed(2)})` });
      }
    });
    const avoidBuilders = buildersData.builders['avoid'] || [];
    avoidBuilders.forEach(b => {
      allRedFlags.push({ severity: 'critical', title: `${b.name}: Avoid tier`, detail: `Trust score ${b.trust_score ?? 'N/A'}. Consider alternatives.` });
    });
  }

  return (
    <div className="space-y-4">
      {/* Tab bar */}
      <div className="sticky top-12 z-10">
      <div className="flex items-center gap-1 rounded-lg border border-white/[0.06] bg-white/[0.03] p-1 overflow-x-auto">
        {TABS.map(tab => {
          const isActive = activeTab === tab.id;
          const grad = TAB_GRADIENTS[tab.id];
          const { Icon } = tab;
          return (
            <button
              key={tab.id}
              onClick={() => { setActiveTab(tab.id); setSelectedBuilderSlug(null); setLoadingTab(tab.id === 'claims' ? null : tab.id); }}
              className="gradient-menu-item relative z-10 h-8 px-3 text-xs font-medium transition-all duration-500 rounded-md flex-shrink-0"
              style={{
                background: isActive ? `linear-gradient(45deg, ${grad.from}, ${grad.to})` : undefined,
              }}
            >
              {!isActive && (
                <span
                  className="absolute inset-0 rounded-md opacity-0 hover:opacity-100 transition-opacity duration-300"
                  style={{ background: `linear-gradient(45deg, ${grad.from}, ${grad.to})` }}
                />
              )}
              {isActive && (
                <span
                  className="absolute inset-0 rounded-md blur-[10px] opacity-40"
                  style={{ background: `linear-gradient(45deg, ${grad.from}, ${grad.to})` }}
                />
              )}
              <span className="relative flex items-center gap-1.5">
                <Icon size={13} className={isActive ? 'text-white' : 'text-white/50'} />
                <span className={isActive ? 'text-white' : 'text-white/60'}>{tab.label}</span>
              </span>
            </button>
          );
        })}
      </div>
      </div>

      {/* Tab content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
        >
          {/* Loading state */}
          {loadingTab === activeTab && (
            <div className="flex items-center justify-center py-12">
              <Loader2 size={20} className="animate-spin text-brand-9" />
              <span className="ml-2 text-sm text-white/50">Loading {activeTab} data...</span>
            </div>
          )}

          {/* Claims tab */}
          {activeTab === 'claims' && (
            <div className="space-y-3">
              {/* Verdict banner */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-xl backdrop-blur-sm p-4"
                style={{
                  background: claimResults.some(r => r.verdict === 'MISLEADING' || r.verdict === 'SIGNIFICANTLY_MISLEADING')
                    ? 'linear-gradient(135deg, rgba(220,38,38,0.08), rgba(245,158,11,0.05))'
                    : claimResults.some(r => r.verdict === 'SLIGHTLY_MISLEADING')
                    ? 'linear-gradient(135deg, rgba(245,158,11,0.08), rgba(0,80,117,0.05))'
                    : 'linear-gradient(135deg, rgba(0,148,61,0.08), rgba(0,80,117,0.05))',
                  border: '1px solid',
                  borderColor: claimResults.some(r => r.verdict === 'MISLEADING' || r.verdict === 'SIGNIFICANTLY_MISLEADING')
                    ? 'rgba(220,38,38,0.2)'
                    : claimResults.some(r => r.verdict === 'SLIGHTLY_MISLEADING')
                    ? 'rgba(245,158,11,0.2)'
                    : 'rgba(0,148,61,0.2)',
                }}
              >
                <div className="flex items-center gap-3">
                  <Shield size={20} className={
                    claimResults.some(r => r.verdict === 'MISLEADING' || r.verdict === 'SIGNIFICANTLY_MISLEADING') ? 'text-red-400' :
                    claimResults.some(r => r.verdict === 'SLIGHTLY_MISLEADING') ? 'text-amber-400' : 'text-brand-9'
                  } />
                  <span className="font-semibold text-foreground text-sm">{summary}</span>
                </div>
              </motion.div>

              {/* AI Narrative */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="rounded-xl bg-white/[0.03] backdrop-blur-sm border border-white/[0.06] p-5"
              >
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles size={14} className="text-brand-9" />
                  <span className="text-[10px] font-bold uppercase tracking-widest text-white/40">AI Analysis</span>
                </div>
                <div className="text-sm text-white leading-relaxed whitespace-pre-line">
                  {narrative || claimResults.map(c => {
                    const d = c.details;
                    return `"${c.original_claim}" — ${d.explanation || c.verdict.replace(/_/g, ' ').toLowerCase() + '.'}`;
                  }).join('\n\n')}
                </div>
              </motion.div>

              {/* Quick verdict pills */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="flex flex-wrap gap-2"
              >
                {claimResults.map((c, i) => {
                  const verdictColor =
                    c.verdict === 'ACCURATE' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' :
                    c.verdict === 'SLIGHTLY_MISLEADING' ? 'bg-amber-500/10 border-amber-500/20 text-amber-400' :
                    (c.verdict === 'MISLEADING' || c.verdict === 'SIGNIFICANTLY_MISLEADING') ? 'bg-red-500/10 border-red-500/20 text-red-400' :
                    'bg-white/[0.04] border-white/[0.08] text-white/50';
                  const icon = c.verdict === 'ACCURATE' ? '✓' :
                    c.verdict === 'SLIGHTLY_MISLEADING' ? '~' :
                    (c.verdict === 'MISLEADING' || c.verdict === 'SIGNIFICANTLY_MISLEADING') ? '✗' : '?';
                  const shortClaim = c.original_claim.length > 40 ? c.original_claim.slice(0, 37) + '...' : c.original_claim;
                  return (
                    <span
                      key={i}
                      className={`inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border ${verdictColor}`}
                      title={`${c.original_claim}\nClaimed: ${c.claimed_value} → Actual: ${c.actual_value}`}
                    >
                      <span className="font-bold">{icon}</span>
                      {shortClaim}
                    </span>
                  );
                })}
              </motion.div>
            </div>
          )}

          {/* Builders tab */}
          {activeTab === 'builders' && loadingTab !== 'builders' && (
            <div className="space-y-4">
              {selectedBuilderSlug ? (
                <BuilderDetailView
                  slug={selectedBuilderSlug}
                  onBack={() => setSelectedBuilderSlug(null)}
                />
              ) : buildersData ? (
                <>
                  {/* AI area summary */}
                  {buildersData.area_summary && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="rounded-xl bg-white/[0.03] backdrop-blur-sm border border-white/[0.06] p-5"
                    >
                      <div className="flex items-center gap-2 mb-3">
                        <Sparkles size={14} className="text-brand-9" />
                        <span className="text-[10px] font-bold uppercase tracking-widest text-white/40">Builder Landscape</span>
                      </div>
                      <p className="text-sm text-white/85 leading-relaxed">{buildersData.area_summary}</p>
                    </motion.div>
                  )}

                  {/* Red flags at the top */}
                  {allRedFlags.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold text-red-400 uppercase tracking-widest flex items-center gap-1.5">
                        <AlertTriangle size={12} /> Red Flags ({allRedFlags.length})
                      </h4>
                      {allRedFlags.map((flag, i) => <RedFlagAlert key={i} flag={flag} />)}
                    </div>
                  )}

                  {(['trusted', 'emerging', 'cautious', 'avoid', 'unscored'] as const).map(tier => {
                    const builders = buildersData.builders[tier] || [];
                    if (builders.length === 0) return null;
                    return (
                      <div key={tier}>
                        <h4 className="text-xs font-bold uppercase tracking-widest mb-2 capitalize" style={{
                          color: tier === 'trusted' ? '#16a34a' : tier === 'emerging' ? '#2563eb' : tier === 'cautious' ? '#ca8a04' : tier === 'avoid' ? '#dc2626' : '#9ca3af'
                        }}>
                          {tier} ({builders.length})
                        </h4>
                        <div className="space-y-2">
                          {builders.map((b: BuilderSummary, i: number) => (
                            <BuilderCard
                              key={b.slug || b.name}
                              builder={b}
                              index={i}
                              aiBrief={b.slug ? buildersData.builder_briefs?.[b.slug] : undefined}
                              onClick={b.slug ? () => setSelectedBuilderSlug(b.slug!) : undefined}
                            />
                          ))}
                        </div>
                      </div>
                    );
                  })}
                  {buildersData.total === 0 && !buildersData.area_summary && (
                    <div className="text-center py-8 text-sm text-white/40">No builders found for this area</div>
                  )}
                </>
              ) : null}
            </div>
          )}

          {/* Area Intel tab */}
          {activeTab === 'area' && loadingTab !== 'area' && areaData && (
            <div className="space-y-4">
              {/* Metrics row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {areaData.property_prices && (
                  <>
                    {(areaData.property_prices as Record<string, unknown>).avg_price_sqft && (
                      <MetricCard label="Avg Price/sqft" value={`₹${Number((areaData.property_prices as Record<string, unknown>).avg_price_sqft).toLocaleString('en-IN')}`} />
                    )}
                    {(areaData.property_prices as Record<string, unknown>).yoy_growth_pct != null && (
                      <MetricCard
                        label="YoY Growth"
                        value={`${Number((areaData.property_prices as Record<string, unknown>).yoy_growth_pct).toFixed(1)}%`}
                        color={Number((areaData.property_prices as Record<string, unknown>).yoy_growth_pct) > 0 ? 'text-brand-9' : 'text-red-400'}
                      />
                    )}
                  </>
                )}
                <MetricCard label="Builders" value={String(areaData.builders.length)} />
                <MetricCard label="Infra Projects" value={String(areaData.infrastructure.length)} />
              </div>

              {/* Infrastructure timeline */}
              {areaData.infrastructure.length > 0 && (
                <div className="rounded-xl bg-white/[0.03] p-4">
                  <h4 className="text-xs font-bold gradient-text uppercase tracking-widest mb-3">Infrastructure Timeline</h4>
                  <InfraTimeline projects={areaData.infrastructure} />
                </div>
              )}

              {/* Builders in area */}
              {areaData.builders.length > 0 && (
                <div>
                  <h4 className="text-xs font-bold gradient-text uppercase tracking-widest mb-2">Builders in Area</h4>
                  <div className="space-y-2">
                    {areaData.builders.slice(0, 10).map((b, i) => (
                      <BuilderCard
                        key={b.slug || b.name}
                        builder={b}
                        index={i}
                        onClick={b.slug ? () => { setActiveTab('builders'); setSelectedBuilderSlug(b.slug!); } : undefined}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* AI Brief tab */}
          {activeTab === 'brief' && loadingTab !== 'brief' && (
            <div className="space-y-4">
              {briefData ? (
                <>
                  {/* Verdict */}
                  <div className="text-center py-4">
                    <Badge
                      variant={
                        briefData.verdict === 'STRONG_BUY' || briefData.verdict === 'BUY' ? 'success' :
                        briefData.verdict === 'CAUTION' || briefData.verdict === 'WAIT' ? 'warning' : 'destructive'
                      }
                      className="text-sm px-4 py-1"
                    >
                      {briefData.verdict.replace(/_/g, ' ')}
                    </Badge>
                  </div>

                  {/* Brief text */}
                  <div className="rounded-xl bg-white/[0.03] p-4">
                    <p className="text-sm text-white/85 leading-relaxed ai-response-md">{briefData.brief}</p>
                  </div>

                  {/* Strengths & Risks */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {briefData.key_strengths.length > 0 && (
                      <div className="rounded-xl bg-brand-9/5 border border-brand-9/15 p-4">
                        <h5 className="text-[10px] font-bold text-brand-9 uppercase tracking-widest mb-2">Key Strengths</h5>
                        <ul className="space-y-1.5">
                          {briefData.key_strengths.map((s, i) => (
                            <li key={i} className="text-xs text-white/80 leading-relaxed pl-3 border-l-2 border-brand-9/30">{s}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {briefData.key_risks.length > 0 && (
                      <div className="rounded-xl bg-red-500/5 border border-red-500/15 p-4">
                        <h5 className="text-[10px] font-bold text-red-400 uppercase tracking-widest mb-2">Key Risks</h5>
                        <ul className="space-y-1.5">
                          {briefData.key_risks.map((r, i) => (
                            <li key={i} className="text-xs text-white/80 leading-relaxed pl-3 border-l-2 border-red-400/30">{r}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* Price assessment */}
                  {briefData.price_assessment && (
                    <div className="rounded-xl bg-white/[0.03] p-4">
                      <h5 className="text-[10px] font-bold gradient-text uppercase tracking-widest mb-1">Price Assessment</h5>
                      <p className="text-sm text-white/80">{briefData.price_assessment}</p>
                    </div>
                  )}
                </>
              ) : !loadingTab && (
                <div className="text-center py-8">
                  <Sparkles size={32} className="text-brand-9/30 mx-auto mb-2" />
                  <p className="text-sm text-white/50">AI brief unavailable for this location</p>
                </div>
              )}
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      <p className="text-[10px] text-white/40 text-center">
        Data: RERA Karnataka, MCA, Consumer Courts, Google Maps APIs, PostGIS spatial queries
      </p>
    </div>
  );
}
