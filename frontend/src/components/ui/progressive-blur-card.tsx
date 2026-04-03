import { cn } from '@/lib/utils';

interface ProgressiveBlurProps {
  className?: string;
  blurIntensity?: number;
}

function ProgressiveBlur({
  className = '',
  blurIntensity = 10
}: ProgressiveBlurProps) {
  return (
    <div
      className={cn(className)}
      style={{
        backdropFilter: `blur(${blurIntensity}px)`,
        WebkitBackdropFilter: `blur(${blurIntensity}px)`,
        mask: 'linear-gradient(to top, black 0%, black 60%, rgba(0,0,0,0.95) 65%, rgba(0,0,0,0.9) 70%, rgba(0,0,0,0.8) 75%, rgba(0,0,0,0.6) 80%, rgba(0,0,0,0.4) 85%, rgba(0,0,0,0.2) 90%, rgba(0,0,0,0.1) 95%, transparent 100%)',
        WebkitMask: 'linear-gradient(to top, black 0%, black 60%, rgba(0,0,0,0.95) 65%, rgba(0,0,0,0.9) 70%, rgba(0,0,0,0.8) 75%, rgba(0,0,0,0.6) 80%, rgba(0,0,0,0.4) 85%, rgba(0,0,0,0.2) 90%, rgba(0,0,0,0.1) 95%, transparent 100%)',
      }}
    />
  );
}

interface ProgressiveBlurCardProps {
  imageSrc: string;
  imageAlt: string;
  title: string;
  subtitle: string;
  selected?: boolean;
  enabled?: boolean;
  className?: string;
}

export function ProgressiveBlurCard({
  imageSrc,
  imageAlt,
  title,
  subtitle,
  selected = false,
  enabled = true,
  className,
}: ProgressiveBlurCardProps) {
  return (
    <div
      className={cn(
        'relative aspect-square w-[380px] rounded-3xl shadow-[0_4px_24px_rgba(0,0,0,0.2)] border transition-all duration-500 hover:shadow-[0_8px_40px_rgba(0,0,0,0.3)] hover:scale-[1.02] overflow-hidden',
        selected ? 'border-[#1a1a1a]' : 'border-[#d0c8b8]',
        className,
      )}
    >
      <img
        src={imageSrc}
        alt={imageAlt}
        className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 hover:scale-105"
        draggable={false}
      />

      {/* Coming soon overlay */}
      {!enabled && (
        <div className="absolute inset-0 z-10 bg-[#f5f0e8]/60 backdrop-blur-[2px] flex items-center justify-center">
          <span className="text-[#8a8a8a] text-xs font-medium tracking-wider uppercase">Coming Soon</span>
        </div>
      )}

      <ProgressiveBlur
        className="pointer-events-none absolute bottom-0 left-0 h-[40%] w-full rounded-b-[20px]"
        blurIntensity={8}
      />
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/50 to-transparent transition-all duration-300 hover:from-black/60">
        <div className="px-6 py-6 group">
          <div className="flex flex-col transform transition-all duration-300 group-hover:translate-y-[-2px]">
            <h2 className="text-lg font-semibold text-white transition-all duration-300 group-hover:text-xl">{title}</h2>
            <p className="text-sm text-white/90 transition-all duration-300 group-hover:text-white">{subtitle}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
