import jsPDF from 'jspdf';
import type { NeighborhoodScoreResponse } from '../types';

const DIMENSIONS: { key: keyof NeighborhoodScoreResponse; label: string; weight: string }[] = [
  { key: 'safety', label: 'Safety', weight: '12%' },
  { key: 'property_prices', label: 'Affordability', weight: '12%' },
  { key: 'transit_access', label: 'Transit Access', weight: '9%' },
  { key: 'flood_risk', label: 'Flood Risk', weight: '8%' },
  { key: 'commute', label: 'Commute', weight: '8%' },
  { key: 'walkability', label: 'Walkability', weight: '7%' },
  { key: 'hospital_access', label: 'Hospital Access', weight: '7%' },
  { key: 'water_supply', label: 'Water Supply', weight: '7%' },
  { key: 'air_quality', label: 'Air Quality', weight: '6%' },
  { key: 'school_access', label: 'School Access', weight: '5%' },
  { key: 'noise', label: 'Noise Level', weight: '4%' },
  { key: 'power_reliability', label: 'Power Reliability', weight: '4%' },
  { key: 'future_infrastructure', label: 'Future Infra', weight: '4%' },
  { key: 'cleanliness', label: 'Cleanliness', weight: '3%' },
  { key: 'builder_reputation', label: 'Builder Rep.', weight: '3%' },
  { key: 'delivery_coverage', label: 'Delivery', weight: '0.5%' },
  { key: 'business_opportunity', label: 'Business', weight: '0.5%' },
];

function scoreColor(s: number): [number, number, number] {
  if (s >= 75) return [5, 150, 105];
  if (s >= 60) return [22, 163, 74];
  if (s >= 40) return [202, 138, 4];
  if (s >= 25) return [234, 88, 12];
  return [220, 38, 38];
}

function scoreBg(s: number): [number, number, number] {
  if (s >= 75) return [236, 253, 245];
  if (s >= 60) return [240, 253, 244];
  if (s >= 40) return [254, 252, 232];
  if (s >= 25) return [255, 247, 237];
  return [254, 242, 242];
}

function label(s: number): string {
  if (s >= 90) return 'Excellent';
  if (s >= 75) return 'Very Good';
  if (s >= 60) return 'Good';
  if (s >= 40) return 'Average';
  if (s >= 25) return 'Below Avg';
  return 'Poor';
}

function clean(t: string): string {
  return t
    .replace(/₹/g, 'Rs.')
    .replace(/°/g, ' deg')
    .replace(/[^\x20-\x7E\n]/g, '');
}

function fmtDuration(mins: number): string {
  const m = Math.round(mins);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const r = m % 60;
  return r === 0 ? `${h} hr` : `${h} hr ${r} min`;
}

class Report {
  private d: jsPDF;
  private y = 0;
  private m = 18;
  private W: number;
  private H: number;
  private cW: number;
  private pg = 1;

  constructor() {
    this.d = new jsPDF({ unit: 'mm', format: 'a4' });
    this.W = this.d.internal.pageSize.getWidth();
    this.H = this.d.internal.pageSize.getHeight();
    this.cW = this.W - this.m * 2;
  }

  private check(n: number) {
    if (this.y + n > this.H - 18) {
      this.footer();
      this.d.addPage();
      this.pg++;
      this.y = this.m + 2;
    }
  }

  private footer() {
    this.d.setFontSize(8);
    this.d.setTextColor(130);
    this.d.text('neighbourhoodscore  |  BBMP, CPCB, BWSSB, BESCOM, RERA, Google Maps, ANAROCK H1 2025', this.m, this.H - 8);
    this.d.text(`Page ${this.pg}`, this.W - this.m, this.H - 8, { align: 'right' });
  }

  private box(x: number, y: number, w: number, h: number, fill: [number, number, number], border?: [number, number, number]) {
    this.d.setFillColor(...fill);
    if (border) {
      this.d.setDrawColor(...border);
      this.d.setLineWidth(0.3);
      this.d.rect(x, y, w, h, 'FD');
    } else {
      this.d.rect(x, y, w, h, 'F');
    }
  }

  private section(title: string, accent: [number, number, number] = [30, 64, 175]) {
    this.check(16);
    this.y += 7;
    this.box(this.m, this.y - 1, this.cW, 10, accent);
    this.d.setTextColor(255);
    this.d.setFontSize(12);
    this.d.setFont('helvetica', 'bold');
    this.d.text(title, this.m + 5, this.y + 5);
    this.y += 14;
  }

  private row(lbl: string, val: string, bold = false) {
    this.check(7);
    this.d.setFontSize(10);
    this.d.setTextColor(50);
    this.d.setFont('helvetica', 'normal');
    this.d.text(lbl, this.m + 5, this.y);
    this.d.setTextColor(15);
    this.d.setFont('helvetica', bold ? 'bold' : 'normal');
    this.d.text(clean(val), this.m + 60, this.y);
    this.y += 6;
  }

  private wrap(text: string, fs = 10, color: [number, number, number] = [20, 20, 20]) {
    this.d.setFontSize(fs);
    this.d.setTextColor(...color);
    this.d.setFont('helvetica', 'normal');
    const lines = this.d.splitTextToSize(clean(text), this.cW - 10);
    const lineH = fs * 0.55;
    this.check(lines.length * lineH + 3);
    this.d.text(lines, this.m + 5, this.y);
    this.y += lines.length * lineH + 3;
  }

  build(data: NeighborhoodScoreResponse) {
    const m = this.m;

    // === HEADER ===
    this.box(0, 0, this.W, 52, [20, 30, 55]);
    this.d.setTextColor(255);
    this.d.setFontSize(24);
    this.d.setFont('helvetica', 'bold');
    this.d.text('Neighbourhood Report', m, 22);

    this.d.setFontSize(11);
    this.d.setFont('helvetica', 'normal');
    const addr = clean(data.address);
    const addrLines = this.d.splitTextToSize(addr, this.cW * 0.6);
    this.d.text(addrLines.slice(0, 2), m, 32);

    this.d.setFontSize(9);
    this.d.setTextColor(180);
    this.d.text(`${data.latitude.toFixed(4)}, ${data.longitude.toFixed(4)}  |  ${new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}`, m, 44);

    if (data.wards_covered?.length) {
      const wText = clean(`Wards: ${data.wards_covered.map(w => w.name).join(', ')}${data.wards_total_population ? ` | Pop: ${data.wards_total_population.toLocaleString('en-IN')}` : ''}`);
      this.d.text(this.d.splitTextToSize(wText, this.cW * 0.7)[0], m, 49);
    }

    // Score badge
    const cs = data.composite_score;
    const [cr, cg, cb] = scoreColor(cs);
    this.box(this.W - m - 44, 8, 44, 36, scoreBg(cs), [cr, cg, cb]);
    this.d.setTextColor(cr, cg, cb);
    this.d.setFontSize(32);
    this.d.setFont('helvetica', 'bold');
    this.d.text(`${cs}`, this.W - m - 22, 28, { align: 'center' });
    this.d.setFontSize(10);
    this.d.text(`/ 100  ${label(cs)}`, this.W - m - 22, 38, { align: 'center' });

    this.y = 60;

    // === KEY DISTANCES ===
    const transit = data.transit_access;
    const keyPois: { label: string; detail: typeof transit.airport }[] = [
      { label: 'Airport', detail: transit.airport },
      { label: 'Majestic Bus Station', detail: transit.majestic },
      { label: 'City Railway (SBC)', detail: transit.city_railway },
    ];
    const hasKeyPois = keyPois.some(p => p.detail);
    if (hasKeyPois) {
      this.section('Key Distances', [50, 70, 120]);
      for (const poi of keyPois) {
        if (!poi.detail) continue;
        this.check(8);
        this.d.setFontSize(10);
        this.d.setFont('helvetica', 'bold');
        this.d.setTextColor(15);
        this.d.text(poi.label, m + 5, this.y);

        const d = poi.detail;
        const parts: string[] = [`${d.distance_km} km`];
        if (d.drive_offpeak_minutes) parts.push(`~${fmtDuration(d.drive_offpeak_minutes)} off-peak`);
        if (d.drive_peak_minutes) parts.push(`~${fmtDuration(d.drive_peak_minutes)} peak`);

        this.d.setFont('helvetica', 'normal');
        this.d.setTextColor(50);
        this.d.text(clean(parts.join('  |  ')), m + 60, this.y);
        this.y += 7;
      }
      this.y += 2;
    }

    // === AI BRIEF ===
    if (data.ai_verification?.verdict || data.ai_verification?.narrative) {
      this.section('Investment Verdict', [0, 105, 140]);

      const LH = 5;
      const FS = 10;

      const brief = data.ai_verification.verdict || data.ai_verification.narrative || '';
      this.d.setFontSize(FS);
      this.d.setFont('helvetica', 'bold');
      this.d.setTextColor(20);
      const bLines = this.d.splitTextToSize(clean(brief), this.cW - 12);
      const bH = bLines.length * LH + 6;
      this.check(bH + 3);
      this.box(m, this.y - 2, this.cW, bH, [245, 250, 255], [200, 215, 235]);
      this.d.text(bLines, m + 6, this.y + 3);
      this.y += bH + 3;

      if (data.ai_verification.best_for) {
        this.d.setFontSize(FS);
        const bfLines = this.d.splitTextToSize(clean(data.ai_verification.best_for), this.cW - 12);
        const bfH = bfLines.length * LH + 6;
        this.check(bfH + 8);
        this.d.setFont('helvetica', 'bold');
        this.d.setTextColor(5, 120, 80);
        this.d.text('BEST FOR:', m + 5, this.y + 2);
        this.y += 6;
        this.box(m, this.y - 2, this.cW, bfH, [240, 255, 245], [180, 230, 200]);
        this.d.setFont('helvetica', 'normal');
        this.d.setTextColor(25);
        this.d.text(bfLines, m + 6, this.y + 2);
        this.y += bfH + 2;
      }

      if (data.ai_verification.avoid_if) {
        this.d.setFontSize(FS);
        const aiLines = this.d.splitTextToSize(clean(data.ai_verification.avoid_if), this.cW - 12);
        const aiH = aiLines.length * LH + 6;
        this.check(aiH + 8);
        this.d.setFont('helvetica', 'bold');
        this.d.setTextColor(180, 30, 30);
        this.d.text('AVOID IF:', m + 5, this.y + 2);
        this.y += 6;
        this.box(m, this.y - 2, this.cW, aiH, [255, 242, 242], [240, 200, 200]);
        this.d.setFont('helvetica', 'normal');
        this.d.setTextColor(25);
        this.d.text(aiLines, m + 6, this.y + 2);
        this.y += aiH + 2;
      }

      const pros = data.ai_verification.pros || [];
      const cons = data.ai_verification.cons || [];

      if (pros.length) {
        this.check(12);
        this.y += 3;
        this.box(m, this.y - 2, this.cW, 8, [5, 120, 80]);
        this.d.setTextColor(255);
        this.d.setFontSize(FS);
        this.d.setFont('helvetica', 'bold');
        this.d.text('PROS', m + 5, this.y + 3);
        this.y += 10;
        for (const p of pros) {
          this.d.setFontSize(FS);
          const pLines = this.d.splitTextToSize(`+  ${clean(p)}`, this.cW - 12);
          this.check(pLines.length * LH + 2);
          this.d.setTextColor(25);
          this.d.setFont('helvetica', 'normal');
          this.d.text(pLines, m + 6, this.y);
          this.y += pLines.length * LH + 2;
        }
      }

      if (cons.length) {
        this.check(12);
        this.y += 3;
        this.box(m, this.y - 2, this.cW, 8, [180, 30, 30]);
        this.d.setTextColor(255);
        this.d.setFontSize(FS);
        this.d.setFont('helvetica', 'bold');
        this.d.text('CONS', m + 5, this.y + 3);
        this.y += 10;
        for (const c of cons) {
          this.d.setFontSize(FS);
          const cLines = this.d.splitTextToSize(`-  ${clean(c)}`, this.cW - 12);
          this.check(cLines.length * LH + 2);
          this.d.setTextColor(25);
          this.d.setFont('helvetica', 'normal');
          this.d.text(cLines, m + 6, this.y);
          this.y += cLines.length * LH + 2;
        }
      }
    }

    // === SCORE TABLE ===
    this.section('17-Dimension Scores', [40, 40, 60]);

    const cols = [m + 4, m + 50, m + 68, m + 88, m + 110];
    this.box(m, this.y - 5, this.cW, 8, [50, 50, 70]);
    this.d.setTextColor(255);
    this.d.setFontSize(9);
    this.d.setFont('helvetica', 'bold');
    this.d.text('Dimension', cols[0], this.y);
    this.d.text('Weight', cols[1], this.y);
    this.d.text('Score', cols[2], this.y);
    this.d.text('Rating', cols[3], this.y);
    this.d.text('Key Detail', cols[4], this.y);
    this.y += 6;

    for (let i = 0; i < DIMENSIONS.length; i++) {
      const dim = DIMENSIONS[i];
      const res = data[dim.key] as { score: number; breakdown?: Record<string, unknown> } | undefined;
      if (!res) continue;
      const s = res.score ?? 0;
      const [sr, sg, sb] = scoreColor(s);

      this.check(7);
      this.box(m, this.y - 4, this.cW, 7, i % 2 === 0 ? [248, 248, 252] : [255, 255, 255]);

      this.d.setTextColor(15);
      this.d.setFontSize(9);
      this.d.setFont('helvetica', 'bold');
      this.d.text(dim.label, cols[0], this.y);

      this.d.setTextColor(80);
      this.d.setFontSize(9);
      this.d.setFont('helvetica', 'normal');
      this.d.text(dim.weight, cols[1], this.y);

      // Score pill
      const pillW = 16;
      this.box(cols[2] - 1, this.y - 3.5, pillW, 5.5, scoreBg(s), [sr, sg, sb]);
      this.d.setTextColor(sr, sg, sb);
      this.d.setFontSize(9);
      this.d.setFont('helvetica', 'bold');
      this.d.text(`${Math.round(s * 10) / 10}`, cols[2] + pillW / 2 - 1, this.y, { align: 'center' });

      this.d.setTextColor(60);
      this.d.setFontSize(9);
      this.d.setFont('helvetica', 'normal');
      this.d.text(label(s), cols[3], this.y);

      this.d.setTextColor(50);
      this.d.setFontSize(8);
      const detail = getKeyDetail(dim.key as string, res.breakdown);
      if (detail) this.d.text(clean(detail).slice(0, 40), cols[4], this.y);

      this.y += 7;
    }

    // === DETAILED CARDS ===
    this.section('Detailed Breakdown', [60, 60, 80]);

    for (const dim of DIMENSIONS) {
      const res = data[dim.key] as { score: number; breakdown?: Record<string, unknown>; details?: Array<{ name: string; distance_km: number }>; sources?: string[] } | undefined;
      if (!res?.breakdown) continue;
      const s = res.score ?? 0;
      const [sr, sg, sb] = scoreColor(s);

      this.check(22);

      // Card header
      this.box(m, this.y - 2, this.cW, 9, [245, 246, 250], [210, 210, 220]);
      this.d.setTextColor(15);
      this.d.setFontSize(11);
      this.d.setFont('helvetica', 'bold');
      this.d.text(dim.label, m + 5, this.y + 3.5);

      this.d.setTextColor(sr, sg, sb);
      this.d.setFontSize(11);
      this.d.setFont('helvetica', 'bold');
      this.d.text(`${Math.round(s * 10) / 10}/100  ${label(s)}`, m + 62, this.y + 3.5);

      this.y += 12;

      // Breakdown rows
      const rows = formatBreakdown(dim.key as string, res.breakdown);
      for (const [lbl, val] of rows) {
        this.check(6);
        this.d.setFontSize(9);
        this.d.setTextColor(70);
        this.d.setFont('helvetica', 'normal');
        this.d.text(lbl, m + 6, this.y);
        this.d.setTextColor(15);
        this.d.setFont('helvetica', 'bold');
        const v = clean(val);
        this.d.text(v.length > 55 ? v.slice(0, 55) + '...' : v, m + 58, this.y);
        this.y += 5.5;
      }

      // Nearby
      if (res.details?.length) {
        this.check(8);
        this.d.setFontSize(10);
        this.d.setFont('helvetica', 'bold');
        this.d.setTextColor(15);
        this.d.text('Nearby:', m + 6, this.y);
        this.y += 6;
        for (const dd of res.details.slice(0, 3)) {
          this.check(6);
          this.d.setFont('helvetica', 'normal');
          this.d.setTextColor(25);
          this.d.setFontSize(9);
          const nm = clean(dd.name);
          this.d.text(`${nm.length > 60 ? nm.slice(0, 60) + '...' : nm}`, m + 8, this.y);
          this.d.setTextColor(70);
          this.d.text(`${dd.distance_km} km`, this.W - m, this.y, { align: 'right' });
          this.y += 5.5;
        }
      }

      this.y += 3;
      this.d.setDrawColor(220);
      this.d.line(m, this.y, this.W - m, this.y);
      this.y += 4;
    }

    // === PROPERTY ===
    const pp = data.property_prices?.breakdown;
    if (pp) {
      this.section('Property & Rental', [170, 100, 10]);
      if (pp.avg_price_sqft) this.row('Avg Price/sqft', `INR ${Number(pp.avg_price_sqft).toLocaleString('en-IN')}`, true);
      if (pp.price_range_low && pp.price_range_high) this.row('Price Range', `INR ${Number(pp.price_range_low).toLocaleString('en-IN')} - ${Number(pp.price_range_high).toLocaleString('en-IN')}/sqft`);
      if (pp.avg_2bhk_price_lakh) this.row('2 BHK Price', `INR ${Number(pp.avg_2bhk_price_lakh)}L`, true);
      if (pp.avg_2bhk_rent) this.row('2 BHK Rent', `INR ${Number(pp.avg_2bhk_rent).toLocaleString('en-IN')}/month`);
      if (pp.yoy_growth_pct) this.row('YoY Growth', `+${pp.yoy_growth_pct}%`, true);
      if (pp.rental_yield_pct) this.row('Rental Yield', `${pp.rental_yield_pct}%`);
      if (pp.rental_recommendation) this.row('Rent vs Buy', String(pp.rental_recommendation), true);
      if (pp.rental_reasoning) this.wrap(String(pp.rental_reasoning), 9, [50, 50, 50]);
    }

    // === REALITY CHECK ===
    this.section('Reality Check: Ads vs Actual', [180, 30, 30]);

    for (const [det, lbl] of [
      [transit.nearest_metro, 'Metro'] as const,
      [transit.nearest_bus_stop, 'Bus'] as const,
      [transit.nearest_train, 'Train'] as const,
    ]) {
      if (!det?.marketing_claim_minutes) continue;
      const delta = det.walk_minutes - det.marketing_claim_minutes;
      if (delta < 1.5) continue;

      this.check(14);
      this.box(m, this.y - 2, this.cW, 12, [255, 248, 240], [240, 200, 160]);
      this.d.setTextColor(15);
      this.d.setFontSize(10);
      this.d.setFont('helvetica', 'bold');
      this.d.text(`${lbl}: ${clean(det.name)}`, m + 5, this.y + 2);
      this.d.setFontSize(9);
      this.d.setFont('helvetica', 'normal');
      this.d.setTextColor(170, 100, 0);
      this.d.text(`Ads: ~${Math.round(det.marketing_claim_minutes)} min`, m + 5, this.y + 7);
      this.d.setTextColor(180, 30, 30);
      this.d.setFont('helvetica', 'bold');
      this.d.text(`Reality: ~${Math.round(det.walk_minutes)} min  (+${Math.round(delta)} min, ${(det.walk_minutes / det.marketing_claim_minutes).toFixed(1)}x)`, m + 48, this.y + 7);
      this.y += 16;
    }

    // Commute
    const cbd = data.commute?.breakdown;
    if (cbd) {
      const claim = (cbd.marketing_claim_min ?? cbd.nearest_no_traffic_min) as number | undefined;
      const peak = (cbd.reality_peak_min ?? cbd.nearest_peak_traffic_min) as number | undefined;
      if (claim && peak) {
        this.check(14);
        this.box(m, this.y - 2, this.cW, 12, [248, 245, 255], [200, 190, 230]);
        this.d.setTextColor(15);
        this.d.setFontSize(10);
        this.d.setFont('helvetica', 'bold');
        this.d.text(`Commute to ${clean(String(cbd.nearest_tech_park || 'tech park'))}`, m + 5, this.y + 2);
        this.d.setFontSize(9);
        this.d.setFont('helvetica', 'normal');
        this.d.setTextColor(100, 60, 160);
        this.d.text(`No-traffic: ~${Math.round(claim)} min`, m + 5, this.y + 7);
        this.d.setTextColor(peak > claim * 1.2 ? 180 : 30, peak > claim * 1.2 ? 30 : 120, peak > claim * 1.2 ? 30 : 60);
        this.d.setFont('helvetica', 'bold');
        this.d.text(`Mon 9AM: ~${Math.round(peak)} min  (${(peak / (claim || 1)).toFixed(1)}x)`, m + 48, this.y + 7);
        this.y += 16;
      }
    }

    // Commute tech parks
    if (data.commute?.details?.length) {
      this.check(10);
      this.d.setFontSize(10);
      this.d.setFont('helvetica', 'bold');
      this.d.setTextColor(15);
      this.d.text('All Tech Park Commutes:', m + 5, this.y);
      this.y += 6;
      for (const dd of data.commute.details.slice(0, 5)) {
        this.check(6);
        this.d.setFontSize(9);
        this.d.setFont('helvetica', 'normal');
        this.d.setTextColor(15);
        const nm = clean(dd.name);
        this.d.text(`${nm.length > 65 ? nm.slice(0, 65) + '...' : nm}`, m + 6, this.y);
        this.d.setTextColor(70);
        this.d.text(`${dd.distance_km} km`, this.W - m, this.y, { align: 'right' });
        this.y += 5.5;
      }
    }

    // === RANKINGS ===
    if (data.recommended_neighborhoods?.length || data.neighborhoods_to_avoid?.length) {
      this.section('Neighborhood Rankings', [5, 120, 80]);

      if (data.recommended_neighborhoods?.length) {
        for (const n of data.recommended_neighborhoods) {
          this.check(16);
          const [nr, ng, nb] = scoreColor(n.score);
          this.box(m, this.y - 2, this.cW, 14, [240, 255, 245], [200, 235, 215]);
          this.d.setTextColor(15);
          this.d.setFontSize(10);
          this.d.setFont('helvetica', 'bold');
          this.d.text(clean(n.name), m + 5, this.y + 3);
          this.d.setTextColor(nr, ng, nb);
          this.d.text(`${n.score}/100`, m + 55, this.y + 3);
          if (n.highlights.length > 0) {
            this.d.setTextColor(15);
            this.d.setFontSize(9);
            this.d.setFont('helvetica', 'normal');
            this.d.text(clean(n.highlights.join('  |  ')), m + 6, this.y + 9);
          }
          this.y += 17;
        }
      }

      if (data.neighborhoods_to_avoid?.length) {
        this.y += 2;
        this.d.setFontSize(10);
        this.d.setFont('helvetica', 'bold');
        this.d.setTextColor(180, 30, 30);
        this.d.text('Watch Out For:', m + 5, this.y);
        this.y += 6;
        for (const n of data.neighborhoods_to_avoid) {
          this.check(16);
          const [nr, ng, nb] = scoreColor(n.score);
          this.box(m, this.y - 2, this.cW, 14, [255, 245, 245], [240, 210, 210]);
          this.d.setTextColor(15);
          this.d.setFontSize(10);
          this.d.setFont('helvetica', 'bold');
          this.d.text(clean(n.name), m + 5, this.y + 3);
          this.d.setTextColor(nr, ng, nb);
          this.d.text(`${n.score}/100`, m + 55, this.y + 3);
          if (n.highlights.length > 0) {
            this.d.setTextColor(15);
            this.d.setFontSize(9);
            this.d.setFont('helvetica', 'normal');
            this.d.text(clean(n.highlights.join('  |  ')), m + 6, this.y + 9);
          }
          this.y += 17;
        }
      }
    }

    // === RENT VS BUY ===
    if (data.best_to_buy?.length || data.best_to_rent?.length) {
      this.section('Rent vs Buy', [30, 80, 160]);
      for (const a of (data.best_to_buy || [])) {
        this.check(7);
        this.d.setFontSize(9);
        this.d.setFont('helvetica', 'bold');
        this.d.setTextColor(15);
        this.d.text(clean(a.area), m + 5, this.y);
        this.d.setFont('helvetica', 'normal');
        this.d.setTextColor(50);
        this.d.text(clean(`INR ${a.avg_price_sqft.toLocaleString('en-IN')}/sqft | ${a.rental_yield_pct}% yield | EMI ${a.emi_rent_ratio}x rent | Buy`), m + 44, this.y);
        this.y += 6;
      }
      for (const a of (data.best_to_rent || [])) {
        this.check(7);
        this.d.setFontSize(9);
        this.d.setFont('helvetica', 'bold');
        this.d.setTextColor(15);
        this.d.text(clean(a.area), m + 5, this.y);
        this.d.setFont('helvetica', 'normal');
        this.d.setTextColor(50);
        this.d.text(clean(`INR ${a.avg_2bhk_rent.toLocaleString('en-IN')}/mo | EMI ${a.emi_rent_ratio}x rent | Rent`), m + 44, this.y);
        this.y += 6;
      }
    }

    this.footer();
    const area = clean(data.address).split(',')[0]?.trim() || 'report';
    this.d.save(`${area.replace(/\s+/g, '-').toLowerCase()}-score-report.pdf`);
  }
}

export async function generateReport(data: NeighborhoodScoreResponse): Promise<void> {
  new Report().build(data);
}

function fmtNum(v: unknown): string {
  if (v == null) return '-';
  const n = Number(v);
  if (isNaN(n)) return String(v);
  return n % 1 === 0 ? n.toLocaleString('en-IN') : n.toFixed(1);
}

function formatBreakdown(dimKey: string, bd: Record<string, unknown>): [string, string][] {
  const rows: [string, string][] = [];
  const push = (l: string, v: unknown, sfx = '') => { if (v != null && v !== '') rows.push([l, `${fmtNum(v)}${sfx}`]); };
  const pushS = (l: string, v: unknown) => { if (v != null && v !== '') rows.push([l, String(v)]); };

  switch (dimKey) {
    case 'safety':
      pushS('Zone', bd.zone); push('Crime Rate', bd.crime_rate_per_100k, '/100k');
      push('CCTV Density', bd.cctv_density_per_sqkm, '/sq km'); push('Nearest Police Stn', bd.nearest_police_station_km, ' km');
      push('Surveillance', bd.surveillance_coverage, '/100'); push('Streetlights', bd.streetlight_coverage, '/100');
      break;
    case 'property_prices':
      pushS('Area', bd.area); push('Avg Price', bd.avg_price_sqft ? `INR ${fmtNum(bd.avg_price_sqft)}/sqft` : null);
      push('2BHK', bd.avg_2bhk_price_lakh ? `INR ${fmtNum(bd.avg_2bhk_price_lakh)}L` : null);
      push('2BHK Rent', bd.avg_2bhk_rent ? `INR ${fmtNum(bd.avg_2bhk_rent)}/mo` : null);
      push('EMI/Income', bd.emi_to_income_pct, '%'); pushS('Verdict', bd.rental_recommendation);
      push('YoY Growth', bd.yoy_growth_pct, '%'); push('Yield', bd.rental_yield_pct, '%');
      break;
    case 'transit_access':
      push('Nearest Metro', bd.nearest_metro_m, ' m'); push('Nearest Bus', bd.nearest_bus_m, ' m');
      push('Nearest Train', bd.nearest_train_m, ' m');
      push('Metro Score', bd.metro_proximity, '/100'); push('Bus Score', bd.bus_stop_proximity, '/100');
      break;
    case 'flood_risk':
      pushS('Risk Level', bd.risk_level); push('Flood Events', bd.flood_history_events);
      push('Elevation', bd.elevation_m, ' m'); pushS('Drainage', bd.drainage_quality);
      pushS('Flood Ward', bd.bbmp_flood_ward ? 'Yes' : 'No');
      break;
    case 'commute':
      pushS('Nearest Park', bd.nearest_tech_park); push('Distance', bd.nearest_distance_km, ' km');
      push('No-traffic', bd.nearest_no_traffic_min, ' min'); push('Peak (9AM)', bd.nearest_peak_traffic_min, ' min');
      push('Traffic Factor', bd.traffic_multiplier, 'x');
      break;
    case 'walkability':
      pushS('Area', bd.matched_area); push('Score', bd.base_walkability_score, '/100');
      push('Parks in 1km', bd.parks_within_1km);
      break;
    case 'hospital_access':
      push('NABH Score', bd.nabh_hospital_proximity, '/100'); push('Bed Density', bd.bed_density_vs_iphs, '/100');
      push('Beds in 5km', bd.total_beds_within_5km); push('Bed Ratio', bd.bed_ratio, 'x norm');
      break;
    case 'water_supply':
      pushS('Stage', bd.cauvery_stage ? `Stage ${bd.cauvery_stage}` : null);
      push('Supply', bd.supply_hours_per_day, ' hrs/day'); pushS('Reliability', bd.reliability);
      break;
    case 'air_quality':
      push('AQI', bd.weighted_aqi); pushS('Category', bd.aqi_category);
      pushS('Station', bd.nearest_station); push('Distance', bd.nearest_station_km, ' km');
      break;
    case 'school_access':
      push('RTE Score', bd.rte_compliance, '/100'); push('Quality', bd.quality_proximity, '/100');
      push('Schools 1km', bd.schools_within_1km_rte); push('Schools 3km', bd.schools_within_3km_rte);
      break;
    case 'noise':
      push('Noise Level', bd.avg_noise_db_estimate, ' dB'); pushS('Rating', bd.noise_label);
      pushS('Exceeds Std', bd.exceeds_cpcb_residential ? 'Yes' : 'No');
      pushS('Flight Path', bd.airport_flight_path ? 'Yes' : 'No'); push('Highway', bd.highway_proximity_km, ' km');
      break;
    case 'power_reliability':
      pushS('Tier', bd.bescom_tier ? `Tier ${bd.bescom_tier} (${bd.tier_label})` : null);
      push('Outages', bd.avg_monthly_outage_hours, ' hrs/mo');
      break;
    case 'future_infrastructure':
      push('Stn in 800m', bd.stations_within_tod_800m); push('Stn in 2km', bd.stations_within_2km);
      push('Stn in 5km', bd.stations_within_5km);
      break;
    case 'cleanliness':
      push('Slums in 2km', bd.slum_count_2km); push('Deprivation', bd.avg_deprivation_dn, '/245');
      push('Waste Centres (5km)', bd.dry_waste_centres_5km); push('Waste Score', bd.waste_access_score, '/100');
      break;
    case 'builder_reputation':
      push('Avg Score', bd.area_average_score, '/100'); push('Active', bd.active_builders_in_area);
      push('Recommended', bd.recommended_count); push('Avoid', bd.avoid_count);
      break;
    case 'delivery_coverage':
      push('Services', bd.coverage_count, '/5'); push('Delivery Time', bd.avg_delivery_min, ' min');
      break;
    case 'business_opportunity':
      push('Acceptance', bd.new_business_acceptability_pct, '%'); push('Footfall', bd.footfall_index, '/100');
      push('Startups', bd.startup_density_per_sqkm, '/sq km'); push('Coworking', bd.coworking_spaces);
      break;
    default:
      for (const [k, v] of Object.entries(bd)) {
        if (v == null || k === 'methodology' || k === 'weighted_by') continue;
        if (typeof v === 'number') push(k.replace(/_/g, ' '), v);
        else if (typeof v === 'string' && v.length < 50) pushS(k.replace(/_/g, ' '), v);
      }
  }
  return rows;
}

function getKeyDetail(key: string, bd?: Record<string, unknown>): string {
  if (!bd) return '';
  switch (key) {
    case 'safety': return bd.crime_rate_per_100k ? `Crime: ${bd.crime_rate_per_100k}/100k` : '';
    case 'property_prices': return bd.avg_price_sqft ? `INR ${Number(bd.avg_price_sqft).toLocaleString()}/sqft` : '';
    case 'air_quality': return bd.aqi_category ? `AQI: ${bd.aqi_category}` : '';
    case 'water_supply': return bd.cauvery_stage ? `Stage ${bd.cauvery_stage}` : '';
    case 'power_reliability': return bd.bescom_tier ? `Tier ${bd.bescom_tier}` : '';
    case 'commute': return bd.nearest_tech_park ? String(bd.nearest_tech_park) : '';
    case 'flood_risk': return bd.flood_history_events ? `${bd.flood_history_events} events` : '';
    case 'noise': return bd.avg_noise_db_estimate ? `${Math.round(Number(bd.avg_noise_db_estimate))} dB` : '';
    case 'cleanliness': return bd.slum_count_2km != null ? `${bd.slum_count_2km} slums` : '';
    case 'transit_access': return bd.nearest_metro_m ? `Metro ${Math.round(Number(bd.nearest_metro_m))}m` : '';
    case 'hospital_access': return bd.total_beds_within_5km ? `${bd.total_beds_within_5km} beds` : '';
    case 'school_access': return bd.schools_within_3km_rte ? `${bd.schools_within_3km_rte} schools` : '';
    default: return '';
  }
}
