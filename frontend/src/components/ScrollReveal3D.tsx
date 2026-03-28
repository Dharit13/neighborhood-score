import { useRef, type ReactNode } from 'react';
import { motion, useInView, useReducedMotion } from 'framer-motion';

interface ScrollReveal3DProps {
  children: ReactNode;
  delay?: number;
  translateZ?: number;
  rotateX?: number;
  className?: string;
}

export default function ScrollReveal3D({
  children,
  delay = 0,
  translateZ = 0,
  rotateX: initialRotateX = -8,
  className,
}: ScrollReveal3DProps) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });
  const prefersReducedMotion = useReducedMotion();

  if (prefersReducedMotion) {
    return (
      <div ref={ref} className={className} style={translateZ ? { transform: `translateZ(${translateZ}px)` } : undefined}>
        {children}
      </div>
    );
  }

  return (
    <motion.div
      ref={ref}
      className={className}
      initial={{ rotateX: initialRotateX, y: 40, opacity: 0, scale: 0.97 }}
      animate={isInView ? { rotateX: 0, y: 0, opacity: 1, scale: 1 } : {}}
      transition={{ type: 'spring', duration: 0.6, bounce: 0.15, delay }}
      style={{
        transformStyle: 'preserve-3d',
        willChange: 'transform, opacity',
        ...(translateZ ? { transform: `translateZ(${translateZ}px)` } : {}),
      }}
    >
      {children}
    </motion.div>
  );
}
