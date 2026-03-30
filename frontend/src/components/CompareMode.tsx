import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Section3DHeading from './Section3DHeading';
import ScrollReveal3D from './ScrollReveal3D';
import { Sparkles, ChevronLeft, RotateCcw, Wallet, MapPin, Heart, User } from 'lucide-react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { ShuffleNumber } from '@/components/ui/shuffle-number';
import TetrisLoading from '@/components/ui/tetris-loader';
import type { NeighborhoodScoreResponse, RecommendItem } from '../types';

const RAW_COLORS = ['#5b9cf5', '#2ad587', '#f5a623'];

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

function matchColor(score: number) {
  if (score >= 90) return 'from-emerald-500 to-green-400';
  if (score >= 75) return 'from-blue-500 to-cyan-400';
  return 'from-amber-500 to-yellow-400';
}

// ---- Question config ----

const BUY_BUDGETS = ['Under 60L', '60L-1Cr', '1Cr-1.5Cr', '1.5Cr-2.5Cr', '2.5Cr+'];
const RENT_BUDGETS = ['Under 20K', '20-35K', '35-50K', '50K+'];

const COMMUTE_PRESETS = [
  'Manyata Tech Park', 'Whitefield IT', 'Electronic City', 'MG Road', 'Work from Home',
];

const PRIORITIES = [
  { id: 'safety', label: 'Safety', emoji: '🛡️' },
  { id: 'good_schools', label: 'Good Schools', emoji: '🎓' },
  { id: 'metro_access', label: 'Metro Access', emoji: '🚇' },
  { id: 'low_flooding', label: 'Low Flooding', emoji: '🌧️' },
  { id: 'clean_air', label: 'Clean Air', emoji: '🌿' },
  { id: 'nightlife_food', label: 'Nightlife & Food', emoji: '🍕' },
  { id: 'green_walkable', label: 'Green & Walkable', emoji: '🚶' },
  { id: 'investment_growth', label: 'Investment Growth', emoji: '📈' },
];

const LIFESTYLES = [
  { id: 'young_professional', label: 'Young Professional', desc: 'Commute, nightlife, convenience', icon: '💼' },
  { id: 'family_with_kids', label: 'Family with Kids', desc: 'Schools, safety, parks', icon: '👨‍👩‍👧' },
  { id: 'retired', label: 'Retired', desc: 'Peace, hospitals, green spaces', icon: '🌅' },
  { id: 'investor', label: 'Investor', desc: 'Growth, infra, rental yield', icon: '📊' },
];

type Step = 'budget' | 'commute' | 'priorities' | 'lifestyle';
const STEPS: Step[] = ['budget', 'commute', 'priorities', 'lifestyle'];
const STEP_ICONS = [Wallet, MapPin, Heart, User];

interface Answers {
  budgetType: 'buy' | 'rent';
  budgetRange: string;
  commute: string;
  priorities: string[];
  lifestyle: string;
}

export default function CompareMode() {
  const [step, setStep] = useState(0); // 0-3 = questions, 4 = loading/results
  const [answers, setAnswers] = useState<Answers>({
    budgetType: 'buy',
    budgetRange: '',
    commute: '',
    priorities: [],
    lifestyle: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<RecommendItem[] | null>(null);

  const canNext = () => {
    if (step === 0) return !!answers.budgetRange;
    if (step === 1) return !!answers.commute;
    if (step === 2) return answers.priorities.length >= 1 && answers.priorities.length <= 3;
    if (step === 3) return !!answers.lifestyle;
    return false;
  };

  const handleNext = () => {
    if (step < 3) {
      setStep(step + 1);
    } else {
      handleSubmit();
    }
  };

  const handleBack = () => {
    if (step > 0) setStep(step - 1);
  };

  const handleSubmit = async () => {
    setStep(4);
    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const resp = await fetch('/api/ai-recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          budget_type: answers.budgetType,
          budget_range: answers.budgetRange,
          commute_destination: answers.commute === 'Work from Home' ? null : answers.commute,
          priorities: answers.priorities,
          lifestyle: answers.lifestyle,
        }),
      });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(typeof err.detail === 'string' ? err.detail : 'Recommendation failed');
      }
      const data = await resp.json();
      setResults(data.recommendations);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  const handleStartOver = () => {
    setStep(0);
    setAnswers({ budgetType: 'buy', budgetRange: '', commute: '', priorities: [], lifestyle: '' });
    setResults(null);
    setError(null);
  };

  const togglePriority = (id: string) => {
    setAnswers(prev => {
      const has = prev.priorities.includes(id);
      if (has) return { ...prev, priorities: prev.priorities.filter(p => p !== id) };
      if (prev.priorities.length >= 3) return prev;
      return { ...prev, priorities: [...prev.priorities, id] };
    });
  };

  // Results data
  const loaded = results?.map(r => r.scores).filter(Boolean) as NeighborhoodScoreResponse[] | undefined;

  const radarData = loaded && loaded.length >= 3 ? DIMENSIONS.map((dim) => {
    const entry: Record<string, unknown> = { metric: dim.label };
    loaded.forEach((r, i) => {
      const val = r[dim.key] as { score: number } | undefined;
      entry[`score${i}`] = val?.score ?? 0;
    });
    return entry;
  }) : [];

  return (
    <div className="space-y-6">
      <Section3DHeading
        title="Find Your Neighborhood"
        subtitle="Answer a few questions — AI recommends 3 neighborhoods tailored to you"
        className="mb-4"
      />

      {/* Progress dots */}
      {step < 4 && (
        <div className="flex items-center justify-center gap-2 mb-6">
          {STEPS.map((_, i) => {
            const Icon = STEP_ICONS[i];
            return (
              <div key={i} className="flex items-center gap-2">
                <button
                  onClick={() => i < step && setStep(i)}
                  aria-current={i === step ? 'step' : undefined}
                  aria-label={`Step ${i + 1}: ${STEPS[i]}`}
                  className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                    i === step
                      ? 'bg-brand-9 text-black scale-110'
                      : i < step
                        ? 'bg-brand-9/30 text-brand-9 cursor-pointer hover:bg-brand-9/50'
                        : 'bg-white/[0.06] text-white/30'
                  }`}
                >
                  <Icon size={14} />
                </button>
                {i < STEPS.length - 1 && (
                  <div className={`w-8 h-0.5 rounded-full ${i < step ? 'bg-brand-9/40' : 'bg-white/[0.06]'}`} />
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Question slides */}
      <AnimatePresence mode="wait">
        {step === 0 && (
          <motion.div
            key="q-budget"
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -40 }}
            transition={{ duration: 0.25 }}
            className="max-w-2xl mx-auto space-y-5"
          >
            <h2 className="text-xl font-semibold text-white text-center">What's your 2BHK budget?</h2>

            {/* Buy / Rent toggle */}
            <div className="flex justify-center gap-2">
              {(['buy', 'rent'] as const).map(t => (
                <button
                  key={t}
                  aria-pressed={answers.budgetType === t}
                  onClick={() => setAnswers(prev => ({ ...prev, budgetType: t, budgetRange: '' }))}
                  className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all ${
                    answers.budgetType === t
                      ? 'bg-brand-9/20 text-brand-9 border border-brand-9/40'
                      : 'bg-white/[0.04] text-white/50 border border-white/[0.08] hover:border-white/20'
                  }`}
                >
                  {t === 'buy' ? 'Buy' : 'Rent'}
                </button>
              ))}
            </div>

            {/* Budget pills */}
            <div className="flex flex-wrap justify-center gap-2">
              {(answers.budgetType === 'buy' ? BUY_BUDGETS : RENT_BUDGETS).map(b => (
                <button
                  key={b}
                  aria-pressed={answers.budgetRange === b}
                  onClick={() => setAnswers(prev => ({ ...prev, budgetRange: b }))}
                  className={`px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    answers.budgetRange === b
                      ? 'bg-brand-9/20 text-brand-9 border border-brand-9/40 scale-105'
                      : 'bg-white/[0.04] text-white/70 border border-white/[0.08] hover:border-white/20 hover:bg-white/[0.06]'
                  }`}
                >
                  {b}
                </button>
              ))}
            </div>
          </motion.div>
        )}

        {step === 1 && (
          <motion.div
            key="q-commute"
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -40 }}
            transition={{ duration: 0.25 }}
            className="max-w-2xl mx-auto space-y-5"
          >
            <h2 className="text-xl font-semibold text-white text-center">Where do you commute to?</h2>

            <div className="flex flex-wrap justify-center gap-2">
              {COMMUTE_PRESETS.map(c => (
                <button
                  key={c}
                  aria-pressed={answers.commute === c}
                  onClick={() => setAnswers(prev => ({ ...prev, commute: c }))}
                  className={`px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    answers.commute === c
                      ? 'bg-brand-9/20 text-brand-9 border border-brand-9/40 scale-105'
                      : 'bg-white/[0.04] text-white/70 border border-white/[0.08] hover:border-white/20 hover:bg-white/[0.06]'
                  }`}
                >
                  {c}
                </button>
              ))}
            </div>

            <div className="flex justify-center">
              <input
                type="text"
                value={COMMUTE_PRESETS.includes(answers.commute) ? '' : answers.commute}
                onChange={e => setAnswers(prev => ({ ...prev, commute: e.target.value }))}
                placeholder="Or type a custom destination..."
                className="w-full max-w-sm rounded-xl border border-white/[0.10] bg-white/[0.04] px-4 py-2.5 text-sm text-white placeholder:text-white/40 outline-none focus:border-brand-9/40 transition-colors"
              />
            </div>
          </motion.div>
        )}

        {step === 2 && (
          <motion.div
            key="q-priorities"
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -40 }}
            transition={{ duration: 0.25 }}
            className="max-w-2xl mx-auto space-y-5"
          >
            <h2 className="text-xl font-semibold text-white text-center">
              What matters most? <span className="text-white/50 font-normal">Pick up to 3</span>
            </h2>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {PRIORITIES.map(p => {
                const selected = answers.priorities.includes(p.id);
                const disabled = !selected && answers.priorities.length >= 3;
                return (
                  <button
                    key={p.id}
                    onClick={() => togglePriority(p.id)}
                    disabled={disabled}
                    className={`py-3 px-3 rounded-xl text-sm font-medium transition-all flex flex-col items-center gap-1.5 ${
                      selected
                        ? 'bg-brand-9/20 text-brand-9 border border-brand-9/40 scale-[1.03]'
                        : disabled
                          ? 'bg-white/[0.02] text-white/20 border border-white/[0.04] cursor-not-allowed'
                          : 'bg-white/[0.04] text-white/70 border border-white/[0.08] hover:border-white/20 hover:bg-white/[0.06]'
                    }`}
                  >
                    <span className="text-lg">{p.emoji}</span>
                    <span>{p.label}</span>
                  </button>
                );
              })}
            </div>
          </motion.div>
        )}

        {step === 3 && (
          <motion.div
            key="q-lifestyle"
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -40 }}
            transition={{ duration: 0.25 }}
            className="max-w-2xl mx-auto space-y-5"
          >
            <h2 className="text-xl font-semibold text-white text-center">What describes you best?</h2>

            <div className="grid grid-cols-2 gap-3">
              {LIFESTYLES.map(l => (
                <button
                  key={l.id}
                  onClick={() => setAnswers(prev => ({ ...prev, lifestyle: l.id }))}
                  className={`py-4 px-4 rounded-xl text-left transition-all ${
                    answers.lifestyle === l.id
                      ? 'bg-brand-9/20 border border-brand-9/40 scale-[1.02]'
                      : 'bg-white/[0.04] border border-white/[0.08] hover:border-white/20 hover:bg-white/[0.06]'
                  }`}
                >
                  <div className="text-2xl mb-2">{l.icon}</div>
                  <div className="text-sm font-semibold text-white">{l.label}</div>
                  <div className="text-xs text-white/50 mt-0.5">{l.desc}</div>
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Navigation buttons */}
      {step >= 0 && step <= 3 && (
        <div className="flex items-center justify-center gap-3 pt-2">
          {step > 0 && (
            <button
              onClick={handleBack}
              className="px-4 py-2 rounded-xl text-sm text-white/60 hover:text-white hover:bg-white/[0.06] transition flex items-center gap-1"
            >
              <ChevronLeft size={14} /> Back
            </button>
          )}
          <button
            onClick={handleNext}
            disabled={!canNext()}
            className="px-6 py-2.5 text-sm font-semibold rounded-xl text-white transition-all hover:scale-105 disabled:opacity-30 disabled:hover:scale-100 flex items-center gap-2"
            style={{
              background: canNext() ? 'linear-gradient(135deg, var(--brand-1), var(--brand-9))' : undefined,
              boxShadow: canNext() ? '0 0 20px rgba(42,213,135,0.25)' : undefined,
            }}
          >
            {step === 3 ? (
              <><Sparkles size={14} /> Find My Neighborhoods</>
            ) : (
              'Next'
            )}
          </button>
        </div>
      )}

      {/* Loading */}
      {step === 4 && loading && (
        <div className="flex flex-col items-center justify-center py-12">
          <TetrisLoading size="sm" speed="fast" loadingText="AI is finding your ideal neighborhoods..." />
          <p className="text-xs text-white/60 mt-2">Analyzing 74 neighborhoods across 17 dimensions</p>
        </div>
      )}

      {/* Error */}
      {step === 4 && error && !loading && (
        <div className="text-center space-y-3">
          <div className="rounded-xl bg-red-500/10 p-4 text-red-400 text-sm max-w-lg mx-auto">{error}</div>
          <button onClick={handleStartOver} className="text-sm text-brand-9 hover:underline flex items-center gap-1 mx-auto">
            <RotateCcw size={12} /> Start over
          </button>
        </div>
      )}

      {/* Results */}
      {step === 4 && results && !loading && loaded && loaded.length >= 3 && (
        <>
          {/* Start over */}
          <div className="flex justify-center">
            <button
              onClick={handleStartOver}
              className="text-sm text-white/50 hover:text-white flex items-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-white/[0.06] transition"
            >
              <RotateCcw size={12} /> Start over
            </button>
          </div>

          {/* AI Recommendation Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 max-w-5xl mx-auto">
            {results.map((rec, i) => (
              <ScrollReveal3D key={i} rotateX={-6} delay={i * 0.08}>
                <div className="rounded-xl bg-white/[0.03] backdrop-blur-sm border border-white/[0.06] p-4 space-y-3 h-full">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base font-semibold" style={{ color: RAW_COLORS[i] }}>
                        {readableName(rec.scores?.address || rec.neighborhood)}
                      </h3>
                      <span className="text-xs text-white/40">#{i + 1} recommendation</span>
                    </div>
                    <div className={`px-2 py-1 rounded-lg text-xs font-bold bg-gradient-to-r ${matchColor(rec.match_score)} text-black`}>
                      {rec.match_score}% match
                    </div>
                  </div>

                  <p className="text-sm text-white/70 leading-relaxed">{rec.reason}</p>

                  <div className="space-y-1">
                    {rec.highlights.map((h, j) => (
                      <div key={j} className="flex items-start gap-2 text-xs text-white/60">
                        <span className="text-brand-9 mt-0.5">•</span>
                        <span>{h}</span>
                      </div>
                    ))}
                  </div>

                  <div className="pt-2 border-t border-white/[0.06] flex items-center justify-between">
                    <span className="text-xs text-white/40">Overall score</span>
                    <span className={`text-lg font-bold font-mono ${getScoreColor(rec.scores?.composite_score || 0)}`}>
                      <ShuffleNumber value={rec.scores?.composite_score || 0} />
                    </span>
                  </div>
                </div>
              </ScrollReveal3D>
            ))}
          </div>

          {/* Radar Chart */}
          <ScrollReveal3D rotateX={-10} translateZ={10}>
            <div className="rounded-xl bg-white/[0.03] backdrop-blur-sm p-6 max-w-5xl mx-auto">
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
            </div>
          </ScrollReveal3D>

          {/* Score Table — 3 columns */}
          <ScrollReveal3D delay={0.05} rotateX={-6}>
            <div className="max-w-5xl mx-auto space-y-2">
              {/* Header */}
              <div className="flex items-center py-3">
                {loaded.map((r, i) => (
                  <div key={i} className="flex-1 text-center text-sm font-semibold" style={{ color: RAW_COLORS[i] }}>
                    {readableName(r.address)}
                  </div>
                ))}
                <div className="w-24" />
              </div>

              {/* Overall */}
              <div className="flex items-center rounded-xl bg-white/[0.04] py-4">
                {loaded.map((r, i) => (
                  <div key={i} className="flex-1 text-center">
                    <span className={`text-2xl font-bold font-mono ${getScoreColor(r.composite_score)}`}>
                      <ShuffleNumber value={r.composite_score} />
                    </span>
                  </div>
                ))}
                <div className="w-24 text-center text-sm font-semibold text-white">Overall</div>
              </div>

              {/* Dimensions */}
              {DIMENSIONS.map((dim, rowIdx) => {
                const scores = loaded.map(r => (r[dim.key] as { score: number } | undefined)?.score ?? 0);
                const maxScore = Math.max(...scores);

                return (
                  <motion.div
                    key={dim.key}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: rowIdx * 0.02 }}
                    className="flex items-center rounded-lg py-2 hover:bg-white/[0.02] transition"
                  >
                    {scores.map((s, i) => {
                      const isWinner = s === maxScore && scores.filter(x => x === maxScore).length === 1;
                      return (
                        <div key={i} className="flex-1 text-center">
                          <span className={`font-semibold font-mono ${getScoreColor(s)} ${isWinner ? 'text-base' : 'text-sm'}`}>
                            {Math.round(s * 10) / 10}
                          </span>
                          {isWinner && <span className="ml-1 text-[10px] text-brand-9/60">●</span>}
                        </div>
                      );
                    })}
                    <div className="w-24 text-center text-xs text-white/50">{dim.label}</div>
                  </motion.div>
                );
              })}
            </div>
          </ScrollReveal3D>
        </>
      )}
    </div>
  );
}
