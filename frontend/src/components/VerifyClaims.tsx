import { useState } from 'react';
import { motion } from 'framer-motion';
import { Shield } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { AnimatedGlowingSearchBar } from '@/components/ui/animated-glowing-search-bar';
import TetrisLoading from '@/components/ui/tetris-loader';

interface ClaimResult {
  original_claim: string;
  claimed_value: string;
  actual_value: string;
  difference: string;
  verdict: string;
  details: Record<string, unknown>;
}

interface VerifyResponse {
  latitude: number;
  longitude: number;
  address: string;
  results: ClaimResult[];
  summary: string;
}

function verdictBadgeVariant(verdict: string) {
  if (verdict === 'ACCURATE') return 'success' as const;
  if (verdict === 'SLIGHTLY_OPTIMISTIC') return 'warning' as const;
  if (verdict === 'MISLEADING') return 'destructive' as const;
  return 'mono' as const;
}

export default function VerifyClaims() {
  const [address, setAddress] = useState('');
  const [claimsText, setClaimsText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VerifyResponse | null>(null);

  const handleVerify = async () => {
    if (!address.trim() || !claimsText.trim()) return;

    const claims = claimsText
      .split('\n')
      .map(l => l.trim())
      .filter(l => l.length > 0);

    if (claims.length === 0) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const resp = await fetch('/api/verify-claims', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: address.trim(), claims }),
      });
      if (!resp.ok) {
        const err = await resp.json();
        const detail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail) || 'Verification failed';
        throw new Error(detail);
      }
      setResult(await resp.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const EXAMPLES = [
    '5 min from metro',
    '20 min to Electronic City',
    '2 km from international airport',
    '15 min walk to bus stop',
    '30 min to Manyata Tech Park',
  ];

  return (
    <div>
      <div className="sticky top-12 z-20 bg-black/50 backdrop-blur-md pb-4 pt-2">
        <div className="mb-4 text-center">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground">
            Verify Property Claims
          </h1>
          <p className="text-sm text-white mt-1">
            Paste claims from a property listing and see if they hold up against real data.
          </p>
        </div>

        {/* Input card */}
        <div className="rounded-xl bg-white/[0.03] backdrop-blur-sm p-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 items-stretch">
          <div className="flex flex-col">
            <label className="block text-xs font-medium text-foreground mb-1">Property address or area</label>
            <div className="flex-1 flex flex-col justify-center">
              <AnimatedGlowingSearchBar
                compact
                value={address}
                onChange={setAddress}
                onSubmit={handleVerify}
                placeholder="e.g., Sarjapur Road, Bangalore"
              />
            </div>
          </div>
          <div className="flex flex-col">
            <label className="block text-xs font-medium text-foreground mb-1">
              Ad claims <span className="text-white/60 font-normal">(one per line)</span>
            </label>
            <textarea
              value={claimsText}
              onChange={(e) => setClaimsText(e.target.value)}
              placeholder={"5 min from metro\n20 min to Electronic City"}
              rows={2}
              className="flex-1 w-full rounded-lg border border-white/[0.10] bg-white/[0.04] px-3 py-2.5 text-sm text-white placeholder:text-white/50 outline-none focus:border-brand-9/30 transition-colors resize-y"
            />
          </div>
        </div>

        <div className="divider" />

        <div className="flex items-center gap-3">
          <div className="flex flex-wrap gap-2 flex-1">
            <span className="text-xs text-white/60 mr-1 self-center font-medium">Try:</span>
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                onClick={() => setClaimsText(prev => prev ? prev + '\n' + ex : ex)}
                className="text-xs px-3 py-1 glass-button rounded-full text-white/60 hover:text-foreground transition"
              >
                {ex}
              </button>
            ))}
          </div>
          <button
            onClick={handleVerify}
            disabled={loading || !address.trim() || !claimsText.trim()}
            className="px-4 py-2 rounded-lg text-sm font-semibold text-white disabled:opacity-40 transition-all"
            style={{ background: 'linear-gradient(135deg, var(--brand-1), var(--brand-9))' }}
          >
            {loading ? 'Verifying...' : 'Verify Claims'}
          </button>
        </div>
      </div>
      </div>

      <div className="space-y-6 pt-4">
        {/* Loading */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-12">
            <TetrisLoading size="sm" speed="fast" loadingText="Verifying ad claims..." />
            <p className="text-xs text-white/60 mt-2">Checking distances, walking routes & peak traffic</p>
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div className="rounded-xl bg-red-500/10 p-4 text-red-400 text-sm">{error}</div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-4">
            <div className="rounded-xl bg-white/[0.03] backdrop-blur-sm px-6 py-3">
              <p className="text-sm text-white/60">
                Checking claims for: <span className="text-foreground font-medium">{result.address}</span>
              </p>
            </div>

            {/* Summary */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-xl bg-white/[0.03] backdrop-blur-sm p-4"
            >
              <div className="flex items-center gap-3">
                <Shield size={20} className={
                  result.results.some(r => r.verdict === 'MISLEADING') ? 'text-red-400' :
                  result.results.some(r => r.verdict === 'SLIGHTLY_OPTIMISTIC') ? 'text-amber-400' : 'text-brand-9'
                } />
                <span className="font-bold text-foreground">{result.summary.replace(/\d+\s*/, '')}</span>
              </div>
            </motion.div>

            {/* Individual claims */}
            <div className="space-y-3">
              {result.results.map((v, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.08 }}
                  className="rounded-xl bg-white/[0.03] backdrop-blur-sm p-4"
                >
                  <div className="flex items-start gap-3 mb-3">
                    <span className="text-brand-9/15 text-3xl font-bold leading-none select-none">
                      {String(i + 1).padStart(2, '0')}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-foreground font-medium">"{v.original_claim}"</span>
                        <Badge variant={verdictBadgeVariant(v.verdict)}>
                          {v.verdict.replace(/_/g, ' ')}
                        </Badge>
                      </div>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div className="rounded-lg bg-white/[0.03] backdrop-blur-sm p-2.5">
                      <div className="text-[10px] text-white/60 uppercase tracking-wide mb-0.5">Ad claims</div>
                      <div className="text-lg font-bold text-brand-9">{v.claimed_value}</div>
                    </div>
                    <div className="rounded-lg bg-white/[0.03] backdrop-blur-sm p-2.5">
                      <div className="text-[10px] text-white/60 uppercase tracking-wide mb-0.5">Reality</div>
                      <div className={`text-lg font-bold ${
                        v.verdict === 'ACCURATE' ? 'text-brand-9' :
                        v.verdict === 'SLIGHTLY_OPTIMISTIC' ? 'text-amber-400' : 'text-red-400'
                      }`}>{v.actual_value}</div>
                    </div>
                    <div className="rounded-lg bg-white/[0.03] backdrop-blur-sm p-2.5">
                      <div className="text-[10px] text-white/60 uppercase tracking-wide mb-0.5">Difference</div>
                      <div className="text-lg font-bold text-red-400">{v.difference}</div>
                    </div>
                  </div>
                  {v.details.nearest != null && (
                    <p className="text-[11px] text-white/60 mt-2">Nearest: {String(v.details.nearest)}</p>
                  )}
                  {v.details.destination != null && (
                    <p className="text-[11px] text-white/60 mt-2">Destination: {String(v.details.destination)}</p>
                  )}
                  {v.details.note != null && (
                    <p className="text-[11px] text-white/60 mt-1">{String(v.details.note)}</p>
                  )}
                </motion.div>
              ))}
            </div>

            <p className="text-[10px] text-white/60 text-center">
              Data: Google Maps Directions API (walking), Google Distance Matrix API (driving, peak traffic), PostGIS spatial queries
            </p>
          </div>
        )}

        {/* Empty state */}
        {!result && !loading && !error && (
          <div className="text-center py-12">
            <div className="float-animation inline-block mb-3">
              <Shield size={48} className="text-brand-9/30" />
            </div>
            <h3 className="text-lg gradient-text mb-2">Don't trust property ads blindly</h3>
            <p className="text-sm text-white/60 max-w-md mx-auto">
              Enter an address and paste claims like "5 min from metro" or "20 min to Electronic City"
              to see how they compare to reality.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
