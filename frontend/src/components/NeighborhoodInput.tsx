import { useState, useEffect, useRef, useCallback } from 'react';
import { MapPin } from 'lucide-react';
import { cn } from '@/lib/utils';

let _cachedNeighborhoods: string[] | null = null;
let _fetchPromise: Promise<string[]> | null = null;

function fetchNeighborhoods(): Promise<string[]> {
  if (_cachedNeighborhoods) return Promise.resolve(_cachedNeighborhoods);
  if (_fetchPromise) return _fetchPromise;
  _fetchPromise = fetch('/api/neighborhoods')
    .then(r => r.json())
    .then((data: unknown) => {
      const arr = Array.isArray(data) ? data.filter((x): x is string => typeof x === 'string') : [];
      _cachedNeighborhoods = arr;
      return arr;
    })
    .catch(() => {
      _fetchPromise = null;
      return [];
    });
  return _fetchPromise;
}

interface Props {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export default function NeighborhoodInput({ value, onChange, placeholder = 'Enter area name...', className }: Props) {
  const [neighborhoods, setNeighborhoods] = useState<string[]>(_cachedNeighborhoods ?? []);
  const [open, setOpen] = useState(false);
  const [highlightIdx, setHighlightIdx] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchNeighborhoods().then(setNeighborhoods);
  }, []);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filtered = value.trim()
    ? neighborhoods.filter(n => n.toLowerCase().includes(value.toLowerCase().trim())).slice(0, 6)
    : neighborhoods.slice(0, 6);

  const selectItem = useCallback((name: string) => {
    onChange(name);
    setOpen(false);
    setHighlightIdx(-1);
    inputRef.current?.blur();
  }, [onChange]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!open || filtered.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightIdx(prev => (prev + 1) % filtered.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightIdx(prev => (prev <= 0 ? filtered.length - 1 : prev - 1));
    } else if (e.key === 'Enter' && highlightIdx >= 0) {
      e.preventDefault();
      selectItem(filtered[highlightIdx]);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  }, [open, filtered, highlightIdx, selectItem]);

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      <div className="relative flex items-center gap-2.5 rounded-lg border border-white/[0.10] bg-white/[0.04] px-3 py-2.5 transition-colors focus-within:border-brand-9/30">
        <MapPin size={15} className="text-brand-9 flex-shrink-0" />
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => { onChange(e.target.value); setOpen(true); setHighlightIdx(-1); }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="flex-1 bg-transparent text-sm text-white placeholder:text-white/50 outline-none min-w-0"
        />
      </div>

      {open && filtered.length > 0 && (
        <div className="absolute z-50 top-full left-0 right-0 mt-1 rounded-lg border border-white/[0.10] bg-[#0a0f14] backdrop-blur-xl shadow-xl overflow-hidden">
          {filtered.map((name, i) => (
            <button
              key={name}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => selectItem(name)}
              onMouseEnter={() => setHighlightIdx(i)}
              className={cn(
                'w-full text-left px-3 py-2 text-sm transition-colors flex items-center gap-2',
                i === highlightIdx ? 'bg-brand-9/15 text-white' : 'text-white/70 hover:bg-white/[0.06]'
              )}
            >
              <MapPin size={12} className="text-brand-9/50 flex-shrink-0" />
              {name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
