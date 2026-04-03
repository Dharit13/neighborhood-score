import { prepare, layout, type PreparedText, type LayoutResult } from '@chenglou/pretext';

// Singleton cache: avoids re-preparing the same font spec
const preparedCache = new Map<string, PreparedText>();

// Font readiness promise — gates accurate measurement
let fontsReady = false;
const fontsReadyPromise: Promise<void> =
  typeof document !== 'undefined'
    ? document.fonts.ready.then(() => { fontsReady = true; })
    : Promise.resolve();

export function areFontsReady(): boolean {
  return fontsReady;
}

export function waitForFonts(): Promise<void> {
  return fontsReadyPromise;
}

/**
 * Get or create a prepared text measurement for a given string + font spec.
 * Font spec follows CSS shorthand: e.g. "13px Plus Jakarta Sans" or "bold 9pt Helvetica"
 */
function getPrepared(text: string, font: string): PreparedText {
  const key = `${font}::${text}`;
  let cached = preparedCache.get(key);
  if (!cached) {
    cached = prepare(text, font);
    preparedCache.set(key, cached);
    // Evict old entries if cache grows too large
    if (preparedCache.size > 500) {
      const first = preparedCache.keys().next().value;
      if (first) preparedCache.delete(first);
    }
  }
  return cached;
}

/**
 * Measure text dimensions without triggering DOM reflow.
 * Returns { height, lineCount } for the given text at the specified font,
 * wrapped to maxWidth with the given lineHeight (both in px).
 */
export function measureText(
  text: string,
  font: string,
  maxWidth: number,
  lineHeight: number,
): LayoutResult {
  const prepared = getPrepared(text, font);
  return layout(prepared, maxWidth, lineHeight);
}

/**
 * Clear the prepared text cache (e.g. on font change or memory pressure).
 */
export function clearPretextCache(): void {
  preparedCache.clear();
}
