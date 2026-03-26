interface Props {
  label: string;
  value: string;
  sublabel?: string;
  color?: string;
}

export default function MetricCard({ label, value, sublabel, color = 'text-brand-9' }: Props) {
  return (
    <div className="rounded-lg bg-white/[0.04] border border-white/[0.08] px-3 py-2.5 text-center">
      <div className="text-[10px] text-white/50 uppercase tracking-wider mb-0.5">{label}</div>
      <div className={`text-base font-bold font-mono ${color}`}>{value}</div>
      {sublabel && <div className="text-[9px] text-white/40 mt-0.5">{sublabel}</div>}
    </div>
  );
}
