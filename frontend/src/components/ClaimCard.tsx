import { motion } from 'framer-motion';
import { ArrowRight, MapPin } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { ClaimVerification } from '@/types';

function verdictVariant(verdict: string) {
  switch (verdict) {
    case 'ACCURATE': return 'success' as const;
    case 'SLIGHTLY_OPTIMISTIC': return 'warning' as const;
    case 'MISLEADING':
    case 'SIGNIFICANTLY_MISLEADING': return 'destructive' as const;
    default: return 'mono' as const;
  }
}

function verdictColor(verdict: string) {
  switch (verdict) {
    case 'ACCURATE': return 'text-brand-9';
    case 'SLIGHTLY_OPTIMISTIC': return 'text-amber-400';
    case 'MISLEADING':
    case 'SIGNIFICANTLY_MISLEADING': return 'text-red-400';
    default: return 'text-white/60';
  }
}

interface Props {
  claim: ClaimVerification;
  index: number;
}

export default function ClaimCard({ claim, index }: Props) {
  const d = claim.details;
  const hasCoords = d.destination_lat != null && d.destination_lng != null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08 }}
      className="rounded-xl bg-white/[0.03] backdrop-blur-sm border border-white/[0.08] hover:border-white/[0.14] transition-colors overflow-hidden"
    >
      <div className="p-4">
        {/* Claim vs Reality */}
        <div className="flex items-start gap-3">
          {/* Speech bubble: the builder's claim */}
          <div className="flex-1 min-w-0">
            <div className="rounded-lg bg-white/[0.06] px-3 py-2 relative">
              <p className="text-sm text-white/90 italic">"{claim.original_claim}"</p>
              <div className="absolute -bottom-1 left-4 w-2 h-2 bg-white/[0.06] rotate-45" />
            </div>
          </div>

          <ArrowRight size={16} className="text-white/30 mt-3 flex-shrink-0" />

          {/* Reality */}
          <div className="flex-1 min-w-0 text-right">
            <div className={`text-lg font-bold font-mono ${verdictColor(claim.verdict)}`}>
              {claim.actual_value}
            </div>
            {d.peak_duration_min != null && d.offpeak_duration_min != null && d.peak_duration_min !== d.offpeak_duration_min && (
              <div className="text-[10px] text-white/50">
                Off-peak: {d.offpeak_duration_min} min
              </div>
            )}
          </div>
        </div>

        {/* Stats row */}
        <div className="flex items-center gap-2 mt-3">
          <div className="grid grid-cols-3 gap-2 flex-1 text-center">
            <div className="rounded-lg bg-white/[0.03] px-2 py-1.5">
              <div className="text-[9px] text-white/50 uppercase tracking-wide">Claimed</div>
              <div className="text-sm font-bold text-brand-9 font-mono">{claim.claimed_value}</div>
            </div>
            <div className="rounded-lg bg-white/[0.03] px-2 py-1.5">
              <div className="text-[9px] text-white/50 uppercase tracking-wide">Actual</div>
              <div className={`text-sm font-bold font-mono ${verdictColor(claim.verdict)}`}>{claim.actual_value}</div>
            </div>
            <div className="rounded-lg bg-white/[0.03] px-2 py-1.5">
              <div className="text-[9px] text-white/50 uppercase tracking-wide">Gap</div>
              <div className="text-sm font-bold text-red-400 font-mono">{claim.difference}</div>
            </div>
          </div>
        </div>

        {/* Verdict + metadata */}
        <div className="flex items-center justify-between mt-3">
          <Badge variant={verdictVariant(claim.verdict)} className="text-[10px]">
            {claim.verdict.replace(/_/g, ' ')}
          </Badge>
          <div className="flex items-center gap-2">
            {d.ratio != null && (
              <span className="text-[10px] text-white/40 font-mono">{d.ratio}x multiplier</span>
            )}
            {d.destination && (
              <span className="text-[10px] text-white/50 flex items-center gap-1">
                {hasCoords && <MapPin size={9} />}
                {d.destination}
                {d.destination_category && <span className="text-white/30">({d.destination_category})</span>}
              </span>
            )}
          </div>
        </div>

        {/* Explanation */}
        {d.explanation && (
          <p className="text-[11px] text-white/50 mt-2 leading-relaxed">{d.explanation}</p>
        )}
        {d.nearest && (
          <p className="text-[11px] text-white/50 mt-1">Nearest: {d.nearest}</p>
        )}
        {d.note && (
          <p className="text-[11px] text-white/50 mt-1">{d.note}</p>
        )}
      </div>
    </motion.div>
  );
}
