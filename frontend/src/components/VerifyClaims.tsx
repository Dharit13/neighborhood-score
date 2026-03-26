import { useState } from 'react';
import { motion } from 'framer-motion';
import { Shield } from 'lucide-react';
import { AnimatedGlowingSearchBar } from '@/components/ui/animated-glowing-search-bar';
import TetrisLoading from '@/components/ui/tetris-loader';
import PropertyIntelligencePanel from './PropertyIntelligencePanel';
import type { VerifyClaimsResponse } from '@/types';

export default function VerifyClaims() {
  const [address, setAddress] = useState('');
  const [claimsText, setClaimsText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VerifyClaimsResponse | null>(null);

  const handleVerify = async () => {
    if (!address.trim() || !claimsText.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const resp = await fetch('/api/verify-claims', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: address.trim(), raw_text: claimsText.trim() }),
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

  return (
    <div>
      <div className="sticky top-12 z-20 bg-black/50 backdrop-blur-md pb-4 pt-2">
        <div className="mb-4 text-center">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground">
            Verify Property Claims
          </h1>
          <p className="text-sm text-white mt-1">
            Paste marketing text from a property listing — AI will extract each claim and verify it against real data.
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
              Marketing claims <span className="text-white/60 font-normal">(paste any ad text — AI splits it)</span>
            </label>
            <textarea
              value={claimsText}
              onChange={(e) => setClaimsText(e.target.value)}
              placeholder={"e.g., It is a few minutes from a Purple Line Metro Station and the upcoming Blue Line Metro Station, and is about 15 minutes from ITPL, Outer Ring Road and Sarjapur Road."}
              rows={3}
              className="flex-1 w-full rounded-lg border border-white/[0.10] bg-white/[0.04] px-3 py-2.5 text-sm text-white placeholder:text-white/50 outline-none focus:border-brand-9/30 transition-colors resize-y"
            />
          </div>
        </div>

        <div className="divider" />

        <div className="flex items-center justify-end gap-3">
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
            <TetrisLoading size="sm" speed="fast" loadingText="Analyzing & verifying claims..." />
            <p className="text-xs text-white/60 mt-2">AI is extracting claims, resolving landmarks & checking real commute data</p>
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div className="rounded-xl bg-red-500/10 p-4 text-red-400 text-sm">{error}</div>
        )}

        {/* Results — full intelligence panel */}
        {result && !loading && (
          <div className="space-y-4">
            <div className="rounded-xl bg-white/[0.03] backdrop-blur-sm px-6 py-3 space-y-2">
              <p className="text-sm text-white/60">
                Checking claims for: <span className="text-foreground font-medium">{result.address}</span>
              </p>
              {result.extracted_claims && result.extracted_claims.length > 1 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  <span className="text-xs text-white/40">AI extracted {result.extracted_claims.length} claims:</span>
                  {result.extracted_claims.map((c, i) => (
                    <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-white/[0.06] text-white/70">{c}</span>
                  ))}
                </div>
              )}
            </div>

            <PropertyIntelligencePanel
              address={result.address}
              latitude={result.latitude}
              longitude={result.longitude}
              claimResults={result.results}
              summary={result.summary}
              narrative={result.narrative}
            />
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
              Enter a property address and paste any marketing text — AI will extract each distance/proximity claim
              and verify it against real commute data.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
