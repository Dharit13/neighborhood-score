import AutoScroll from "embla-carousel-auto-scroll";
import { Shield, Footprints, Train, Car, Hospital, GraduationCap, Wind, Droplets, Zap, Waves, Building2, Construction, TrendingUp, Package, Volume2, Briefcase, Sparkles } from "lucide-react";

import {
  Carousel,
  CarouselContent,
  CarouselItem,
} from "@/components/ui/carousel";

interface CriteriaItem {
  id: string;
  label: string;
  icon: React.ReactNode;
}

interface Logos3Props {
  heading?: string;
  items?: CriteriaItem[];
  className?: string;
}

const DEFAULT_ITEMS: CriteriaItem[] = [
  { id: "safety", label: "Safety", icon: <Shield size={18} /> },
  { id: "walkability", label: "Walkability", icon: <Footprints size={18} /> },
  { id: "transit", label: "Transit Access", icon: <Train size={18} /> },
  { id: "commute", label: "Commute", icon: <Car size={18} /> },
  { id: "hospitals", label: "Hospitals", icon: <Hospital size={18} /> },
  { id: "schools", label: "Schools", icon: <GraduationCap size={18} /> },
  { id: "air", label: "Air Quality", icon: <Wind size={18} /> },
  { id: "water", label: "Water Supply", icon: <Droplets size={18} /> },
  { id: "power", label: "Power", icon: <Zap size={18} /> },
  { id: "flood", label: "Flood Risk", icon: <Waves size={18} /> },
  { id: "noise", label: "Noise Level", icon: <Volume2 size={18} /> },
  { id: "cleanliness", label: "Cleanliness", icon: <Sparkles size={18} /> },
  { id: "builders", label: "Builders", icon: <Building2 size={18} /> },
  { id: "property", label: "Property Prices", icon: <TrendingUp size={18} /> },
  { id: "infra", label: "Future Infra", icon: <Construction size={18} /> },
  { id: "delivery", label: "Delivery", icon: <Package size={18} /> },
  { id: "business", label: "Business", icon: <Briefcase size={18} /> },
];

const Logos3 = ({
  heading = "We consider all the criteria that matter",
  items = DEFAULT_ITEMS,
}: Logos3Props) => {
  return (
    <section className="w-full">
      <p className="text-[11px] text-white/40 uppercase tracking-[0.2em] text-center mb-4">
        {heading}
      </p>
      <div className="relative mx-auto flex items-center justify-center max-w-xl">
        <Carousel
          opts={{ loop: true, dragFree: true }}
          plugins={[AutoScroll({ playOnInit: true, speed: 0.5 })]}
        >
          <CarouselContent className="ml-0">
            {items.map((item) => (
              <CarouselItem
                key={item.id}
                className="flex basis-1/4 sm:basis-1/5 justify-center pl-0"
              >
                <div className="mx-3 flex shrink-0 items-center gap-1.5 px-3 py-1.5 rounded-full border border-white/[0.06] bg-white/[0.02]">
                  <span className="text-brand-9/60">{item.icon}</span>
                  <span className="text-[11px] text-white/50 whitespace-nowrap">{item.label}</span>
                </div>
              </CarouselItem>
            ))}
          </CarouselContent>
        </Carousel>
        <div className="absolute inset-y-0 left-0 w-12 bg-gradient-to-r from-background to-transparent pointer-events-none" />
        <div className="absolute inset-y-0 right-0 w-12 bg-gradient-to-l from-background to-transparent pointer-events-none" />
      </div>
    </section>
  );
};

export { Logos3 };
