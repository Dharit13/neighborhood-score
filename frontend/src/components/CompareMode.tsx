import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import ScrollReveal3D from './ScrollReveal3D';
import { Sparkles, ChevronLeft, RotateCcw, Wallet, MapPin, Heart, User, Trophy, TrendingUp, TrendingDown, BarChart3 } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip, Legend,
} from 'recharts';
import { ShuffleNumber } from '@/components/ui/shuffle-number';
import TetrisLoading from '@/components/ui/tetris-loader';
import type { NeighborhoodScoreResponse, RecommendItem } from '../types';

const RAW_COLORS = ['#818cf8', '#34d399', '#fbbf24'];
const RAW_COLORS_DIM = ['rgba(129,140,248,0.3)', 'rgba(52,211,153,0.3)', 'rgba(251,191,36,0.3)'];

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
  if (score >= 60) return 'text-indigo-400';
  if (score >= 52) return 'text-amber-400';
  return 'text-red-400';
}

function matchColor(score: number) {
  if (score >= 90) return 'from-indigo-500 to-blue-400';
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
      const resp = await apiFetch('/api/ai-recommend', {
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

  const [activeView, setActiveView] = useState<'radar' | 'bars'>('bars');
  const [hoveredDim, setHoveredDim] = useState<string | null>(null);

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

  // Bar chart data for dimension comparison
  const barData = useMemo(() => {
    if (!loaded || loaded.length < 3) return [];
    return DIMENSIONS.map((dim) => {
      const scores = loaded.map(r => (r[dim.key] as { score: number } | undefined)?.score ?? 0);
      const maxScore = Math.max(...scores);
      const winnerIdx = scores.filter(x => x === maxScore).length === 1 ? scores.indexOf(maxScore) : -1;
      return {
        dimension: dim.label,
        dimKey: dim.key,
        score0: scores[0],
        score1: scores[1],
        score2: scores[2],
        winner: winnerIdx,
        maxScore,
        diff: Math.round((maxScore - Math.min(...scores)) * 10) / 10,
      };
    });
  }, [loaded]);

  // Win counts per neighborhood
  const winCounts = useMemo(() => {
    const counts = [0, 0, 0];
    barData.forEach(d => { if (d.winner >= 0) counts[d.winner]++; });
    return counts;
  }, [barData]);

  // Best & worst dimensions per neighborhood
  const neighborhoodInsights = useMemo(() => {
    if (!loaded || loaded.length < 3) return [];
    return loaded.map((r) => {
      const dimScores = DIMENSIONS.map(dim => ({
        label: dim.label,
        score: (r[dim.key] as { score: number } | undefined)?.score ?? 0,
      })).sort((a, b) => b.score - a.score);
      return {
        best: dimScores.slice(0, 3),
        worst: dimScores.slice(-3).reverse(),
      };
    });
  }, [loaded]);

  return (
    <div className="space-y-6">
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
                      ? 'bg-indigo-500 text-white scale-110'
                      : i < step
                        ? 'bg-indigo-500/30 text-indigo-400 cursor-pointer hover:bg-indigo-500/50'
                        : 'bg-white/[0.06] text-white/30'
                  }`}
                >
                  <Icon size={14} />
                </button>
                {i < STEPS.length - 1 && (
                  <div className={`w-8 h-0.5 rounded-full ${i < step ? 'bg-indigo-500/40' : 'bg-white/[0.06]'}`} />
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
                      ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/40'
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
                      ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/40 scale-105'
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
                      ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/40 scale-105'
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
                className="w-full max-w-sm rounded-xl border border-white/[0.10] bg-white/[0.04] px-4 py-2.5 text-sm text-white placeholder:text-white/40 outline-none focus:border-indigo-500/40 transition-colors"
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
                        ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/40 scale-[1.03]'
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
                      ? 'bg-indigo-500/20 border border-indigo-500/40 scale-[1.02]'
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
              background: canNext() ? 'linear-gradient(135deg, #4338ca, #818cf8)' : undefined,
              boxShadow: canNext() ? '0 0 20px rgba(129,140,248,0.25)' : undefined,
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
          <TetrisLoading size="sm" speed="fast" variant="compare" loadingText="AI is finding your ideal neighborhoods..." />
          <p className="text-xs text-white/60 mt-2">Analyzing 74 neighborhoods across 17 dimensions</p>
        </div>
      )}

      {/* Error */}
      {step === 4 && error && !loading && (
        <div className="text-center space-y-3">
          <div className="rounded-xl bg-red-500/10 p-4 text-red-400 text-sm max-w-lg mx-auto">{error}</div>
          <button onClick={handleStartOver} className="text-sm text-indigo-400 hover:underline flex items-center gap-1 mx-auto">
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

          {/* AI Recommendation Cards with scoreboard */}
          <div className="max-w-5xl mx-auto space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {results.map((rec, i) => (
                <ScrollReveal3D key={i} rotateX={-6} delay={i * 0.08}>
                  <div className="rounded-xl bg-white/[0.03] backdrop-blur-sm border border-white/[0.06] p-4 space-y-3 h-full relative overflow-hidden">
                    {/* Color accent bar */}
                    <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: RAW_COLORS[i] }} />

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
                          <span style={{ color: RAW_COLORS[i] }} className="mt-0.5">•</span>
                          <span>{h}</span>
                        </div>
                      ))}
                    </div>

                    {/* Score + wins footer */}
                    <div className="pt-2 border-t border-white/[0.06] flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Trophy size={12} className="text-white/30" />
                        <span className="text-xs text-white/50">
                          Wins <span className="font-bold font-mono" style={{ color: RAW_COLORS[i] }}>{winCounts[i]}</span>
                          <span className="text-white/30"> / {DIMENSIONS.length}</span>
                        </span>
                      </div>
                      <span className={`text-lg font-bold font-mono ${getScoreColor(rec.scores?.composite_score || 0)}`}>
                        <ShuffleNumber value={rec.scores?.composite_score || 0} />
                      </span>
                    </div>
                  </div>
                </ScrollReveal3D>
              ))}
            </div>
          </div>

          {/* View toggle */}
          <div className="flex justify-center gap-1 max-w-5xl mx-auto">
            <button
              onClick={() => setActiveView('bars')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                activeView === 'bars' ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' : 'text-white/40 hover:text-white/60 border border-transparent'
              }`}
            >
              <BarChart3 size={12} /> Bar Comparison
            </button>
            <button
              onClick={() => setActiveView('radar')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                activeView === 'radar' ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' : 'text-white/40 hover:text-white/60 border border-transparent'
              }`}
            >
              <svg width={12} height={12} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}><polygon points="12,2 22,8.5 22,15.5 12,22 2,15.5 2,8.5" /></svg>
              Radar Overlay
            </button>
          </div>

          <AnimatePresence mode="wait">
            {activeView === 'bars' ? (
              <motion.div
                key="bars"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
              >
                {/* Interactive dimension rows */}
                <ScrollReveal3D delay={0.05} rotateX={-6}>
                  <div className="max-w-5xl mx-auto space-y-1.5 mt-4">
                    {barData.map((dim, rowIdx) => {
                      const isHovered = hoveredDim === dim.dimKey;
                      return (
                        <motion.div
                          key={dim.dimKey}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: rowIdx * 0.03 }}
                          onMouseEnter={() => setHoveredDim(dim.dimKey)}
                          onMouseLeave={() => setHoveredDim(null)}
                          className={`rounded-lg px-4 py-2.5 transition-all cursor-default ${
                            isHovered ? 'bg-white/[0.05]' : 'bg-white/[0.015] hover:bg-white/[0.03]'
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-24 flex-shrink-0">
                              <span className="text-xs font-medium text-white/60">{dim.dimension}</span>
                            </div>
                            <div className="flex-1 flex items-center gap-2">
                              {[dim.score0, dim.score1, dim.score2].map((score, i) => {
                                const isWinner = dim.winner === i;
                                const pct = score;
                                return (
                                  <div key={i} className="flex-1 flex items-center gap-2">
                                    <div className="flex-1 h-5 rounded-full overflow-hidden relative" style={{ background: 'rgba(255,255,255,0.04)' }}>
                                      <motion.div
                                        className="h-full rounded-full relative"
                                        initial={{ width: 0 }}
                                        animate={{ width: `${pct}%` }}
                                        transition={{ duration: 0.8, delay: rowIdx * 0.03 + i * 0.1, ease: 'easeOut' }}
                                        style={{
                                          background: isWinner
                                            ? `linear-gradient(90deg, ${RAW_COLORS_DIM[i]}, ${RAW_COLORS[i]})`
                                            : RAW_COLORS_DIM[i],
                                        }}
                                      />
                                      <span className={`absolute right-2 top-1/2 -translate-y-1/2 text-[10px] font-mono font-bold ${
                                        isWinner ? 'text-white' : 'text-white/50'
                                      }`}>
                                        {Math.round(score * 10) / 10}
                                      </span>
                                    </div>
                                    {isWinner && (
                                      <motion.div
                                        initial={{ scale: 0 }}
                                        animate={{ scale: 1 }}
                                        transition={{ delay: rowIdx * 0.03 + 0.5 }}
                                      >
                                        <Trophy size={10} style={{ color: RAW_COLORS[i] }} />
                                      </motion.div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        </motion.div>
                      );
                    })}
                  </div>
                </ScrollReveal3D>
              </motion.div>
            ) : (
              <motion.div
                key="radar"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
              >
                {/* Radar Chart */}
                <ScrollReveal3D rotateX={-10} translateZ={10}>
                  <div className="rounded-xl bg-white/[0.03] backdrop-blur-sm p-6 max-w-5xl mx-auto">
                    <h3 className="text-sm font-semibold section-heading-compare mb-4 text-center uppercase tracking-widest">Score Overlay</h3>
                    <ResponsiveContainer width="100%" height={450}>
                      <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
                        <PolarGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />
                        <PolarAngleAxis
                          dataKey="metric"
                          tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10 }}
                        />
                        <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: 'rgba(255,255,255,0.2)', fontSize: 9 }} axisLine={false} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'rgba(0,0,0,0.95)',
                            border: '1px solid rgba(129,140,248,0.2)',
                            borderRadius: '10px',
                            color: 'white',
                            fontSize: '12px',
                            backdropFilter: 'blur(12px)',
                            padding: '10px 14px',
                          }}
                        />
                        <Legend
                          wrapperStyle={{ fontSize: '11px', paddingTop: '12px' }}
                        />
                        {loaded.map((r, i) => (
                          <Radar
                            key={i}
                            name={readableName(r.address)}
                            dataKey={`score${i}`}
                            stroke={RAW_COLORS[i]}
                            fill={RAW_COLORS[i]}
                            fillOpacity={0.08}
                            strokeWidth={2}
                            dot={{ r: 3, fill: RAW_COLORS[i], strokeWidth: 0 }}
                            activeDot={{ r: 5, fill: RAW_COLORS[i], stroke: 'white', strokeWidth: 1 }}
                          />
                        ))}
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                </ScrollReveal3D>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Strengths & Weaknesses per neighborhood */}
          <ScrollReveal3D delay={0.1} rotateX={-6}>
            <div className="max-w-5xl mx-auto">
              <h3 className="text-sm font-semibold section-heading-compare mb-4 text-center uppercase tracking-widest">Strengths & Weaknesses</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {loaded.map((r, i) => (
                  <div key={i} className="rounded-xl bg-white/[0.03] backdrop-blur-sm border border-white/[0.06] p-4 space-y-3">
                    <h4 className="text-sm font-semibold" style={{ color: RAW_COLORS[i] }}>
                      {readableName(r.address)}
                    </h4>

                    {/* Best */}
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-1.5 text-[10px] text-white/40 uppercase tracking-wider font-medium">
                        <TrendingUp size={10} className="text-emerald-400" /> Top strengths
                      </div>
                      {neighborhoodInsights[i]?.best.map((d, j) => (
                        <div key={j} className="flex items-center justify-between">
                          <span className="text-xs text-white/70">{d.label}</span>
                          <div className="flex items-center gap-1.5">
                            <div className="w-16 h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
                              <div className="h-full rounded-full bg-emerald-500/60" style={{ width: `${d.score}%` }} />
                            </div>
                            <span className="text-xs font-mono font-semibold text-emerald-400 w-8 text-right">{Math.round(d.score)}</span>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Worst */}
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-1.5 text-[10px] text-white/40 uppercase tracking-wider font-medium">
                        <TrendingDown size={10} className="text-amber-400" /> Watch out for
                      </div>
                      {neighborhoodInsights[i]?.worst.map((d, j) => (
                        <div key={j} className="flex items-center justify-between">
                          <span className="text-xs text-white/70">{d.label}</span>
                          <div className="flex items-center gap-1.5">
                            <div className="w-16 h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
                              <div className="h-full rounded-full bg-amber-500/60" style={{ width: `${d.score}%` }} />
                            </div>
                            <span className="text-xs font-mono font-semibold text-amber-400 w-8 text-right">{Math.round(d.score)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </ScrollReveal3D>
        </>
      )}
    </div>
  );
}
