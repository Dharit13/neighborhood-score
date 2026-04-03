import { motion } from 'framer-motion';
import { Compass, MapPin, Shield, Database, Share2, Download, LogOut, Search } from 'lucide-react';
import { cn } from '@/lib/utils';

type AppMode = 'score' | 'verify' | 'compare' | 'sources';

const SECTION_IDS: Record<AppMode, string> = {
  score: 'explore-section',
  verify: 'verify-section',
  compare: 'compare-section',
  sources: 'sources-section',
};

const tabs = [
  { id: 'score' as const, label: 'Explore', icon: Compass },
  { id: 'compare' as const, label: 'Compare', icon: MapPin },
  { id: 'verify' as const, label: 'Verify', icon: Shield },
  { id: 'sources' as const, label: 'Sources', icon: Database },
];

interface FloatingNavProps {
  mode: AppMode;
  onChange: (m: AppMode) => void;
  onNavigate?: () => void;
  onShare?: () => void;
  onDownload?: () => void;
  onLogout: () => void;
  onSearchFocus?: () => void;
  hasData: boolean;
  linkCopied?: boolean;
  downloadingPdf?: boolean;
}

export default function FloatingNav({
  mode,
  onChange,
  onNavigate,
  onShare,
  onDownload,
  onLogout,
  onSearchFocus,
  hasData,
  linkCopied,
  downloadingPdf,
}: FloatingNavProps) {
  const handleTabClick = (id: AppMode) => {
    onNavigate?.();
    onChange(id);
    document.getElementById(SECTION_IDS[id])?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <motion.nav
      className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2"
      initial={{ y: 100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ type: 'spring', damping: 25, stiffness: 200, delay: 0.3 }}
    >
      <div className="flex items-center gap-1 rounded-full bg-[#0a0a0a]/90 backdrop-blur-xl border border-white/10 px-2 py-2 shadow-2xl">
        {/* Search trigger */}
        {onSearchFocus && (
          <button
            onClick={onSearchFocus}
            className="flex items-center justify-center w-9 h-9 rounded-full text-white/40 hover:text-white/70 transition-colors"
            title="Search"
          >
            <Search size={15} />
          </button>
        )}

        {/* Divider */}
        <div className="w-px h-5 bg-white/10 mx-1" />

        {/* Nav tabs */}
        {tabs.map((tab) => {
          const isActive = mode === tab.id;
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => handleTabClick(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-full text-[11px] font-mono uppercase tracking-wider transition-all duration-300',
                isActive
                  ? 'bg-white text-black'
                  : 'text-white/50 hover:text-white'
              )}
            >
              <Icon size={14} className={isActive ? 'text-black' : undefined} />
              <span className={cn(
                'transition-all duration-300 overflow-hidden whitespace-nowrap',
                isActive ? 'max-w-[80px] opacity-100' : 'max-w-0 opacity-0'
              )}>
                {tab.label}
              </span>
            </button>
          );
        })}

        {/* Divider */}
        <div className="w-px h-5 bg-white/10 mx-1" />

        {/* Action buttons */}
        {hasData && (
          <>
            {onShare && (
              <button
                onClick={onShare}
                className="flex items-center justify-center w-9 h-9 rounded-full text-white/40 hover:text-white/70 transition-colors"
                title="Copy URL"
              >
                {linkCopied ? (
                  <span className="text-[9px] font-mono text-magnetto-amber">OK</span>
                ) : (
                  <Share2 size={14} />
                )}
              </button>
            )}
            {onDownload && (
              <button
                onClick={onDownload}
                disabled={downloadingPdf}
                className="flex items-center justify-center w-9 h-9 rounded-full text-white/40 hover:text-white/70 transition-colors disabled:opacity-30"
                title="Download Report"
              >
                <Download size={14} />
              </button>
            )}
          </>
        )}

        <button
          onClick={onLogout}
          className="flex items-center justify-center w-9 h-9 rounded-full bg-magnetto-orange text-white hover:bg-magnetto-amber transition-colors"
          title="Log Out"
        >
          <LogOut size={14} />
        </button>
      </div>
    </motion.nav>
  );
}
