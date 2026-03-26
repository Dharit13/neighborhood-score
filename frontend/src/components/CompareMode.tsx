import { useState } from 'react';
import { motion } from 'framer-motion';
import { Scale, ArrowRightLeft } from 'lucide-react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { ShuffleNumber } from '@/components/ui/shuffle-number';
import TetrisLoading from '@/components/ui/tetris-loader';
import NeighborhoodInput from './NeighborhoodInput';
import type { NeighborhoodScoreResponse } from '../types';

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
interface Props {}

const RAW_COLORS = ['#5b9cf5', '#2ad587'];

const PRESET_LOCATIONS = [
  'Indiranagar', 'Koramangala', 'Whitefield', 'HSR Layout',
  'Jayanagar', 'Malleshwaram', 'Electronic City', 'Hebbal',
  'JP Nagar', 'Marathahalli', 'Banashankari', 'Sarjapur Road',
];

const DIMENSIONS: { key: keyof NeighborhoodScoreResponse; label: string }[] = [
  { key: 'safety', label: 'Safety' },
  { key: 'property_prices', label: 'Affordability' },
  { key: 'transit_access', label: 'Transit' },
  { key: 'flood_risk', label: 'Flood Risk' },
  { key: 'commute', label: 'Commute' },
  { key: 'walkability', label: 'Walk' },
  { key: 'hospital_access', label: 'Hospitals' },
  { key: 'water_supply', label: 'Water' },
  { key: 'air_quality', label: 'Air Quality' },
  { key: 'school_access', label: 'Schools' },
  { key: 'noise', label: 'Noise' },
  { key: 'power_reliability', label: 'Power' },
  { key: 'future_infrastructure', label: 'Future Infra' },
  { key: 'builder_reputation', label: 'Builders' },
  { key: 'delivery_coverage', label: 'Delivery' },
  { key: 'business_opportunity', label: 'Business' },
  { key: 'cleanliness', label: 'Cleanliness' },
];

function readableName(address: string): string {
  const parts = address.split(',').map(p => p.trim());
  const readable = parts.find(p => !/^[A-Z0-9+]{4,}\+/.test(p) && !/^\d+[A-Z]?$/.test(p));
  return readable || parts[0] || 'Unknown';
}

function getScoreColor(score: number) {
  if (score >= 75) return 'text-slate-300';
  if (score >= 68) return 'text-blue-400';
  if (score >= 60) return 'text-brand-9';
  if (score >= 52) return 'text-amber-400';
  return 'text-red-400';
}

async function fetchOne(addr: string): Promise<NeighborhoodScoreResponse> {
  const resp = await fetch('/api/scores', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ address: addr.trim() }),
  });
  if (!resp.ok) {
    const err = await resp.json();
    let detail = 'Failed to compute scores';
    if (typeof err.detail === 'string') detail = err.detail;
    else if (Array.isArray(err.detail)) detail = 'This location is outside the supported area';
    throw new Error(detail);
  }
  return resp.json();
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export default function CompareMode(_props: Props) {
  const [addresses, setAddresses] = useState<string[]>(['', '']);
  const [results, setResults] = useState<(NeighborhoodScoreResponse | null)[]>([null, null]);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canCompare = addresses[0].trim() && addresses[1].trim() && !comparing;

  const handleCompare = async () => {
    if (!canCompare) return;
    setComparing(true);
    setError(null);
    setResults([null, null]);

    try {
      const [r0, r1] = await Promise.all([
        fetchOne(addresses[0]),
        fetchOne(addresses[1]),
      ]);
      setResults([r0, r1]);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to compare');
    } finally {
      setComparing(false);
    }
  };

  const handlePreset = (idx: number, preset: string) => {
    setAddresses(prev => { const n = [...prev]; n[idx] = preset; return n; });
  };

  const loaded = results.filter(Boolean) as NeighborhoodScoreResponse[];

  const radarData = DIMENSIONS.map((dim) => {
    const entry: Record<string, unknown> = { metric: dim.label };
    loaded.forEach((r, i) => {
      const val = r[dim.key] as { score: number } | undefined;
      entry[`score${i}`] = val?.score ?? 0;
    });
    return entry;
  });

  return (
    <div className="space-y-6">
      <div className="sticky top-12 z-20 bg-black/50 backdrop-blur-md pb-4 pt-2">
        <h1 className="text-2xl sm:text-3xl font-semibold text-foreground text-center mb-4">
          Compare Neighborhoods
        </h1>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl mx-auto">
          {addresses.map((addr, idx) => (
            <div key={idx} className="space-y-2">
              <NeighborhoodInput
                value={addr}
                onChange={(val) => setAddresses(prev => { const n = [...prev]; n[idx] = val; return n; })}
                placeholder={idx === 0 ? 'Neighborhood 1...' : 'Neighborhood 2...'}
                className="w-full"
              />
              <div className="flex flex-wrap gap-1">
                {PRESET_LOCATIONS.slice(idx * 4, idx * 4 + 4).map(p => (
                  <button key={p} onClick={() => handlePreset(idx, p)}
                    className="text-xs px-2 py-1 glass-button rounded-full text-white/60 hover:text-foreground transition">
                    {p}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="flex justify-center mt-4">
          <button
            onClick={handleCompare}
            disabled={!canCompare}
            className="px-6 py-2.5 text-sm font-semibold rounded-full text-white transition-all hover:scale-105 disabled:opacity-40 disabled:hover:scale-100 flex items-center gap-2"
            style={{
              background: canCompare ? 'linear-gradient(135deg, var(--brand-1), var(--brand-9))' : undefined,
              boxShadow: canCompare ? '0 0 20px rgba(42,213,135,0.25)' : undefined,
            }}
          >
            <ArrowRightLeft size={15} />
            {comparing ? 'Comparing...' : 'Compare'}
          </button>
        </div>

        {error && (
          <p className="text-red-400 text-sm text-center mt-3">{error}</p>
        )}
      </div>

      {comparing && (
        <div className="flex flex-col items-center justify-center py-12">
          <TetrisLoading size="sm" speed="fast" loadingText="Computing scores..." />
          <p className="text-xs text-white/60 mt-2">Analyzing 17 dimensions across transit, safety, infrastructure & more</p>
        </div>
      )}

      {loaded.length >= 2 && !comparing && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="rounded-xl bg-white/[0.03] backdrop-blur-sm p-6 max-w-4xl mx-auto"
        >
          <h3 className="text-sm font-semibold gradient-text mb-4 text-center uppercase tracking-widest">Score Overlay</h3>
          <ResponsiveContainer width="100%" height={400}>
            <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="65%">
              <PolarGrid className="stroke-white/10" strokeDasharray="3 3" />
              <PolarAngleAxis dataKey="metric" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10 }} />
              <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 9 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(0,0,0,0.9)',
                  border: '1px solid rgba(42,213,135,0.2)',
                  borderRadius: '8px',
                  color: 'white',
                  fontSize: '12px',
                  backdropFilter: 'blur(12px)',
                }}
              />
              <Legend />
              {loaded.map((r, i) => (
                <Radar
                  key={i}
                  name={readableName(r.address)}
                  dataKey={`score${i}`}
                  stroke={RAW_COLORS[i]}
                  fill={RAW_COLORS[i]}
                  fillOpacity={0.1}
                  strokeWidth={2}
                />
              ))}
            </RadarChart>
          </ResponsiveContainer>
        </motion.div>
      )}

      {loaded.length >= 2 && !comparing && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="max-w-4xl mx-auto space-y-3"
        >
          <div className="flex items-center py-3">
            <div className="flex-1 text-center text-sm font-semibold" style={{ color: RAW_COLORS[0] }}>
              {readableName(loaded[0].address)}
            </div>
            <div className="w-28" />
            <div className="flex-1 text-center text-sm font-semibold" style={{ color: RAW_COLORS[1] }}>
              {readableName(loaded[1].address)}
            </div>
          </div>

          <div className="flex items-center rounded-xl bg-white/[0.04] py-4">
            <div className="flex-1 text-center">
              <span className={`text-3xl font-bold font-mono ${getScoreColor(loaded[0].composite_score)}`}>
                <ShuffleNumber value={loaded[0].composite_score} />
              </span>
            </div>
            <div className="w-28 text-center text-sm font-semibold text-white">Overall</div>
            <div className="flex-1 text-center">
              <span className={`text-3xl font-bold font-mono ${getScoreColor(loaded[1].composite_score)}`}>
                <ShuffleNumber value={loaded[1].composite_score} />
              </span>
            </div>
          </div>

          {DIMENSIONS.map((dim, rowIdx) => {
            const s0 = (loaded[0][dim.key] as { score: number } | undefined)?.score ?? 0;
            const s1 = (loaded[1][dim.key] as { score: number } | undefined)?.score ?? 0;
            const winner = s0 > s1 ? 0 : s1 > s0 ? 1 : -1;

            return (
              <motion.div
                key={dim.key}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: rowIdx * 0.02 }}
                className="flex items-center rounded-lg py-2.5 hover:bg-white/[0.02] transition"
              >
                <div className="flex-1 text-center">
                  <span className={`font-semibold font-mono ${getScoreColor(s0)} ${winner === 0 ? 'text-base' : 'text-sm'}`}>
                    {Math.round(s0 * 10) / 10}
                  </span>
                  {winner === 0 && <span className="ml-1 text-[10px] text-brand-9/60">●</span>}
                </div>
                <div className="w-28 text-center text-sm text-white/70">{dim.label}</div>
                <div className="flex-1 text-center">
                  <span className={`font-semibold font-mono ${getScoreColor(s1)} ${winner === 1 ? 'text-base' : 'text-sm'}`}>
                    {Math.round(s1 * 10) / 10}
                  </span>
                  {winner === 1 && <span className="ml-1 text-[10px] text-brand-9/60">●</span>}
                </div>
              </motion.div>
            );
          })}
        </motion.div>
      )}

      {loaded.length < 2 && !comparing && (
        <div className="text-center py-16">
          <div className="float-animation inline-block mb-3">
            <Scale size={48} className="text-brand-9/30" />
          </div>
          <h3 className="text-lg gradient-text mb-2">Enter 2 neighborhoods to compare</h3>
          <p className="text-sm text-white/60 max-w-md mx-auto">
            See all 17 scores side by side with radar overlay. Pick the best neighborhood for your needs.
          </p>
        </div>
      )}
    </div>
  );
}
