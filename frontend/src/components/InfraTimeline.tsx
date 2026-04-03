import { useState } from 'react';
import { motion } from 'framer-motion';
import { Badge } from '@/components/ui/badge';
import type { InfraProject } from '@/types';

const TYPE_COLORS: Record<string, string> = {
  metro: '#06b6d4',
  suburban_rail: '#8b5cf6',
  expressway: '#f59e0b',
  highway: '#f59e0b',
  flyover: '#ef4444',
  road: '#6b7280',
};

function parseYear(dateStr?: string): number | null {
  if (!dateStr) return null;
  const match = dateStr.match(/(\d{4})/);
  return match ? parseInt(match[1]) : null;
}

interface Props {
  projects: InfraProject[];
}

export default function InfraTimeline({ projects }: Props) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  if (projects.length === 0) {
    return (
      <div className="text-center py-6 text-sm" style={{ color: '#a09888' }}>No infrastructure projects found</div>
    );
  }

  const now = new Date().getFullYear();
  const allYears = projects.flatMap(p => {
    const years: number[] = [];
    const off = parseYear(p.official_completion_date);
    const low = parseYear(p.realistic_completion_date_low);
    const high = parseYear(p.realistic_completion_date_high);
    if (off) years.push(off);
    if (low) years.push(low);
    if (high) years.push(high);
    return years;
  });
  allYears.push(now);

  const minYear = Math.min(...allYears) - 1;
  const maxYear = Math.max(...allYears) + 1;
  const span = maxYear - minYear;

  function yearToPercent(year: number) {
    return ((year - minYear) / span) * 100;
  }

  return (
    <div className="space-y-2">
      {/* Year axis */}
      <div className="relative h-6">
        {Array.from({ length: span + 1 }, (_, i) => minYear + i).map(year => (
          <span
            key={year}
            className="absolute text-[9px] font-mono -translate-x-1/2"
            style={{ color: '#a09888', left: `${yearToPercent(year)}%` }}
          >
            {year}
          </span>
        ))}
      </div>

      {/* Project bars */}
      {projects.map((project, i) => {
        const color = TYPE_COLORS[project.type] ?? '#6b7280';
        const offYear = parseYear(project.official_completion_date);
        const realLow = parseYear(project.realistic_completion_date_low);
        const realHigh = parseYear(project.realistic_completion_date_high);
        const isHovered = hoveredIdx === i;

        return (
          <div
            key={i}
            className="relative"
            onMouseEnter={() => setHoveredIdx(i)}
            onMouseLeave={() => setHoveredIdx(null)}
          >
            <div className="flex items-center gap-2 mb-1">
              <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
              <span className="text-[11px] truncate flex-1" style={{ color: '#4a4a4a' }}>{project.name}</span>
              <Badge variant="mono-light" className="text-[8px] flex-shrink-0">{project.type}</Badge>
              <span className="text-[10px] font-mono" style={{ color: '#a09888' }}>{project.completion_percentage}%</span>
            </div>

            <div className="relative h-4 rounded-full overflow-hidden" style={{ background: 'rgba(208,200,184,0.4)' }}>
              {/* Completion fill */}
              <motion.div
                className="absolute top-0 left-0 h-full rounded-full opacity-30"
                style={{ backgroundColor: color }}
                initial={{ width: 0 }}
                animate={{ width: `${yearToPercent(now)}%` }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
              />

              {/* Official ETA marker */}
              {offYear && (
                <div
                  className="absolute top-0 h-full w-0.5 border-l border-dashed"
                  style={{ borderColor: '#a09888', left: `${yearToPercent(offYear)}%` }}
                  title={`Official: ${project.official_completion_date}`}
                />
              )}

              {/* Realistic range */}
              {realLow && realHigh && (
                <motion.div
                  className="absolute top-0.5 bottom-0.5 rounded-full"
                  style={{
                    left: `${yearToPercent(realLow)}%`,
                    width: `${yearToPercent(realHigh) - yearToPercent(realLow)}%`,
                    backgroundColor: color,
                    opacity: 0.6,
                  }}
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ duration: 0.5, delay: i * 0.1 }}
                />
              )}
            </div>

            {/* Hover tooltip */}
            {isHovered && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="absolute z-10 top-full mt-1 left-0 right-0 rounded-lg bg-[#faf7f0] border border-[#a09888] shadow-lg p-3 text-xs space-y-1"
              >
                <p className="font-semibold" style={{ color: '#1a1a1a' }}>{project.name}</p>
                <p style={{ color: '#8a8a8a' }}>{project.current_status}</p>
                {project.route_description && <p style={{ color: '#8a8a8a' }}>{project.route_description}</p>}
                <div className="flex gap-3" style={{ color: '#8a8a8a' }}>
                  {project.official_completion_date && <span>Official: {project.official_completion_date}</span>}
                  {project.realistic_completion_date_low && <span>Realistic: {project.realistic_completion_date_low} — {project.realistic_completion_date_high}</span>}
                </div>
                {project.prediction_confidence && (
                  <Badge variant="mono-light" className="text-[8px]">Confidence: {project.prediction_confidence}</Badge>
                )}
                {project.delay_multiplier && project.delay_multiplier > 1 && (
                  <span className="text-amber-700 text-[10px]">{project.delay_multiplier}x typical delay</span>
                )}
              </motion.div>
            )}
          </div>
        );
      })}

      <div className="flex items-center gap-4 pt-2 text-[9px]" style={{ color: '#a09888' }}>
        <span className="flex items-center gap-1"><span className="inline-block w-3 h-0.5 border-t border-dashed" style={{ borderColor: '#a09888' }} /> Official ETA</span>
        <span className="flex items-center gap-1"><span className="inline-block w-3 h-2 rounded-sm" style={{ background: 'rgba(160,152,136,0.4)' }} /> Realistic range</span>
      </div>
    </div>
  );
}
