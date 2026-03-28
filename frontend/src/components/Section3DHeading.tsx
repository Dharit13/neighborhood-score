import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { cn } from '@/lib/utils';

export default function Section3DHeading({ title, subtitle, className }: { title: string; subtitle?: string; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <div ref={ref} className={cn('text-center', className)} style={{ perspective: '600px' }}>
      <motion.h1
        initial={{ y: 30, opacity: 0, rotateX: -15 }}
        animate={isInView ? { y: 0, opacity: 1, rotateX: 0 } : {}}
        transition={{ type: 'spring', duration: 0.6, bounce: 0.15 }}
        className="text-2xl sm:text-3xl font-semibold text-white"
        style={{ transformStyle: 'preserve-3d' }}
      >
        {title}
      </motion.h1>
      {subtitle && (
        <motion.p
          initial={{ y: 20, opacity: 0, rotateX: -10 }}
          animate={isInView ? { y: 0, opacity: 1, rotateX: 0 } : {}}
          transition={{ type: 'spring', duration: 0.6, bounce: 0.15, delay: 0.1 }}
          className="text-sm text-white/50 mt-1"
        >
          {subtitle}
        </motion.p>
      )}
    </div>
  );
}
