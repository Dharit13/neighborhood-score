interface Props {
  label: string;
  value: string;
  sublabel?: string;
  color?: string;
}

export default function MetricCard({ label, value, sublabel, color = 'text-[#b91c1c]' }: Props) {
  return (
    <div className="rounded-lg bg-white/40 border border-[#d0c8b8] px-3 py-2.5 text-center">
      <div className="text-[10px] uppercase tracking-wider mb-0.5" style={{ color: '#8a8a8a' }}>{label}</div>
      <div className={`text-base font-bold font-mono ${color}`}>{value}</div>
      {sublabel && <div className="text-[9px] mt-0.5" style={{ color: '#a09888' }}>{sublabel}</div>}
    </div>
  );
}
