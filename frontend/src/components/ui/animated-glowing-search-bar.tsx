import { useRef, type FormEvent } from 'react';
import { Send } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SearchBarTheme {
  primary: string;    // e.g. '#2ad587'
  secondary: string;  // e.g. '#007260'
  dark: string;       // e.g. '#002c7c'
  glow: string;       // e.g. 'rgba(42,213,135,0.4)'
  glowSoft: string;   // e.g. 'rgba(42,213,135,0.2)'
}

const GREEN_THEME: SearchBarTheme = {
  primary: '#2ad587', secondary: '#007260', dark: '#002c7c',
  glow: 'rgba(42,213,135,0.4)', glowSoft: 'rgba(42,213,135,0.2)',
};

const ORANGE_THEME: SearchBarTheme = {
  primary: '#fb923c', secondary: '#ea580c', dark: '#9a3412',
  glow: 'rgba(251,146,60,0.4)', glowSoft: 'rgba(251,146,60,0.2)',
};

const SEARCH_THEMES = { green: GREEN_THEME, orange: ORANGE_THEME } as const;

interface AnimatedGlowingSearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  loading?: boolean;
  compact?: boolean;
  className?: string;
  theme?: 'green' | 'orange';
  light?: boolean;
}

export function AnimatedGlowingSearchBar({
  value,
  onChange,
  onSubmit,
  placeholder = 'Search any neighborhood...',
  loading = false,
  compact = false,
  className,
  theme = 'green',
  light = false,
}: AnimatedGlowingSearchBarProps) {
  const t = SEARCH_THEMES[theme];
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (value.trim()) onSubmit();
  };

  if (compact && light) {
    return (
      <form onSubmit={handleSubmit} className={cn('relative', className)}>
        <div className="relative flex items-center gap-2.5 bg-white rounded-lg px-4 py-2.5 w-full overflow-hidden border border-[#d0c8b8] transition-all focus-within:border-[#b91c1c]/50 focus-within:shadow-[0_0_0_3px_rgba(185,28,28,0.08)]">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" fill="none">
            <circle stroke="#8a8a8a" r="8" cy="11" cx="11" />
            <line stroke="#a09888" y2="16.65" y1="22" x2="16.65" x1="22" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className="flex-1 bg-transparent text-sm text-[#1a1a1a] placeholder:text-[#8a8a8a] outline-none min-w-0"
          />
          {!loading && (
            <button
              type="submit"
              disabled={!value.trim()}
              className="flex cursor-pointer items-center justify-center rounded-lg p-1.5 transition-all duration-300 disabled:opacity-30"
              style={{
                background: 'rgba(26,26,26,0.08)',
                color: '#1a1a1a',
              }}
            >
              <Send size={13} />
            </button>
          )}
          {loading && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 overflow-hidden rounded-b-lg">
              <div
                className="h-full w-[200%]"
                style={{
                  background: 'linear-gradient(to right, transparent, #b91c1c, transparent)',
                  animation: 'search-slide 1.2s linear infinite',
                }}
              />
              <style>{`@keyframes search-slide { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }`}</style>
            </div>
          )}
        </div>
      </form>
    );
  }

  if (compact) {
    return (
      <form onSubmit={handleSubmit} className={cn('relative', className)}>
        <div className="relative flex items-center justify-center group">
          <div className="absolute z-[-1] overflow-hidden h-full w-full rounded-xl blur-[4px]"
               style={{ ['--conic-outer' as string]: `conic-gradient(#000, ${t.dark} 5%, #000 38%, #000 50%, ${t.primary} 60%, #000 87%)` }}>
            <div className="absolute z-[-2] w-[800px] h-[800px] bg-no-repeat top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rotate-[60deg] transition-all duration-2000 group-hover:rotate-[-120deg] group-focus-within:rotate-[420deg] group-focus-within:duration-[4000ms]"
                 style={{ background: `conic-gradient(#000, ${t.dark} 5%, #000 38%, #000 50%, ${t.primary} 60%, #000 87%)` }} />
          </div>
          <div className="absolute z-[-1] overflow-hidden h-full w-full rounded-lg blur-[2px]">
            <div className="absolute z-[-2] w-[600px] h-[600px] bg-no-repeat top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rotate-[83deg] brightness-150 transition-all duration-2000 group-hover:rotate-[-97deg] group-focus-within:rotate-[443deg] group-focus-within:duration-[4000ms]"
                 style={{ background: `conic-gradient(rgba(0,0,0,0) 0%, ${t.secondary}, rgba(0,0,0,0) 10%, rgba(0,0,0,0) 50%, ${t.primary}, rgba(0,0,0,0) 60%)` }} />
          </div>
          <div className="relative flex items-center gap-2.5 bg-[#010201] rounded-lg px-4 py-2.5 w-full overflow-hidden">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" fill="none">
              <circle stroke={t.primary} r="8" cy="11" cx="11" />
              <line stroke={t.secondary} y2="16.65" y1="22" x2="16.65" x1="22" />
            </svg>
            <input
              ref={inputRef}
              type="text"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              placeholder={placeholder}
              className="flex-1 bg-transparent text-sm text-white placeholder:text-white/50 outline-none min-w-0"
            />
            {!loading && (
              <button
                type="submit"
                disabled={!value.trim()}
                className="flex cursor-pointer items-center justify-center rounded-lg p-1.5 transition-all duration-300 disabled:opacity-30 disabled:shadow-none"
                style={{
                  background: `${t.primary}26`,
                  color: t.primary,
                  boxShadow: value.trim() ? `0 0 8px ${t.glowSoft}` : undefined,
                }}
              >
                <Send size={13} />
              </button>
            )}
            {loading && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 overflow-hidden rounded-b-lg">
                <div
                  className="h-full w-[200%]"
                  style={{
                    background: `linear-gradient(to right, transparent, ${t.primary}, transparent)`,
                    animation: 'search-slide 1.2s linear infinite',
                  }}
                />
                <style>{`@keyframes search-slide { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }`}</style>
              </div>
            )}
          </div>
        </div>
      </form>
    );
  }

  return (
    <form onSubmit={handleSubmit} className={cn('relative flex items-center justify-center', className)}>
      <div className="relative flex items-center justify-center group">
        {/* Layer 1: outer conic glow */}
        <div className="absolute z-[-1] overflow-hidden h-full w-full max-h-[70px] rounded-xl blur-[3px]
                        before:absolute before:content-[''] before:z-[-2] before:w-[999px] before:h-[999px] before:bg-no-repeat before:top-1/2 before:left-1/2 before:-translate-x-1/2 before:-translate-y-1/2 before:rotate-60
                        before:bg-[conic-gradient(#000,#002c7c_5%,#000_38%,#000_50%,#2ad587_60%,#000_87%)] before:transition-all before:duration-2000
                        group-hover:before:rotate-[-120deg] group-focus-within:before:rotate-[420deg] group-focus-within:before:duration-[4000ms]" />
        {/* Layer 2-4: mid conic layers */}
        {[0, 1, 2].map((i) => (
          <div key={i} className="absolute z-[-1] overflow-hidden h-full w-full max-h-[65px] rounded-xl blur-[3px]
                          before:absolute before:content-[''] before:z-[-2] before:w-[600px] before:h-[600px] before:bg-no-repeat before:top-1/2 before:left-1/2 before:-translate-x-1/2 before:-translate-y-1/2 before:rotate-[82deg]
                          before:bg-[conic-gradient(rgba(0,0,0,0),#003e7a,rgba(0,0,0,0)_10%,rgba(0,0,0,0)_50%,#007260,rgba(0,0,0,0)_60%)] before:transition-all before:duration-2000
                          group-hover:before:rotate-[-98deg] group-focus-within:before:rotate-[442deg] group-focus-within:before:duration-[4000ms]" />
        ))}
        {/* Layer 5: bright accent line */}
        <div className="absolute z-[-1] overflow-hidden h-full w-full max-h-[63px] rounded-lg blur-[2px]
                        before:absolute before:content-[''] before:z-[-2] before:w-[600px] before:h-[600px] before:bg-no-repeat before:top-1/2 before:left-1/2 before:-translate-x-1/2 before:-translate-y-1/2 before:rotate-[83deg]
                        before:bg-[conic-gradient(rgba(0,0,0,0)_0%,#10b463,rgba(0,0,0,0)_8%,rgba(0,0,0,0)_50%,#2ad587,rgba(0,0,0,0)_58%)] before:brightness-140
                        before:transition-all before:duration-2000 group-hover:before:rotate-[-97deg] group-focus-within:before:rotate-[443deg] group-focus-within:before:duration-[4000ms]" />
        {/* Layer 6: inner border glow */}
        <div className="absolute z-[-1] overflow-hidden h-full w-full max-h-[59px] rounded-xl blur-[0.5px]
                        before:absolute before:content-[''] before:z-[-2] before:w-[600px] before:h-[600px] before:bg-no-repeat before:top-1/2 before:left-1/2 before:-translate-x-1/2 before:-translate-y-1/2 before:rotate-70
                        before:bg-[conic-gradient(#0a0e14,#002c7c_5%,#0a0e14_14%,#0a0e14_50%,#2ad587_60%,#0a0e14_64%)] before:brightness-130
                        before:transition-all before:duration-2000 group-hover:before:rotate-[-110deg] group-focus-within:before:rotate-[430deg] group-focus-within:before:duration-[4000ms]" />

        {/* Input area */}
        <div className="relative group">
          <input
            ref={inputRef}
            placeholder={placeholder}
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="bg-[#010201] border-none w-[301px] sm:w-[420px] h-[56px] rounded-lg text-white px-[59px] text-base sm:text-lg focus:outline-none placeholder-gray-400"
          />
          <div className="pointer-events-none w-[100px] h-[20px] absolute bg-gradient-to-r from-transparent to-black top-[18px] left-[70px] group-focus-within:hidden" />
          <div className="pointer-events-none w-[30px] h-[20px] absolute bg-[#2ad587] top-[10px] left-[5px] blur-2xl opacity-80 transition-all duration-2000 group-hover:opacity-0" />

          {/* Submit button */}
          <button
            type="submit"
            disabled={loading || !value.trim()}
            className="absolute top-2 right-2 flex items-center justify-center z-[2] max-h-10 max-w-[38px] h-full w-full [isolation:isolate] overflow-hidden rounded-lg bg-brand-9/15 text-brand-9 hover:bg-brand-9/25 hover:shadow-[0_0_16px_rgba(42,213,135,0.5)] shadow-[0_0_10px_rgba(42,213,135,0.25)] transition-all duration-300 disabled:opacity-30 disabled:shadow-none cursor-pointer"
          >
            {loading ? (
              <div className="w-5 h-5 rounded-full border-2 border-brand-9/20 border-t-brand-9 animate-spin" />
            ) : (
              <Send size={18} />
            )}
          </button>

          {/* Search icon */}
          <div className="absolute left-5 top-[15px] pointer-events-none">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" viewBox="0 0 24 24" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" height="24" fill="none">
              <circle stroke="url(#search-grad)" r="8" cy="11" cx="11" />
              <line stroke="url(#search-line)" y2="16.65" y1="22" x2="16.65" x1="22" />
              <defs>
                <linearGradient gradientTransform="rotate(50)" id="search-grad">
                  <stop stopColor="#2ad587" offset="0%" />
                  <stop stopColor="#007260" offset="50%" />
                </linearGradient>
                <linearGradient id="search-line">
                  <stop stopColor="#007260" offset="0%" />
                  <stop stopColor="#002c7c" offset="50%" />
                </linearGradient>
              </defs>
            </svg>
          </div>
        </div>
      </div>
    </form>
  );
}

export default AnimatedGlowingSearchBar;
