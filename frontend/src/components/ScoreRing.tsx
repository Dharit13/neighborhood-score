import { useEffect, useState } from 'react';
import { motion, useMotionValue, useTransform, animate } from 'framer-motion';

interface Props {
  score: number;
  size?: number;
  strokeWidth?: number;
  showLabel?: boolean;
  animated?: boolean;
  className?: string;
  label?: string;
  displayValue?: string;
  colorOverride?: string;
}

function getScoreColor(score: number): string {
  if (score >= 75) return '#c0c7d0';
  if (score >= 68) return '#3b82f6';
  if (score >= 60) return '#2ad587';
  if (score >= 52) return '#fbbf24';
  return '#f87171';
}

export default function ScoreRing({ score, size = 80, strokeWidth = 6, showLabel = true, animated = true, className = '', label, displayValue, colorOverride }: Props) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  const motionScore = useMotionValue(0);
  const dashOffset = useTransform(motionScore, (v) => circumference * (1 - v / 100));
  const displayScore = useTransform(motionScore, (v) => Math.round(v));
  const [displayed, setDisplayed] = useState(0);

  useEffect(() => {
    if (animated) {
      const controls = animate(motionScore, score, { duration: 0.8, ease: 'easeOut' });
      const unsub = displayScore.on('change', (v) => setDisplayed(v));
      return () => { controls.stop(); unsub(); };
    } else {
      motionScore.set(score);
      setDisplayed(Math.round(score));
    }
  }, [score, animated]);

  const color = colorOverride || getScoreColor(score);
  const center = size / 2;

  return (
    <div className={`relative inline-flex items-center justify-center ${className}`} style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={center} cy={center} r={radius}
          fill="none"
          className="score-ring-track"
          strokeWidth={strokeWidth}
          opacity={0.15}
          stroke={color}
        />
        <defs>
          <linearGradient id={`ring-grad-${size}-${score}`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={color} stopOpacity={0.8} />
            <stop offset="100%" stopColor={color} />
          </linearGradient>
        </defs>
        <motion.circle
          cx={center} cy={center} r={radius}
          fill="none"
          stroke={`url(#ring-grad-${size}-${score})`}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          style={{ strokeDashoffset: dashOffset }}
          transform={`rotate(-90 ${center} ${center})`}
        />
      </svg>
      {showLabel && (
        <div className="absolute inset-0 flex items-center justify-center">
          {displayValue ? (
            <span className="font-mono font-bold leading-none" style={{ fontSize: size * 0.28, color }}>
              {displayValue}
            </span>
          ) : displayed === 0 && label ? (
            <span className="font-semibold leading-tight text-center px-1" style={{ fontSize: Math.max(size * 0.14, 8), color }}>
              {label}
            </span>
          ) : (
            <span className="font-mono font-bold leading-none" style={{ fontSize: size * 0.32, color }}>
              {displayed}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
