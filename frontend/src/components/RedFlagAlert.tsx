import { AlertTriangle, AlertCircle, Info } from 'lucide-react';
import type { RiskFlag } from '@/types';

const SEVERITY_CONFIG = {
  critical: {
    border: 'border-l-4 border-red-600',
    bg: 'bg-red-50',
    Icon: AlertTriangle,
    iconColor: 'text-red-600',
  },
  warning: {
    border: 'border-l-4 border-amber-600',
    bg: 'bg-amber-50',
    Icon: AlertCircle,
    iconColor: 'text-amber-600',
  },
  info: {
    border: 'border-l-4 border-blue-600',
    bg: 'bg-blue-50',
    Icon: Info,
    iconColor: 'text-blue-600',
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
        <p className="text-sm font-semibold" style={{ color: '#1a1a1a' }}>{flag.title}</p>
        <p className="text-xs mt-0.5 leading-relaxed" style={{ color: '#4a4a4a' }}>{flag.detail}</p>
      </div>
    </div>
  );
}
