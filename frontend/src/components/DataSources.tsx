import { motion } from 'framer-motion';
import { Footprints, Shield, Volume2, Hospital, GraduationCap, Train, Car, Package, Wind, Droplets, Zap, Waves, Building2, Construction, TrendingUp, Briefcase, Sparkles } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

const DIMENSIONS = [
  {
    num: '01', name: 'Walkability', icon: Footprints, weight: 5,
    desc: 'Pedestrian infrastructure, sidewalk quality, and walkable amenities within 500m',
    sources: [
      { name: 'OpenCity.in', url: 'https://data.opencity.in' },
      { name: 'ITDP India', url: 'https://www.itdp.in' },
      { name: 'Google Places API', url: 'https://developers.google.com/maps' },
    ],
  },
  {
    num: '02', name: 'Safety', icon: Shield, weight: 12,
    desc: 'Crime rate per capita, police station proximity, and safety zone classification',
    sources: [
      { name: 'BBMP Zone Data', url: 'https://data.opencity.in' },
      { name: 'Karnataka NCRB', url: 'https://data.opencity.in' },
      { name: 'MOHUA EoLI', url: 'https://smartcities.gov.in' },
    ],
  },
  {
    num: '03', name: 'Noise Level', icon: Volume2, weight: 3,
    desc: 'Ambient noise estimates from traffic, airports, and highways',
    sources: [
      { name: 'CPCB Noise Monitoring', url: 'https://cpcb.nic.in' },
      { name: 'data.gov.in', url: 'https://data.gov.in' },
    ],
  },
  {
    num: '04', name: 'Cleanliness', icon: Sparkles, weight: 3,
    desc: 'Waste infrastructure density, slum proximity, and sanitation facilities',
    sources: [
      { name: 'BBMP Waste Infra', url: 'https://data.opencity.in' },
      { name: 'Bengaluru Slums Map', url: 'https://data.opencity.in' },
    ],
  },
  {
    num: '05', name: 'Hospital Access', icon: Hospital, weight: 8,
    desc: 'NABH-accredited hospitals and clinics within IPHS 2022 norms',
    sources: [
      { name: 'BBMP Hospital List', url: 'https://data.opencity.in' },
      { name: 'NABH Portal', url: 'https://portal.nabh.co' },
      { name: 'IPHS 2022', url: 'https://nhm.gov.in' },
    ],
  },
  {
    num: '06', name: 'School Access', icon: GraduationCap, weight: 8,
    desc: 'Top-ranked schools within RTE Act 1km/3km norms',
    sources: [
      { name: 'IIRF 2024 Rankings', url: 'https://www.iirf.in' },
      { name: 'RTE Act 2009', url: 'https://education.gov.in' },
      { name: 'Google Places API', url: 'https://developers.google.com/maps' },
    ],
  },
  {
    num: '07', name: 'Transit Access', icon: Train, weight: 10,
    desc: 'Metro, bus stop, and train station proximity with actual walk times',
    sources: [
      { name: 'BMTC Bus Stops', url: 'https://github.com/openbangalore' },
      { name: 'Namma Metro', url: 'https://data.opencity.in' },
      { name: 'Indian Railways', url: 'https://www.irctc.co.in' },
      { name: 'Google Directions', url: 'https://developers.google.com/maps' },
    ],
  },
  {
    num: '08', name: 'Commute', icon: Car, weight: 10,
    desc: 'Peak and off-peak driving times to major tech parks',
    sources: [
      { name: 'Google Distance Matrix', url: 'https://developers.google.com/maps/documentation/distance-matrix' },
    ],
  },
  {
    num: '09', name: 'Delivery Coverage', icon: Package, weight: 3,
    desc: 'Quick commerce serviceability across Zepto, Blinkit, Swiggy, BigBasket',
    sources: [
      { name: 'Zepto', url: 'https://zepto.com' },
      { name: 'Blinkit', url: 'https://blinkit.com' },
      { name: 'Swiggy Instamart', url: 'https://www.swiggy.com' },
      { name: 'BigBasket', url: 'https://www.bigbasket.com' },
    ],
  },
  {
    num: '10', name: 'Air Quality', icon: Wind, weight: 5,
    desc: 'Weighted AQI from nearest CPCB monitoring stations',
    sources: [
      { name: 'CPCB National AQI', url: 'https://cpcb.nic.in' },
      { name: 'AQI Stations Data', url: 'https://data.opencity.in' },
      { name: 'data.gov.in', url: 'https://data.gov.in' },
    ],
  },
  {
    num: '11', name: 'Water Supply', icon: Droplets, weight: 7,
    desc: 'BWSSB Cauvery stage classification and supply hours',
    sources: [
      { name: 'BWSSB Cauvery Stages', url: 'https://bwssb.karnataka.gov.in' },
      { name: 'OpenCity.in BWSSB', url: 'https://data.opencity.in' },
    ],
  },
  {
    num: '12', name: 'Power Reliability', icon: Zap, weight: 4,
    desc: 'BESCOM tier classification and outage frequency',
    sources: [
      { name: 'BESCOM', url: 'https://bescom.karnataka.gov.in' },
    ],
  },
  {
    num: '13', name: 'Flood Risk', icon: Waves, weight: 5,
    desc: 'Historical flood events, elevation, and drainage quality',
    sources: [
      { name: 'BBMP Flood Spots', url: 'https://data.opencity.in' },
      { name: 'Google Elevation API', url: 'https://developers.google.com/maps' },
    ],
  },
  {
    num: '14', name: 'Builder Reputation', icon: Building2, weight: 5,
    desc: 'RERA compliance, project delivery record, and customer ratings',
    sources: [
      { name: 'RERA Karnataka', url: 'https://rera.karnataka.gov.in' },
      { name: 'MagicBricks', url: 'https://www.magicbricks.com' },
      { name: '99acres', url: 'https://www.99acres.com' },
    ],
  },
  {
    num: '15', name: 'Property Prices', icon: TrendingUp, weight: 5,
    desc: 'Average price/sqft, 2BHK prices, rent, YoY growth, and rental yield',
    sources: [
      { name: 'RBI RAPMS', url: 'https://rbi.org.in' },
      { name: 'ANAROCK', url: 'https://www.anarock.com' },
      { name: 'MagicBricks', url: 'https://www.magicbricks.com' },
    ],
  },
  {
    num: '16', name: 'Future Infrastructure', icon: Construction, weight: 4,
    desc: 'Upcoming metro lines, suburban rail, and road projects',
    sources: [
      { name: 'Namma Metro Phase 2', url: 'https://booknewproperty.com' },
      { name: 'K-RIDE Suburban Rail', url: 'https://en.wikipedia.org/wiki/Bangalore_Suburban_Railway' },
    ],
  },
  {
    num: '17', name: 'Business Opportunity', icon: Briefcase, weight: 3,
    desc: 'Tech park proximity, startup ecosystem, and commercial activity',
    sources: [
      { name: 'Karnataka Startup Cell', url: 'https://startup.karnataka.gov.in' },
      { name: 'BBMP Trade License', url: 'https://data.opencity.in' },
    ],
  },
];

export default function DataSources() {
  return (
    <div>
      <div className="sticky top-12 z-20 bg-black/50 backdrop-blur-md pb-4 pt-2 text-center">
        <h1 className="text-2xl sm:text-3xl font-semibold text-white">
          Data Sources
        </h1>
        <p className="text-sm text-white mt-1">
          17 dimensions scored from 8+ government agencies and verified APIs
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-4">
        {DIMENSIONS.map((dim, i) => {
          const Icon = dim.icon;
          return (
            <motion.div
              key={dim.num}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04, type: 'spring', damping: 25 }}
              className="rounded-xl bg-white/[0.03] backdrop-blur-sm p-5 hover:translate-y-[-2px] transition-transform duration-300"
            >
              <div className="flex items-start justify-between mb-3">
                <span className="text-brand-9/40 text-3xl font-bold leading-none select-none">
                  {dim.num}
                </span>
                <Badge variant="stroke">{dim.weight}%</Badge>
              </div>
              <div className="flex items-center gap-2 mb-2">
                <Icon size={16} className="text-brand-9" />
                <h3 className="text-sm font-semibold text-white">{dim.name}</h3>
              </div>
              <p className="text-xs text-white leading-relaxed mb-3">
                {dim.desc}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {dim.sources.map((src) => (
                  <a
                    key={src.name}
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[10px] px-2 py-0.5 rounded-full bg-white/[0.04] text-white hover:text-brand-9 hover:border-brand-9/30 transition"
                  >
                    {src.name}
                  </a>
                ))}
              </div>
            </motion.div>
          );
        })}
      </div>

      <div className="divider my-8" />
      <p className="text-center text-[11px] text-white pb-8">
        Data freshness varies by source. Most government datasets are updated quarterly.
        AI verification runs nightly using Claude for data quality assurance.
      </p>
    </div>
  );
}
