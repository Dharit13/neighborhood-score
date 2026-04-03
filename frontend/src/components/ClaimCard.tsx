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
    case 'ACCURATE': return 'text-emerald-700';
    case 'SLIGHTLY_OPTIMISTIC': return 'text-amber-700';
    case 'MISLEADING':
    case 'SIGNIFICANTLY_MISLEADING': return 'text-red-700';
    default: return 'text-[#8a8a8a]';
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
      className="rounded-xl bg-white/40 border border-[#d0c8b8] hover:border-[#a09888] transition-colors overflow-hidden"
    >
      <div className="p-4">
        {/* Claim vs Reality */}
        <div className="flex items-start gap-3">
          {/* Speech bubble: the builder's claim */}
          <div className="flex-1 min-w-0">
            <div className="rounded-lg px-3 py-2 relative" style={{ background: 'rgba(232,224,208,0.6)' }}>
              <p className="text-sm italic" style={{ color: '#1a1a1a' }}>"{claim.original_claim}"</p>
              <div className="absolute -bottom-1 left-4 w-2 h-2 rotate-45" style={{ background: 'rgba(232,224,208,0.6)' }} />
            </div>
          </div>

          <ArrowRight size={16} className="mt-3 flex-shrink-0" style={{ color: '#a09888' }} />

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
            <div className="rounded-lg px-2 py-1.5" style={{ background: 'rgba(232,224,208,0.4)' }}>
              <div className="text-[9px] uppercase tracking-wide" style={{ color: '#8a8a8a' }}>Claimed</div>
              <div className="text-sm font-bold font-mono" style={{ color: '#b91c1c' }}>{claim.claimed_value}</div>
            </div>
            <div className="rounded-lg px-2 py-1.5" style={{ background: 'rgba(232,224,208,0.4)' }}>
              <div className="text-[9px] uppercase tracking-wide" style={{ color: '#8a8a8a' }}>Actual</div>
              <div className={`text-sm font-bold font-mono ${verdictColor(claim.verdict)}`}>{claim.actual_value}</div>
            </div>
            <div className="rounded-lg px-2 py-1.5" style={{ background: 'rgba(232,224,208,0.4)' }}>
              <div className="text-[9px] uppercase tracking-wide" style={{ color: '#8a8a8a' }}>Gap</div>
              <div className="text-sm font-bold text-red-700 font-mono">{claim.difference}</div>
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
              <span className="text-[10px] font-mono" style={{ color: '#a09888' }}>{d.ratio}x multiplier</span>
            )}
            {d.destination && (
              <span className="text-[10px] flex items-center gap-1" style={{ color: '#8a8a8a' }}>
                {hasCoords && <MapPin size={9} />}
                {d.destination}
                {d.destination_category && <span style={{ color: '#a09888' }}>({d.destination_category})</span>}
              </span>
            )}
          </div>
        </div>

        {/* Explanation */}
        {d.explanation && (
          <p className="text-[11px] mt-2 leading-relaxed" style={{ color: '#8a8a8a' }}>{d.explanation}</p>
        )}
        {d.nearest && (
          <p className="text-[11px] mt-1" style={{ color: '#8a8a8a' }}>Nearest: {d.nearest}</p>
        )}
        {d.note && (
          <p className="text-[11px] mt-1" style={{ color: '#8a8a8a' }}>{d.note}</p>
        )}
      </div>
    </motion.div>
  );
}
