import { motion } from 'framer-motion';
import { Train, Bus, GraduationCap, Hospital, Shield, TreePine, ShoppingCart, Building2, Construction, Waves } from 'lucide-react';
import type { NeighborhoodScoreResponse } from '../types';

export interface CategoryDef {
  id: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  color: string;
  match: string[];
}

export const CATEGORIES: CategoryDef[] = [
  { id: 'metro', label: 'Metro', icon: Train, color: '#a855f7', match: ['metro'] },
  { id: 'bus', label: 'Bus', icon: Bus, color: '#3b82f6', match: ['bus_stop'] },
  { id: 'train', label: 'Train', icon: Train, color: '#f97316', match: ['train_station'] },
  { id: 'school', label: 'Schools', icon: GraduationCap, color: '#06b6d4', match: ['school_rank', 'school'] },
  { id: 'hospital', label: 'Hospitals', icon: Hospital, color: '#ec4899', match: ['hospital_tier', 'hospital'] },
  { id: 'police', label: 'Police', icon: Shield, color: '#ef4444', match: ['police_station'] },
  { id: 'park', label: 'Parks', icon: TreePine, color: '#16a34a', match: ['park'] },
  { id: 'grocery', label: 'Grocery', icon: ShoppingCart, color: '#22c55e', match: ['grocery'] },
  { id: 'tech_park', label: 'Tech Parks', icon: Building2, color: '#8b5cf6', match: ['tech_park'] },
  { id: 'future', label: 'Future Infra', icon: Construction, color: '#c084fc', match: ['future_metro', 'future_suburban', 'future_expressway'] },
  { id: 'flood', label: 'Flood Zones', icon: Waves, color: '#38bdf8', match: ['flood', 'water_stage'] },
];

export function getCategoryCount(catId: string, data: NeighborhoodScoreResponse): number {
  const cat = CATEGORIES.find(c => c.id === catId);
  if (!cat) return 0;
  let count = 0;
  const allDetails = [
    ...data.walkability.details,
    ...data.safety.details,
    ...data.hospital_access.details,
    ...data.school_access.details,
    ...data.transit_access.details,
    ...data.air_quality.details,
    ...data.future_infrastructure.details,
    ...(data.commute?.details ?? []),
    ...(data.flood_risk?.details ?? []),
  ];
  for (const d of allDetails) {
    if (cat.match.some(m => d.category.startsWith(m) || d.category === m)) count++;
  }
  return count;
}

interface Props {
  activeCategories: Set<string>;
  onToggle: (id: string) => void;
  data: NeighborhoodScoreResponse;
}

export default function CategoryChips({ activeCategories, onToggle, data }: Props) {
  const containerClass = 'flex gap-2 overflow-x-auto pb-1 scrollbar-thin';

  return (
    <div className={containerClass}>
      {CATEGORIES.map((cat) => {
        const count = getCategoryCount(cat.id, data);
        if (count === 0) return null;
        const active = activeCategories.has(cat.id);
        const Icon = cat.icon;

        return (
          <motion.button
            key={cat.id}
            onClick={() => onToggle(cat.id)}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all whitespace-nowrap ${
              active
                ? 'text-white shadow-lg'
                : 'rounded-lg border border-white/[0.06] text-white/40 hover:text-white/70 hover:bg-white/[0.04]'
            }`}
            style={active ? {
              backgroundColor: cat.color + '30',
              border: `1px solid ${cat.color}60`,
              boxShadow: `0 0 12px ${cat.color}20`,
              color: cat.color,
            } : undefined}
          >
            <Icon size={13} />
            <span>{cat.label}</span>
            <span className="opacity-60 text-[10px]">({count})</span>
          </motion.button>
        );
      })}
    </div>
  );
}
