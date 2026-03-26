import { motion } from 'framer-motion';
import { CATEGORIES, getCategoryCount } from '@/utils/categories';
import type { NeighborhoodScoreResponse } from '../types';

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
