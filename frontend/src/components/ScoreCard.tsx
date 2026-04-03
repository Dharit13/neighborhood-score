import { useState } from 'react';
import { ChevronDown, Footprints, Shield, Volume2, Sparkles, Hospital, GraduationCap, Train, Car, Package, Wind, Droplets, Zap, Waves, Building2, Construction, TrendingUp, Briefcase } from 'lucide-react';
import ScoreRing from './ScoreRing';
import { Badge } from '@/components/ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import type { ScoreResult, TransitScoreResult, BuilderScoreResult, TransitDetail } from '../types';

const ICON_MAP: Record<string, React.ComponentType<{ size?: number; className?: string; style?: React.CSSProperties }>> = {
  walk: Footprints, shield: Shield, volume: Volume2, sparkles: Sparkles,
  hospital: Hospital, school: GraduationCap, train: Train, car: Car,
  package: Package, wind: Wind, droplets: Droplets, zap: Zap, waves: Waves,
  building: Building2, construction: Construction, trending: TrendingUp, briefcase: Briefcase,
};

interface Props {
  title: string;
  icon: string;
  result: ScoreResult | TransitScoreResult | BuilderScoreResult;
  freshness?: string | null;
  compact?: boolean;
  ringColor?: string;
}

function getScoreColor(score: number) {
  if (score >= 75) return '#c0c7d0';
  if (score >= 68) return '#3b82f6';
  if (score >= 60) return '#2ad587';
  if (score >= 52) return '#fbbf24';
  return '#f87171';
}

function scoreBadgeVariant(score: number): "success" | "info" | "warning" | "destructive" {
  if (score >= 68) return 'info';
  if (score >= 60) return 'success';
  if (score >= 52) return 'warning';
  return 'destructive';
}

function fmtDuration(mins: number): string {
  const m = Math.round(mins);
  if (m >= 60) {
    const h = Math.floor(m / 60);
    const rem = m % 60;
    return rem > 0 ? `${h}h ${rem}m` : `${h}h`;
  }
  return `${m} min`;
}

function TransitRow({ detail, icon }: { detail: TransitDetail; icon: string }) {
  const isDrive = detail.recommended_mode === 'drive/ride';
  return (
    <div className="rounded-lg bg-white/[0.05] border border-white/[0.08] px-3 py-2 text-xs space-y-1.5">
      <div className="flex justify-between items-center">
        <span className="text-white/90 font-medium">{icon} {detail.name}</span>
        <Badge variant={detail.recommended_mode === 'walk' ? 'success' : 'info'} className="text-[11px]">
          {detail.recommended_mode === 'walk' ? 'Walkable' : 'Drive/Ride'}
        </Badge>
      </div>
      {isDrive && detail.drive_offpeak_minutes != null ? (
        <div className="space-y-0.5">
          <div className="flex justify-between">
            <span className="text-white/80">By car ({Math.round(detail.drive_km!)} km)</span>
            <span className="text-emerald-400 font-semibold">~{fmtDuration(detail.drive_offpeak_minutes)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-white/80">Peak</span>
            <span className="text-red-400 font-semibold">~{fmtDuration(detail.drive_peak_minutes!)}</span>
          </div>
        </div>
      ) : (
        <div className="space-y-0.5">
          <div className="flex justify-between">
            <span className="text-white/80">Walk: {Math.round((detail.actual_walk_km ?? 0) * 10) / 10} km</span>
            <span className="text-emerald-400 font-semibold">~{fmtDuration(detail.walk_minutes)}</span>
          </div>
          {detail.marketing_claim_minutes != null && detail.walk_minutes > detail.marketing_claim_minutes && (
            <div className="flex justify-between text-[11px]">
              <span className="text-white/85">Ads claim <span className="text-brand-9 font-medium">"~{Math.round(detail.marketing_claim_minutes)} min"</span></span>
              <span className="text-red-400 font-medium">+{Math.round(detail.walk_minutes - detail.marketing_claim_minutes)} min longer</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ScoreCard({ title, icon, result, freshness, compact, ringColor }: Props) {
  const [expanded, setExpanded] = useState(false);
  const Icon = ICON_MAP[icon] || Sparkles;
  const transitResult = 'nearest_metro' in result ? result as TransitScoreResult : null;
  const builderResult = 'builders' in result ? result as BuilderScoreResult : null;
  const safetyColor = title === 'Safety'
    ? (result.score >= 90 ? '#ec4899' : result.score >= 70 ? '#22c55e' : result.score >= 50 ? '#fbbf24' : '#f87171')
    : null;
  const color = safetyColor || getScoreColor(result.score);

  const ringDisplay = (() => {
    if (icon === 'wind' && result.breakdown.weighted_aqi != null) {
      return `${Math.round(Number(result.breakdown.weighted_aqi))}`;
    }
    if (icon === 'volume' && result.breakdown.avg_noise_db_estimate != null) {
      return `${Math.round(Number(result.breakdown.avg_noise_db_estimate))}`;
    }
    return undefined;
  })();

  if (compact) {
    return (
      <Collapsible open={expanded} onOpenChange={setExpanded}>
        <div className="rounded-xl bg-white/[0.04] hover:bg-white/[0.07] border border-white/[0.10] hover:border-brand-9/20 transition-colors duration-300 overflow-hidden relative">
          <CollapsibleTrigger asChild>
            <div className="px-4 py-4 flex items-center gap-3.5 cursor-pointer relative">
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center"
                style={{ backgroundColor: color + '20' }}
              >
                <Icon size={15} style={{ color }} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <h4 className="text-sm font-semibold text-white truncate">{title}</h4>
                  {result.data_confidence === 'low' && (
                    <Badge variant="warning" className="text-[11px]">Low data</Badge>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  {title === 'Safety' ? (
                    <>
                      {result.score >= 90 && <Badge variant="mono" className="text-[11px] border-pink-500/30 text-pink-400">Woman Safe</Badge>}
                      {result.score >= 70 && result.score < 90 && <Badge variant="mono" className="text-[11px] border-green-500/30 text-green-400">Safe</Badge>}
                      {result.score >= 50 && result.score < 70 && <Badge variant="mono" className="text-[11px] border-yellow-500/30 text-yellow-400">Somewhat Safe</Badge>}
                      {result.score < 50 && <Badge variant="mono" className="text-[11px] border-red-500/30 text-red-400">Not Safe</Badge>}
                    </>
                  ) : (
                    <Badge variant={scoreBadgeVariant(result.score)} className="text-[11px]">{result.label}</Badge>
                  )}
                  {freshness && <span className="text-xs text-white/80">{freshness}</span>}
                </div>
              </div>
              {ringDisplay ? (
                <div className="text-right flex-shrink-0">
                  <span className="font-mono font-bold text-base" style={{ color }}>{ringDisplay}</span>
                  <span className="text-[10px] ml-0.5" style={{ color }}>{icon === 'wind' ? 'AQI' : 'dB'}</span>
                </div>
              ) : (
                <div>
                  <ScoreRing score={result.score} size={42} strokeWidth={3.5} showLabel={true} animated={false}
                    colorOverride={title === 'Safety'
                      ? (result.score >= 90 ? '#ec4899' : result.score >= 70 ? '#22c55e' : result.score >= 50 ? '#fbbf24' : '#f87171')
                      : ringColor
                    } />
                </div>
              )}
              <div className="flex items-center gap-1 text-brand-9">
                {!expanded && <span className="text-xs">Details</span>}
                <div className={`transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}>
                  <ChevronDown size={13} />
                </div>
              </div>
            </div>
          </CollapsibleTrigger>

          <CollapsibleContent>
            <div className="px-4 pb-5 border-t border-white/[0.08] pt-4 space-y-4 max-h-[400px] overflow-y-auto scrollbar-thin">
              <div className="space-y-1.5">
                {Object.entries(result.breakdown).map(([key, val]) => {
                  if (val == null || typeof val === 'object') return null;
                  let display = String(val);
                  const k = key.toLowerCase();
                  if (typeof val === 'number') {
                    const raw = val % 1 === 0 ? String(val) : val.toFixed(1);
                    if (k.includes('pct')) display = `${raw}%`;
                    else if (k.endsWith('_km')) display = `${raw} km`;
                    else if (k.endsWith('_min') || k.includes('minutes')) {
                      const mins = Number(raw);
                      if (mins >= 60) {
                        const h = Math.floor(mins / 60);
                        const m = Math.round(mins % 60);
                        display = m > 0 ? `${h}h ${m}m` : `${h}h`;
                      } else {
                        display = `${raw} min`;
                      }
                    }
                    else if (k.includes('lakh')) display = `₹${raw}L`;
                    else if (k.includes('_rs') || k.includes('rent') || k.includes('price') || k.includes('emi') || k.includes('maintenance')) display = `₹${Number(raw).toLocaleString('en-IN')}`;
                    else display = raw;
                  }
                  if (typeof val === 'boolean') display = val ? 'Yes' : 'No';
                  return (
                    <div key={key} className="flex justify-between text-xs">
                      <span className="text-white/80">{key.replace(/_/g, ' ')}</span>
                      <span className="text-white font-mono font-medium">{display}</span>
                    </div>
                  );
                })}
              </div>

              {transitResult && (
                <div className="space-y-2">
                  <p className="text-xs text-white/90 uppercase tracking-widest font-semibold">Nearest Transit</p>
                  {transitResult.nearest_metro && <TransitRow detail={transitResult.nearest_metro} icon="🚇" />}
                  {transitResult.nearest_bus_stop && <TransitRow detail={transitResult.nearest_bus_stop} icon="🚌" />}
                  {transitResult.nearest_train && <TransitRow detail={transitResult.nearest_train} icon="🚆" />}

                  <p className="text-xs text-white/90 uppercase tracking-widest font-semibold pt-1">Key Hubs</p>
                  {transitResult.airport && <TransitRow detail={transitResult.airport} icon="✈️" />}
                  {transitResult.majestic && <TransitRow detail={transitResult.majestic} icon="🚏" />}
                  {transitResult.city_railway && <TransitRow detail={transitResult.city_railway} icon="🚉" />}
                </div>
              )}

              {builderResult && builderResult.builders.length > 0 && (
                <div className="space-y-1.5">
                  <p className="text-xs text-white/90 uppercase tracking-widest font-semibold">Builders</p>
                  {builderResult.builders.slice(0, 5).map((b) => (
                    <div key={b.name} className="flex items-center justify-between text-xs rounded-lg bg-white/[0.05] border border-white/[0.08] px-3 py-2">
                      <span className="text-white/90">{b.name}</span>
                      <span className="font-mono font-semibold" style={{ color: getScoreColor(b.score) }}>{b.score}</span>
                    </div>
                  ))}
                </div>
              )}

              {result.details.length > 0 && !builderResult && (
                <div className="space-y-1.5">
                  <p className="text-xs text-white/90 uppercase tracking-widest font-semibold">Nearby</p>
                  {result.details.slice(0, 5).map((d, i) => (
                    <div key={i} className="rounded-lg bg-white/[0.05] border border-white/[0.08] px-3 py-2 flex justify-between text-xs">
                      <span className="text-white/90 truncate mr-2">{d.name}</span>
                      <span className="text-white/90 whitespace-nowrap font-mono">{d.distance_km} km</span>
                    </div>
                  ))}
                </div>
              )}

              <div>
                <p className="text-[11px] text-white/80 uppercase tracking-widest font-semibold mb-0.5">Sources</p>
                <p className="text-[11px] text-white/80">{result.sources.join(' · ')}</p>
              </div>
            </div>
          </CollapsibleContent>
        </div>
      </Collapsible>
    );
  }

  return null;
}
