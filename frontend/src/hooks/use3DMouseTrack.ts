import { useCallback } from 'react';
import { useSpring, useReducedMotion } from 'framer-motion';

interface Use3DMouseTrackConfig {
  maxRotation?: number;
  stiffness?: number;
  damping?: number;
}

export function use3DMouseTrack({
  maxRotation = 6,
  stiffness = 200,
  damping = 25,
}: Use3DMouseTrackConfig = {}) {
  const prefersReducedMotion = useReducedMotion();

  const rotateX = useSpring(0, { stiffness, damping });
  const rotateY = useSpring(0, { stiffness, damping });

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (prefersReducedMotion) return;
      const rect = e.currentTarget.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      rotateY.set(x * maxRotation);
      rotateX.set(-y * maxRotation);
    },
    [prefersReducedMotion, maxRotation, rotateX, rotateY],
  );

  const handleMouseLeave = useCallback(() => {
    rotateX.set(0);
    rotateY.set(0);
  }, [rotateX, rotateY]);

  return { rotateX, rotateY, handleMouseMove, handleMouseLeave };
}
