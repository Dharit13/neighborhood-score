import { useState, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Star, AlertTriangle, ChevronDown, Sparkles } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import TrustScoreCircle from './TrustScoreCircle';
import TrustBreakdownChart from './TrustBreakdownChart';
import type { BuilderSummary } from '@/types';

function tierBadgeVariant(tier: string | null) {
  switch (tier) {
    case 'trusted': return 'success' as const;
    case 'emerging': return 'info' as const;
    case 'cautious': return 'warning' as const;
    case 'avoid': return 'destructive' as const;
    default: return 'mono' as const;
  }
}

interface Props {
  builder: BuilderSummary;
  onClick?: () => void;
  index?: number;
  aiBrief?: string;
}

export default function BuilderCard({ builder, onClick, index = 0, aiBrief }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [glowPos, setGlowPos] = useState({ x: 50, y: 50 });
  const [expanded, setExpanded] = useState(false);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    setTilt({ x: (y - 0.5) * -4, y: (x - 0.5) * 4 });
    setGlowPos({ x: x * 100, y: y * 100 });
  }, []);

  const score = builder.trust_score ?? 0;
  const hasRisk = builder.complaints > 15;

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0, rotateX: tilt.x, rotateY: tilt.y }}
      transition={{ type: 'spring', stiffness: 300, damping: 20, delay: index * 0.06 }}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setTilt({ x: 0, y: 0 })}
      style={{ transformStyle: 'preserve-3d', perspective: '800px' }}
      className="relative overflow-hidden rounded-xl bg-white/[0.04] hover:bg-white/[0.07] border border-white/[0.10] hover:border-brand-9/20 transition-colors cursor-pointer"
      onClick={() => {
        if (onClick) onClick();
        else setExpanded(!expanded);
      }}
    >
      {/* Hover glow */}
      <div
        className="absolute inset-0 pointer-events-none transition-opacity duration-300"
        style={{
          background: `radial-gradient(circle at ${glowPos.x}% ${glowPos.y}%, rgba(42,213,135,0.08), transparent 60%)`,
          opacity: tilt.x !== 0 || tilt.y !== 0 ? 1 : 0,
        }}
      />

      <div className="relative p-3 flex items-center gap-3" style={{ transform: 'translateZ(5px)' }}>
        {/* Trust circle */}
        <TrustScoreCircle score={score} size={48} strokeWidth={3.5} animated={false} />

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-semibold text-white truncate">{builder.name}</h4>
            <Badge variant={tierBadgeVariant(builder.trust_tier)} className="text-[9px] flex-shrink-0">
              {builder.trust_tier || 'unscored'}
            </Badge>
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            {builder.segment && (
              <Badge variant="mono" className="text-[9px]">{builder.segment}</Badge>
            )}
            {builder.avg_rating != null && (
              <span className="flex items-center gap-0.5 text-[10px] text-amber-400">
                <Star size={9} fill="currentColor" />
                {builder.avg_rating.toFixed(1)}
              </span>
            )}
            <span className="text-[10px] text-white/40">{builder.rera_projects} projects</span>
          </div>
        </div>

        {/* Risk indicators */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {hasRisk && (
            <Badge variant="destructive" className="text-[9px] gap-0.5">
              <AlertTriangle size={9} /> {builder.complaints}
            </Badge>
          )}
          <motion.div animate={{ rotate: expanded ? 180 : 0 }} transition={{ duration: 0.2 }}>
            <ChevronDown size={14} className="text-white/30" />
          </motion.div>
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className="border-t border-white/[0.06] px-3 pb-3"
        >
          <div className="pt-3 space-y-3">
            {builder.notable_projects.length > 0 && (
              <div>
                <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Notable Projects</p>
                <div className="flex flex-wrap gap-1">
                  {builder.notable_projects.slice(0, 5).map(p => (
                    <Badge key={p} variant="mono" className="text-[9px]">{p}</Badge>
                  ))}
                </div>
              </div>
            )}

            {builder.trust_score_breakdown && (
              <div>
                <p className="text-[10px] text-white/40 uppercase tracking-wider mb-2">Trust Breakdown</p>
                <TrustBreakdownChart breakdown={builder.trust_score_breakdown} />
              </div>
            )}

            <div className="flex gap-3 text-[10px] text-white/50">
              <span>On-time: <strong className="text-white/80">{builder.on_time_delivery_pct}%</strong></span>
              <span>Complaints: <strong className="text-white/80">{builder.complaints}</strong></span>
              <span>Ratio: <strong className="text-white/80">{builder.complaints_ratio.toFixed(2)}</strong></span>
            </div>

            {aiBrief && (
              <div className="rounded-lg bg-white/[0.03] border border-white/[0.06] p-3">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <Sparkles size={10} className="text-brand-9" />
                  <span className="text-[9px] font-bold uppercase tracking-widest text-white/40">AI Brief</span>
                </div>
                <p className="text-xs text-white/80 leading-relaxed">{aiBrief}</p>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
