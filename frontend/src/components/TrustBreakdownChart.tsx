import { motion } from 'framer-motion';

interface Props {
  breakdown: Record<string, number>;
}

const DIMENSION_LABELS: Record<string, string> = {
  delivery: 'Delivery',
  legal: 'Legal',
  financial: 'Financial',
  satisfaction: 'Satisfaction',
  quality: 'Quality',
  delivery_track_record: 'Delivery',
  legal_compliance: 'Legal',
  financial_health: 'Financial',
  customer_satisfaction: 'Satisfaction',
  project_quality: 'Quality',
};

function barColor(score: number): string {
  if (score >= 75) return '#16a34a';
  if (score >= 55) return '#2563eb';
  if (score >= 40) return '#ca8a04';
  return '#dc2626';
}

export default function TrustBreakdownChart({ breakdown }: Props) {
  const entries = Object.entries(breakdown).map(([key, val]) => ({
    key,
    label: DIMENSION_LABELS[key] || key.replace(/_/g, ' '),
    score: typeof val === 'number' ? val : 0,
  }));

  if (entries.length === 0) return null;

  return (
    <div className="space-y-2">
      {entries.map((entry, i) => (
        <div key={entry.key} className="flex items-center gap-3">
          <span className="text-[11px] text-white/70 w-24 text-right capitalize">{entry.label}</span>
          <div className="flex-1 h-3 bg-white/[0.06] rounded-full overflow-hidden">
            <motion.div
              className="h-full rounded-full"
              style={{ backgroundColor: barColor(entry.score) }}
              initial={{ width: 0 }}
              animate={{ width: `${entry.score}%` }}
              transition={{ duration: 0.6, delay: i * 0.1, ease: 'easeOut' }}
            />
          </div>
          <span className="text-[11px] font-mono font-bold w-8" style={{ color: barColor(entry.score) }}>
            {entry.score}
          </span>
        </div>
      ))}
    </div>
  );
}
