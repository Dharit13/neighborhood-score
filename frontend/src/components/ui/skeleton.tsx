import { cn } from '@/lib/utils';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
}

export function Skeleton({ className, variant = 'text', width, height }: SkeletonProps) {
  return (
    <div
      data-slot="skeleton"
      className={cn(
        'animate-pulse bg-white/[0.08] rounded',
        variant === 'circular' && 'rounded-full',
        variant === 'text' && 'h-4 rounded-md',
        variant === 'rectangular' && 'rounded-xl',
        className,
      )}
      style={{ width, height }}
    />
  );
}

export function ScoreCardSkeleton() {
  return (
    <div className="rounded-xl bg-white/[0.04] border border-white/[0.10] p-4 space-y-3">
      <div className="flex items-center gap-3">
        <Skeleton variant="circular" width={48} height={48} />
        <div className="flex-1 space-y-2">
          <Skeleton width="60%" />
          <Skeleton width="40%" className="h-3" />
        </div>
      </div>
      <Skeleton variant="rectangular" height={8} className="w-full" />
      <div className="flex gap-2">
        <Skeleton width="30%" className="h-3" />
        <Skeleton width="20%" className="h-3" />
      </div>
    </div>
  );
}

export function BuilderCardSkeleton() {
  return (
    <div className="rounded-xl bg-white/[0.04] border border-white/[0.10] p-3 flex items-center gap-3">
      <Skeleton variant="circular" width={48} height={48} />
      <div className="flex-1 space-y-2">
        <Skeleton width="50%" />
        <div className="flex gap-2">
          <Skeleton width={60} className="h-5 rounded-full" />
          <Skeleton width={40} className="h-5 rounded-full" />
        </div>
      </div>
      <Skeleton width={14} height={14} variant="circular" />
    </div>
  );
}
