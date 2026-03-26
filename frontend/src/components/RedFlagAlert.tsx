import { AlertTriangle, AlertCircle, Info } from 'lucide-react';
import type { RiskFlag } from '@/types';

const SEVERITY_CONFIG = {
  critical: {
    border: 'border-l-4 border-red-500',
    bg: 'bg-red-500/5',
    Icon: AlertTriangle,
    iconColor: 'text-red-400',
  },
  warning: {
    border: 'border-l-4 border-amber-500',
    bg: 'bg-amber-500/5',
    Icon: AlertCircle,
    iconColor: 'text-amber-400',
  },
  info: {
    border: 'border-l-4 border-blue-500',
    bg: 'bg-blue-500/5',
    Icon: Info,
    iconColor: 'text-blue-400',
  },
} as const;

interface Props {
  flag: RiskFlag;
}

export default function RedFlagAlert({ flag }: Props) {
  const config = SEVERITY_CONFIG[flag.severity] ?? SEVERITY_CONFIG.info;
  const { Icon } = config;

  return (
    <div className={`rounded-lg ${config.border} ${config.bg} px-4 py-3 flex items-start gap-3`}>
      <Icon size={16} className={`${config.iconColor} mt-0.5 flex-shrink-0`} />
      <div className="min-w-0">
        <p className="text-sm font-semibold text-white">{flag.title}</p>
        <p className="text-xs text-white/60 mt-0.5 leading-relaxed">{flag.detail}</p>
      </div>
    </div>
  );
}
