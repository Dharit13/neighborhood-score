import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Building2, MapPin, Landmark, FolderKanban } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { AnimatedGlowingSearchBar } from '@/components/ui/animated-glowing-search-bar';
import type { SearchResults } from '@/types';

interface Props {
  onSearch: (q: { address?: string; builder_name?: string }) => void;
  loading: boolean;
  address: string;
  className?: string;
}

function readableAddress(addr: string): string {
  return addr.split(',').map(p => p.trim()).filter(p => !/^[A-Z0-9+]{4,}\+/.test(p) && !/^\d+[A-Z]?$/.test(p)).join(', ') || addr;
}

const CATEGORY_CONFIG = {
  builders: { icon: Building2, label: 'Builders', color: '#2563eb' },
  projects: { icon: FolderKanban, label: 'Projects', color: '#8b5cf6' },
  areas: { icon: MapPin, label: 'Areas', color: '#16a34a' },
  landmarks: { icon: Landmark, label: 'Landmarks', color: '#f59e0b' },
} as const;

export default function SearchAutocomplete({ onSearch, loading, address, className }: Props) {
  const [value, setValue] = useState('');
  const [results, setResults] = useState<SearchResults | null>(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const [searching, setSearching] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);

  const fetchResults = useCallback(async (query: string) => {
    if (query.length < 2) { setResults(null); return; }
    setSearching(true);
    try {
      const resp = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
      if (resp.ok) {
        const data: SearchResults = await resp.json();
        setResults(data);
        setShowDropdown(data.total > 0);
      }
    } catch {
      // Silently fail - search is best-effort
    } finally {
      setSearching(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (value.trim().length < 2) {
      setResults(null);
      setShowDropdown(false);
      return;
    }
    debounceRef.current = setTimeout(() => fetchResults(value.trim()), 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [value, fetchResults]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (type: string, item: Record<string, unknown>) => {
    setShowDropdown(false);
    setValue('');
    if (type === 'builders') {
      onSearch({ builder_name: String(item.name) });
    } else if (type === 'areas') {
      onSearch({ address: String(item.name) });
    } else if (type === 'landmarks') {
      onSearch({ address: String(item.name) });
    } else if (type === 'projects') {
      onSearch({ address: String(item.location_area || item.project_name) });
    }
  };

  const handleSubmit = () => {
    if (value.trim()) {
      setShowDropdown(false);
      onSearch({ address: value.trim() });
      setValue('');
    }
  };

  return (
    <div ref={containerRef} className={`relative ${className || ''}`}>
      <AnimatedGlowingSearchBar
        compact
        value={value}
        onChange={(v) => { setValue(v); if (v.length >= 2) setShowDropdown(true); }}
        onSubmit={handleSubmit}
        placeholder={address ? readableAddress(address).split(',')[0] : 'Search a neighborhood...'}
        loading={loading || searching}
      />

      <AnimatePresence>
        {showDropdown && results && results.total > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full mt-1 left-0 right-0 z-50 rounded-xl bg-black/95 backdrop-blur-xl border border-white/[0.10] shadow-2xl overflow-hidden max-h-[320px] overflow-y-auto scrollbar-thin"
          >
            {(Object.entries(results.results) as [keyof typeof CATEGORY_CONFIG, unknown[]][]).map(([category, items]) => {
              if (!items || items.length === 0) return null;
              const config = CATEGORY_CONFIG[category];
              if (!config) return null;
              const { icon: Icon, label, color } = config;

              return (
                <div key={category}>
                  <div className="px-3 py-1.5 flex items-center gap-2 border-b border-white/[0.04]">
                    <Icon size={11} style={{ color }} />
                    <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color }}>{label}</span>
                    <Badge variant="mono" className="text-[8px] ml-auto">{items.length}</Badge>
                  </div>
                  {(items as Record<string, unknown>[]).map((item, i) => (
                    <button
                      key={i}
                      onClick={() => handleSelect(category, item)}
                      className="w-full text-left px-3 py-2 hover:bg-white/[0.06] transition-colors flex items-center gap-2"
                    >
                      <span className="text-sm text-white/90 flex-1 truncate">
                        {String(item.name || item.project_name || '')}
                      </span>
                      {item.trust_tier != null && (
                        <Badge
                          variant={item.trust_tier === 'trusted' ? 'success' : item.trust_tier === 'emerging' ? 'info' : item.trust_tier === 'cautious' ? 'warning' : 'mono'}
                          className="text-[8px]"
                        >
                          {String(item.trust_tier)}
                        </Badge>
                      )}
                      {item.status != null && (
                        <Badge variant="mono" className="text-[8px]">{String(item.status)}</Badge>
                      )}
                      {item.category != null && (
                        <span className="text-[10px] text-white/30">{String(item.category)}</span>
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
  );
}
