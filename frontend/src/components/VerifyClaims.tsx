import { useState, useEffect, useRef, useCallback } from 'react';
import { Shield, MapPin, Building2, Landmark, FolderKanban } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import { apiUrl, apiFetch } from '@/lib/api';
import ScrollReveal3D from './ScrollReveal3D';
import { AnimatedGlowingSearchBar } from '@/components/ui/animated-glowing-search-bar';
import { Badge } from '@/components/ui/badge';
import TetrisLoading from '@/components/ui/tetris-loader';
import PropertyIntelligencePanel from './PropertyIntelligencePanel';
import type { VerifyClaimsResponse, SearchResults } from '@/types';

const CATEGORY_CONFIG = {
  builders: { icon: Building2, label: 'Builders', color: '#2563eb' },
  projects: { icon: FolderKanban, label: 'Projects', color: '#8b5cf6' },
  areas: { icon: MapPin, label: 'Areas', color: '#16a34a' },
  landmarks: { icon: Landmark, label: 'Landmarks', color: '#b45309' },
} as const;

export default function VerifyClaims() {
  const [address, setAddress] = useState('');
  const [claimsText, setClaimsText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VerifyClaimsResponse | null>(null);

  // Autocomplete state
  const [searchResults, setSearchResults] = useState<SearchResults | null>(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const [searching, setSearching] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);

  const fetchResults = useCallback(async (query: string) => {
    if (query.length < 2) { setSearchResults(null); return; }
    setSearching(true);
    try {
      const resp = await fetch(apiUrl(`/api/search?q=${encodeURIComponent(query)}`));
      if (resp.ok) {
        const data: SearchResults = await resp.json();
        setSearchResults(data);
        setShowDropdown(data.total > 0);
      }
    } catch {
      // best-effort
    } finally {
      setSearching(false);
    }
  }, []);

  // Debounced search on address typing
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (address.trim().length < 2) {
      setSearchResults(null);
      setShowDropdown(false);
      return;
    }
    debounceRef.current = setTimeout(() => fetchResults(address.trim()), 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [address, fetchResults]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectSuggestion = (type: string, item: Record<string, unknown>) => {
    setShowDropdown(false);
    if (type === 'builders') {
      setAddress(String(item.name));
    } else if (type === 'projects') {
      setAddress(String(item.location_area || item.project_name));
    } else {
      setAddress(String(item.name));
    }
  };

  const handleVerify = async () => {
    setShowDropdown(false);
    if (!address.trim() || !claimsText.trim()) return;

    // Validate claims text — must be meaningful
    const trimmed = claimsText.trim();
    if (trimmed.length < 10) {
      setError('Please paste actual property marketing text (e.g., "5 min from metro, near schools"). The text is too short to contain verifiable claims.');
      return;
    }
    // Check if it looks like gibberish (no spaces = single word, or all non-alpha)
    const words = trimmed.split(/\s+/);
    if (words.length < 3 && !/\d/.test(trimmed) && !/(near|close|from|to|min|km|metro|school|hospital)/i.test(trimmed)) {
      setError('That doesn\'t look like property marketing text. Paste claims like "5 min from metro", "near top schools", or a full ad paragraph.');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const resp = await apiFetch('/api/verify-claims', {
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
      <div className="sticky top-12 z-20 pb-4 pt-2" style={{ background: '#f5f0e8' }}>
        {/* Input card */}
        <ScrollReveal3D rotateX={-5}>
        <div className="rounded-xl bg-white/40 border border-[#d0c8b8] p-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 items-stretch">
          <div className="flex flex-col" ref={containerRef}>
            <label className="block text-xs font-medium mb-1" style={{ color: '#1a1a1a' }}>Property address or area</label>
            <div className="flex-1 flex flex-col justify-center relative">
              <AnimatedGlowingSearchBar
                compact
                light
                theme="green"
                value={address}
                onChange={(v) => { setAddress(v); if (v.length >= 2) setShowDropdown(true); }}
                onSubmit={handleVerify}
                placeholder="Start typing — e.g., Sarjapur, Whitefield, Electronic City"
                loading={searching}
              />
              <AnimatePresence>
                {showDropdown && searchResults && searchResults.total > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: -4, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -4, scale: 0.98 }}
                    transition={{ duration: 0.15 }}
                    className="absolute top-full mt-1 left-0 right-0 z-50 rounded-xl bg-[#faf7f0] border border-[#a09888] shadow-lg overflow-hidden max-h-[280px] overflow-y-auto scrollbar-thin"
                  >
                    {(Object.entries(searchResults.results) as [keyof typeof CATEGORY_CONFIG, unknown[]][]).map(([category, items]) => {
                      if (!items || items.length === 0) return null;
                      const config = CATEGORY_CONFIG[category];
                      if (!config) return null;
                      const { icon: Icon, label, color } = config;
                      return (
                        <div key={category}>
                          <div className="px-3 py-1.5 flex items-center gap-2 border-b border-[#d0c8b8]">
                            <Icon size={11} style={{ color }} />
                            <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color }}>{label}</span>
                            <Badge variant="mono-light" className="text-[8px] ml-auto">{items.length}</Badge>
                          </div>
                          {(items as Record<string, unknown>[]).map((item, i) => (
                            <button
                              key={i}
                              onClick={() => handleSelectSuggestion(category, item)}
                              className="w-full text-left px-3 py-2 hover:bg-[#e8e0d0] transition-colors flex items-center gap-2"
                            >
                              <span className="text-sm flex-1 truncate" style={{ color: '#1a1a1a' }}>
                                {String(item.name || item.project_name || '')}
                              </span>
                              {item.trust_tier != null && (
                                <Badge
                                  variant={item.trust_tier === 'trusted' ? 'success-light' : item.trust_tier === 'emerging' ? 'info-light' : item.trust_tier === 'cautious' ? 'warning-light' : 'mono-light'}
                                  className="text-[8px]"
                                >
                                  {String(item.trust_tier)}
                                </Badge>
                              )}
                              {item.category != null && (
                                <span className="text-[10px]" style={{ color: '#a09888' }}>{String(item.category)}</span>
                              )}
                            </button>
                          ))}
                        </div>
                      );
                    })}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
          <div className="flex flex-col">
            <label className="block text-xs font-medium mb-1" style={{ color: '#1a1a1a' }}>
              Marketing claims <span className="font-normal" style={{ color: '#8a8a8a' }}>(paste any ad text — AI splits it)</span>
            </label>
            <textarea
              value={claimsText}
              onChange={(e) => setClaimsText(e.target.value)}
              placeholder={"e.g., It is a few minutes from a Purple Line Metro Station and the upcoming Blue Line Metro Station, and is about 15 minutes from ITPL, Outer Ring Road and Sarjapur Road."}
              rows={3}
              className="flex-1 w-full rounded-lg border border-[#d0c8b8] bg-white/50 px-3 py-2.5 text-sm text-[#1a1a1a] placeholder:text-[#8a8a8a] outline-none focus:border-[#b91c1c]/40 transition-colors resize-y"
            />
          </div>
        </div>

        <div className="h-px" style={{ background: '#d0c8b8' }} />

        <div className="flex items-center justify-end gap-3">
          <button
            onClick={handleVerify}
            disabled={loading || !address.trim() || !claimsText.trim()}
            className="px-4 py-2 rounded-lg text-sm font-semibold disabled:opacity-40 transition-all hover:brightness-110"
            style={{ background: '#1a1a1a', color: '#f5f0e8' }}
          >
            {loading ? 'Verifying...' : 'Verify Claims'}
          </button>
        </div>
      </div>
      </ScrollReveal3D>
      </div>

      <div className="space-y-6 pt-4">
        {/* Loading */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-12">
            <TetrisLoading size="sm" speed="fast" loadingText="Analyzing & verifying claims..." />
            <p className="text-xs mt-2" style={{ color: '#8a8a8a' }}>AI is extracting claims, resolving landmarks & checking real commute data</p>
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div className="rounded-xl bg-red-50 border border-red-200 p-4 text-red-700 text-sm">{error}</div>
        )}

        {/* Results — full intelligence panel */}
        {result && !loading && (
          <ScrollReveal3D rotateX={-8} delay={0.1}>
          <div className="space-y-4">
            <div className="rounded-xl bg-white/40 border border-[#d0c8b8] px-6 py-3 space-y-2">
              <p className="text-sm" style={{ color: '#8a8a8a' }}>
                Checking claims for: <span className="font-medium" style={{ color: '#1a1a1a' }}>{result.address}</span>
              </p>
              {result.extracted_claims && result.extracted_claims.length > 1 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  <span className="text-xs" style={{ color: '#a09888' }}>AI extracted {result.extracted_claims.length} claims:</span>
                  {result.extracted_claims.map((c, i) => (
                    <span key={i} className="text-xs px-2 py-0.5 rounded-full" style={{ background: '#e8e0d0', color: '#4a4a4a' }}>{c}</span>
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
          </ScrollReveal3D>
        )}

        {/* Empty state */}
        {!result && !loading && !error && (
          <div className="text-center py-12">
            <div className="float-animation inline-block mb-3">
              <Shield size={48} style={{ color: 'rgba(26,26,26,0.25)' }} />
            </div>
            <h3 className="text-lg font-semibold mb-2" style={{ color: '#1a1a1a' }}>Don't trust property ads blindly</h3>
            <p className="text-sm max-w-md mx-auto" style={{ color: '#8a8a8a' }}>
              Enter a property address and paste any marketing text — AI will extract each distance/proximity claim
              and verify it against real commute data.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
