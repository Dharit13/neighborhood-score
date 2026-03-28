import { type ReactNode } from 'react';
import { motion } from 'framer-motion';
import { use3DMouseTrack } from '@/hooks/use3DMouseTrack';

interface Perspective3DContainerProps {
  children: ReactNode;
  perspective?: number;
  maxRotation?: number;
  disabled?: boolean;
  className?: string;
}

export default function Perspective3DContainer({
  children,
  perspective = 1000,
  maxRotation = 3,
  disabled = false,
  className,
}: Perspective3DContainerProps) {
  const { rotateX, rotateY, handleMouseMove, handleMouseLeave } = use3DMouseTrack({
    maxRotation,
    stiffness: 150,
    damping: 20,
  });

  if (disabled) {
    return (
      <div className={className} style={{ perspective: `${perspective}px` }}>
        {children}
      </div>
    );
  }

  return (
    <div
      className={className}
      style={{ perspective: `${perspective}px` }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <motion.div
        style={{
          rotateX,
          rotateY,
          transformStyle: 'preserve-3d',
          willChange: 'transform',
        }}
      >
        {children}
      </motion.div>
    </div>
  );
}
