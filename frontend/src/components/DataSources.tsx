import { Footprints, Shield, Volume2, Hospital, GraduationCap, Train, Car, Package, Wind, Droplets, Zap, Waves, Building2, Construction, TrendingUp, Briefcase, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';

import ScrollReveal3D from './ScrollReveal3D';
import { use3DMouseTrack } from '@/hooks/use3DMouseTrack';

const DIMENSIONS = [
  { name: 'Walkability', icon: Footprints, weight: 5, sources: ['OpenCity.in', 'ITDP India', 'Google Places'] },
  { name: 'Safety', icon: Shield, weight: 12, sources: ['BBMP Zones', 'NCRB', 'MOHUA'] },
  { name: 'Noise', icon: Volume2, weight: 3, sources: ['CPCB', 'data.gov.in'] },
  { name: 'Cleanliness', icon: Sparkles, weight: 3, sources: ['BBMP Waste', 'Slums Map'] },
  { name: 'Hospitals', icon: Hospital, weight: 8, sources: ['BBMP', 'NABH', 'IPHS'] },
  { name: 'Schools', icon: GraduationCap, weight: 8, sources: ['IIRF 2024', 'RTE Act', 'Google'] },
  { name: 'Transit', icon: Train, weight: 10, sources: ['BMTC', 'Metro', 'Railways'] },
  { name: 'Commute', icon: Car, weight: 10, sources: ['Google Distance Matrix'] },
  { name: 'Delivery', icon: Package, weight: 3, sources: ['Zepto', 'Blinkit', 'Swiggy'] },
  { name: 'Air Quality', icon: Wind, weight: 5, sources: ['CPCB AQI', 'data.gov.in'] },
  { name: 'Water', icon: Droplets, weight: 7, sources: ['BWSSB', 'OpenCity.in'] },
  { name: 'Power', icon: Zap, weight: 4, sources: ['BESCOM'] },
  { name: 'Flood Risk', icon: Waves, weight: 5, sources: ['BBMP', 'Google Elevation'] },
  { name: 'Builders', icon: Building2, weight: 5, sources: ['RERA', 'MagicBricks', '99acres'] },
  { name: 'Prices', icon: TrendingUp, weight: 5, sources: ['RBI', 'ANAROCK', 'MagicBricks'] },
  { name: 'Future Infra', icon: Construction, weight: 4, sources: ['Metro Ph2', 'K-RIDE'] },
  { name: 'Business', icon: Briefcase, weight: 3, sources: ['KA Startup', 'BBMP Trade'] },
];

function DimensionCard({ dim, index }: { dim: typeof DIMENSIONS[number]; index: number }) {
  const Icon = dim.icon;
  const { rotateX, rotateY, handleMouseMove, handleMouseLeave } = use3DMouseTrack({ maxRotation: 6 });

  return (
    <ScrollReveal3D delay={index * 0.03} rotateX={-6}>
      <motion.div
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        style={{ rotateX, rotateY, transformStyle: 'preserve-3d' }}
        className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-4 hover:border-brand-9/20 transition-colors duration-300"
      >
        <div className="flex items-center gap-2.5 mb-3">
          <div className="w-9 h-9 rounded-lg bg-white/[0.06] flex items-center justify-center flex-shrink-0" style={{ transform: 'translateZ(8px)' }}>
            <Icon size={18} className="text-brand-9" />
          </div>
          <span className="text-[15px] font-medium text-white flex-1">{dim.name}</span>
          <span className="text-xs text-white/30 font-mono">{dim.weight}%</span>
        </div>
        <div className="flex flex-wrap gap-1.5" style={{ transform: 'translateZ(4px)' }}>
          {dim.sources.map((s) => (
            <span key={s} className="text-xs px-2.5 py-1 rounded-full border border-white/10 bg-white/[0.05] text-white/60">{s}</span>
          ))}
        </div>
      </motion.div>
    </ScrollReveal3D>
  );
}

export default function DataSources() {
  return (
    <div className="h-full flex flex-col items-center justify-center px-6">
      <div className="w-full max-w-6xl grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4" style={{ perspective: '1000px' }}>
        {DIMENSIONS.map((dim, index) => (
          <DimensionCard key={dim.name} dim={dim} index={index} />
        ))}
      </div>

      <p className="text-[10px] text-white/25 text-center mt-5">
        Updated quarterly &middot; AI verification nightly via Claude
      </p>
    </div>
  );
}
