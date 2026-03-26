export const TRUST_TIERS = [
  { min: 75, color: '#16a34a', label: 'Trusted' },
  { min: 55, color: '#2563eb', label: 'Emerging' },
  { min: 40, color: '#ca8a04', label: 'Use Caution' },
  { min: 0, color: '#dc2626', label: 'Avoid' },
] as const;

export function getTrustTier(score: number) {
  return TRUST_TIERS.find(t => score >= t.min) ?? TRUST_TIERS[TRUST_TIERS.length - 1];
}
