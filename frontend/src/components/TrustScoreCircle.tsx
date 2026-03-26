import { useEffect, useState } from 'react';
import { motion, useMotionValue, useTransform, animate } from 'framer-motion';
import { getTrustTier } from '@/utils/trustTiers';

interface Props {
  score: number;
  size?: number;
  strokeWidth?: number;
  animated?: boolean;
  className?: string;
}

export default function TrustScoreCircle({ score, size = 80, strokeWidth = 6, animated = true, className = '' }: Props) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const tier = getTrustTier(score);

  const motionScore = useMotionValue(animated ? 0 : score);
  const dashOffset = useTransform(motionScore, (v) => circumference * (1 - v / 100));
  const displayScore = useTransform(motionScore, (v) => Math.round(v));
  const [displayed, setDisplayed] = useState(() => animated ? 0 : Math.round(score));

  useEffect(() => {
    if (!animated) {
      motionScore.set(score);
      return;
    }
    const controls = animate(motionScore, score, { duration: 0.8, ease: 'easeOut' });
    const unsub = displayScore.on('change', (v) => setDisplayed(v));
    return () => { controls.stop(); unsub(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [score, animated]);

  const resolvedDisplayed = animated ? displayed : Math.round(score);

  const center = size / 2;
  const gradId = `trust-ring-${size}-${score}`;

  return (
    <div className={`relative inline-flex flex-col items-center justify-center ${className}`}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          <circle
            cx={center} cy={center} r={radius}
            fill="none" strokeWidth={strokeWidth}
            stroke={tier.color} opacity={0.15}
          />
          <defs>
            <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={tier.color} stopOpacity={0.8} />
              <stop offset="100%" stopColor={tier.color} />
            </linearGradient>
          </defs>
          <motion.circle
            cx={center} cy={center} r={radius}
            fill="none" stroke={`url(#${gradId})`}
            strokeWidth={strokeWidth} strokeLinecap="round"
            strokeDasharray={circumference}
            style={{ strokeDashoffset: dashOffset }}
            transform={`rotate(-90 ${center} ${center})`}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="font-mono font-bold leading-none" style={{ fontSize: size * 0.3, color: tier.color }}>
            {resolvedDisplayed}
          </span>
        </div>
      </div>
      {size >= 56 && (
        <span className="text-[10px] font-semibold mt-0.5 uppercase tracking-wider" style={{ color: tier.color }}>
          {tier.label}
        </span>
      )}
    </div>
  );
}
