import NumberFlow from '@number-flow/react';
import { cn } from '@/lib/utils';

interface ShuffleNumberProps {
  value: number;
  className?: string;
  diff?: number;
  showDiff?: boolean;
}

export function ShuffleNumber({
  value,
  className,
  diff,
  showDiff = false,
}: ShuffleNumberProps) {
  return (
    <span className={cn('inline-flex items-center gap-1.5', className)}>
      <NumberFlow
        value={value}
        transformTiming={{ duration: 600, easing: 'ease-out' }}
        spinTiming={{ duration: 600, easing: 'ease-out' }}
      />
      {showDiff && diff != null && diff !== 0 && (
        <span
          className={cn(
            'inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-semibold',
            diff > 0
              ? 'bg-brand-9/15 text-brand-9'
              : 'bg-destructive/15 text-destructive'
          )}
        >
          <svg
            width="10"
            height="10"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ transform: diff < 0 ? 'rotate(180deg)' : undefined }}
          >
            <path d="M12 19V5M5 12l7-7 7 7" />
          </svg>
          {Math.abs(diff).toFixed(1)}%
        </span>
      )}
    </span>
  );
}
