import { useState, useEffect, useMemo } from 'react';
import { measureText, areFontsReady, waitForFonts } from '@/lib/pretext';
import type { LayoutResult } from '@chenglou/pretext';

interface UseTextMeasureInput {
  text: string;
  font: string;
  maxWidth: number;
  lineHeight: number;
}

interface UseTextMeasureResult extends LayoutResult {
  ready: boolean;
}

/**
 * React hook for measuring text dimensions via Pretext (no DOM reflow).
 * Returns { height, lineCount, ready }. When ready=false, falls back to
 * zero values — callers should use DOM measurement as fallback.
 */
export function useTextMeasure({ text, font, maxWidth, lineHeight }: UseTextMeasureInput): UseTextMeasureResult {
  const [ready, setReady] = useState(areFontsReady);

  useEffect(() => {
    if (!ready) {
      waitForFonts().then(() => setReady(true));
    }
  }, [ready]);

  const result = useMemo(() => {
    if (!ready || !text || maxWidth <= 0 || lineHeight <= 0) {
      return { height: 0, lineCount: 0 };
    }
    return measureText(text, font, maxWidth, lineHeight);
  }, [text, font, maxWidth, lineHeight, ready]);

  return { ...result, ready };
}
