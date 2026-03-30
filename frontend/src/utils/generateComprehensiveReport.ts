import jsPDF from 'jspdf';
import type { NeighborhoodScoreResponse } from '../types';
import { apiUrl } from '../lib/api';

// ── Types ──

interface KeyStat { label: string; value: string }
interface ReportSection { title: string; score: number; highlights: string[] }
interface ScoringSubcategory { name: string; score: number }
interface ScoringCategory { category: string; weight_pct: number; score: number; subcategories: ScoringSubcategory[] }
interface PropertyRow { config: string; purchase_range: string; rent_range: string }
interface ComparisonRow { name: string; composite: number; strongest_edge: string; biggest_gap: string }

interface ComprehensiveReportData {
  neighborhood_name: string;
  headline: string;
  composite_score: number;
  executive_summary: string;
  key_stats: KeyStat[];
  sections: ReportSection[];
  scoring_model: ScoringCategory[];
  property_table: PropertyRow[];
  comparisons: ComparisonRow[];
  bottom_line: string;
  pro_tip: string;
}

// ── Helpers (0-100 scale) ──

type RGB = [number, number, number];

const BLACK: RGB = [0, 0, 0];
const ACCENT: RGB = [24, 32, 52];

function clean(t: string): string {
  return t.replace(/₹/g, 'Rs.').replace(/°/g, ' deg').replace(/[^\x20-\x7E\n]/g, '');
}

function scoreColor(s: number): RGB {
  if (s >= 75) return [16, 150, 110];
  if (s >= 60) return [34, 160, 80];
  if (s >= 40) return [190, 140, 20];
  if (s >= 25) return [220, 100, 30];
  return [210, 50, 50];
}

function scoreBgLight(s: number): RGB {
  if (s >= 75) return [232, 250, 242];
  if (s >= 60) return [236, 252, 240];
  if (s >= 40) return [254, 250, 230];
  if (s >= 25) return [255, 244, 234];
  return [254, 238, 238];
}

function scoreLabel(s: number): string {
  if (s >= 90) return 'Excellent';
  if (s >= 75) return 'Very Good';
  if (s >= 60) return 'Good';
  if (s >= 40) return 'Average';
  if (s >= 25) return 'Below Avg';
  return 'Poor';
}

const SECTION_ACCENTS: RGB[] = [
  [30, 90, 130],
  [145, 95, 25],
  [20, 110, 85],
  [110, 55, 130],
];

// ── Renderer ──

class VisualReport {
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
    if (this.y + n > this.H - 14) {
      this.footer();
      this.d.addPage();
      this.pg++;
      this.y = this.m + 2;
    }
  }

  private footer() {
    this.d.setFontSize(7);
    this.d.setTextColor(140);
    this.d.text('neighbourhoodscore  |  Data: BBMP, CPCB, BWSSB, BESCOM, RERA, Google Maps, ANAROCK', this.m, this.H - 6);
    this.d.text(`${this.pg}`, this.W - this.m, this.H - 6, { align: 'right' });
  }

  private rect(x: number, y: number, w: number, h: number, fill: RGB, border?: RGB) {
    this.d.setFillColor(...fill);
    if (border) {
      this.d.setDrawColor(...border);
      this.d.setLineWidth(0.25);
      this.d.rect(x, y, w, h, 'FD');
    } else {
      this.d.rect(x, y, w, h, 'F');
    }
  }

  // ── Visual primitives ──

  private scoreBar(x: number, y: number, w: number, h: number, score: number) {
    this.rect(x, y, w, h, [235, 237, 242]);
    const fillW = Math.max(1, (score / 100) * w);
    this.rect(x, y, fillW, h, scoreColor(score));
  }

  private scorePill(x: number, y: number, score: number, fontSize = 9) {
    const [r, g, b] = scoreColor(score);
    const bg = scoreBgLight(score);
    const s = Math.round(score);
    const pillW = s >= 100 ? 16 : 14;
    this.rect(x, y - 3.5, pillW, 6, bg, [r, g, b]);
    this.d.setTextColor(r, g, b);
    this.d.setFontSize(fontSize);
    this.d.setFont('helvetica', 'bold');
    this.d.text(`${s}`, x + pillW / 2, y + 0.3, { align: 'center' });
  }

  // ── Build ──

  build(scoreData: NeighborhoodScoreResponse, report: ComprehensiveReportData) {
    const m = this.m;

    // ═══ HEADER ═══
    this.rect(0, 0, this.W, 50, ACCENT);

    this.d.setTextColor(255);
    this.d.setFontSize(22);
    this.d.setFont('helvetica', 'bold');
    this.d.text('Neighbourhood Report', m, 19);

    this.d.setFontSize(11);
    this.d.setFont('helvetica', 'normal');
    const addrLines: string[] = this.d.splitTextToSize(clean(scoreData.address), this.cW * 0.55);
    this.d.text(addrLines.slice(0, 2), m, 29);

    this.d.setFontSize(9);
    this.d.setTextColor(180, 190, 210);
    this.d.text(
      `${scoreData.latitude.toFixed(4)}, ${scoreData.longitude.toFixed(4)}  |  ${new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}`,
      m, 42,
    );

    // Composite badge
    const cs = report.composite_score;
    const [cr, cg, cb] = scoreColor(cs);
    const badgeX = this.W - m - 42;
    this.rect(badgeX, 6, 42, 38, [255, 255, 255]);
    this.d.setTextColor(cr, cg, cb);
    this.d.setFontSize(30);
    this.d.setFont('helvetica', 'bold');
    this.d.text(`${Math.round(cs)}`, badgeX + 21, 25, { align: 'center' });
    this.d.setFontSize(9);
    this.d.text('/ 100', badgeX + 21, 33, { align: 'center' });
    this.d.setFontSize(8);
    this.d.setTextColor(100);
    this.d.text(scoreLabel(cs), badgeX + 21, 40, { align: 'center' });

    this.y = 57;

    // ═══ HEADLINE ═══
    this.d.setFontSize(16);
    this.d.setFont('helvetica', 'bold');
    this.d.setTextColor(...BLACK);
    const hl: string[] = this.d.splitTextToSize(clean(report.headline), this.cW);
    this.d.text(hl, m, this.y);
    this.y += hl.length * 7 + 3;

    // Executive summary
    this.d.setFontSize(11);
    this.d.setFont('helvetica', 'normal');
    this.d.setTextColor(...BLACK);
    const sl: string[] = this.d.splitTextToSize(clean(report.executive_summary), this.cW);
    this.d.text(sl, m, this.y);
    this.y += sl.length * 5 + 7;

    // ═══ KEY STATS ROW ═══
    const stats = (report.key_stats || []).slice(0, 6);
    if (stats.length) {
      const gap = 3;
      const cardW = (this.cW - gap * (stats.length - 1)) / stats.length;
      const cardH = 24;

      for (let i = 0; i < stats.length; i++) {
        const sx = m + i * (cardW + gap);
        this.rect(sx, this.y, cardW, cardH, [247, 248, 252], [220, 222, 230]);

        this.d.setFontSize(12);
        this.d.setFont('helvetica', 'bold');
        this.d.setTextColor(...BLACK);
        const valLines: string[] = this.d.splitTextToSize(clean(stats[i].value), cardW - 4);
        this.d.text(valLines[0] || '', sx + cardW / 2, this.y + 10, { align: 'center' });

        this.d.setFontSize(8);
        this.d.setFont('helvetica', 'normal');
        this.d.setTextColor(...BLACK);
        this.d.text(clean(stats[i].label), sx + cardW / 2, this.y + 18, { align: 'center' });
      }
      this.y += cardH + 8;
    }

    // ═══ CATEGORY SCORE BARS ═══
    if (report.scoring_model?.length) {
      this.d.setFontSize(12);
      this.d.setFont('helvetica', 'bold');
      this.d.setTextColor(...BLACK);
      this.d.text('Score Breakdown', m, this.y);
      this.y += 7;

      const barW = this.cW - 72;
      for (const cat of report.scoring_model) {
        this.check(11);

        this.d.setFontSize(10);
        this.d.setFont('helvetica', 'normal');
        this.d.setTextColor(...BLACK);
        this.d.text(clean(`${cat.category} (${cat.weight_pct}%)`), m, this.y + 1);

        this.scoreBar(m + 54, this.y - 1.5, barW, 4, cat.score);
        this.scorePill(m + 54 + barW + 3, this.y + 0.5, cat.score, 8);

        this.y += 9;
      }
      this.y += 5;
    }

    // ═══ SECTION CARDS ═══
    for (let i = 0; i < report.sections.length; i++) {
      const sec = report.sections[i];
      const accent = SECTION_ACCENTS[i % SECTION_ACCENTS.length];
      this.drawSectionCard(sec, accent);

      if (i === 1 && report.property_table?.length) {
        this.drawPropertyTable(report.property_table);
      }
    }

    // ═══ SCORING DETAIL ═══
    this.drawScoringDetail(report.scoring_model);

    // ═══ COMPARISON TABLE ═══
    if (report.comparisons?.length) {
      this.drawComparisonTable(report.comparisons, report.neighborhood_name, cs);
    }

    // ═══ BOTTOM LINE ═══
    this.check(30);
    this.y += 4;
    this.rect(m, this.y, this.cW, 1, ACCENT);
    this.y += 6;
    this.d.setFontSize(12);
    this.d.setFont('helvetica', 'bold');
    this.d.setTextColor(...BLACK);
    this.d.text('The Bottom Line', m, this.y);
    this.y += 6;
    this.d.setFontSize(10);
    this.d.setFont('helvetica', 'normal');
    this.d.setTextColor(...BLACK);
    const blLines: string[] = this.d.splitTextToSize(clean(report.bottom_line), this.cW - 4);
    for (const ln of blLines) {
      this.check(5);
      this.d.text(ln, m + 2, this.y);
      this.y += 4.8;
    }

    // Pro tip
    if (report.pro_tip) {
      this.y += 5;
      this.check(16);
      this.rect(m, this.y, this.cW, 14, [238, 250, 244], [180, 225, 200]);
      this.d.setFontSize(9);
      this.d.setFont('helvetica', 'bold');
      this.d.setTextColor(...BLACK);
      this.d.text('PRO TIP', m + 5, this.y + 5.5);
      this.d.setFont('helvetica', 'normal');
      this.d.setFontSize(9);
      this.d.setTextColor(...BLACK);
      const tipLines: string[] = this.d.splitTextToSize(clean(report.pro_tip), this.cW - 32);
      this.d.text(tipLines[0] || '', m + 26, this.y + 5.5);
      if (tipLines[1]) this.d.text(tipLines[1], m + 26, this.y + 10);
      this.y += 17;
    }

    this.footer();
    const area = clean(report.neighborhood_name || scoreData.address.split(',')[0]).trim() || 'report';
    this.d.save(`${area.replace(/\s+/g, '-').replace(/[^a-zA-Z0-9-]/g, '').toLowerCase()}-report.pdf`);
  }

  // ── Section card ──

  private drawSectionCard(sec: ReportSection, accent: RGB) {
    const m = this.m;
    const bulletCount = sec.highlights?.length || 0;
    const estH = 16 + bulletCount * 7.5;
    this.check(Math.min(estH, 55));

    this.y += 3;
    const cardTop = this.y;

    this.rect(m, cardTop, 2.5, estH, accent);
    this.rect(m + 2.5, cardTop, this.cW - 2.5, estH, [251, 252, 254], [232, 235, 240]);

    // Title
    this.d.setFontSize(12);
    this.d.setFont('helvetica', 'bold');
    this.d.setTextColor(...BLACK);
    this.d.text(clean(sec.title), m + 8, cardTop + 7);

    // Score pill
    this.scorePill(this.W - m - 20, cardTop + 6, sec.score);

    // Score bar
    this.scoreBar(m + 8, cardTop + 11.5, this.cW - 38, 3, sec.score);

    // Bullet points
    let by = cardTop + 19;
    for (const h of (sec.highlights || [])) {
      if (by > cardTop + estH - 2) break;
      this.d.setFontSize(9);
      this.d.setTextColor(...BLACK);
      this.d.setFont('helvetica', 'normal');
      this.d.text('\u2022', m + 8, by);
      const lines: string[] = this.d.splitTextToSize(clean(h), this.cW - 28);
      this.d.text(lines[0] || '', m + 13, by);
      if (lines.length > 1) {
        by += 5;
        this.d.text(lines[1] || '', m + 13, by);
      }
      by += 6;
    }

    this.y = cardTop + estH + 4;
  }

  // ── Property table ──

  private drawPropertyTable(rows: PropertyRow[]) {
    const m = this.m;
    this.check(12 + rows.length * 8);
    this.y += 1;

    const c0 = m + 4;
    const c1 = m + 42;
    const c2 = m + 112;

    this.rect(m, this.y - 2, this.cW, 8, [50, 55, 70]);
    this.d.setTextColor(255);
    this.d.setFontSize(9);
    this.d.setFont('helvetica', 'bold');
    this.d.text('Type', c0, this.y + 2);
    this.d.text('Purchase Range', c1, this.y + 2);
    this.d.text('Monthly Rent', c2, this.y + 2);
    this.y += 8;

    for (let i = 0; i < rows.length; i++) {
      this.rect(m, this.y - 2, this.cW, 7.5, i % 2 === 0 ? [247, 248, 252] : [255, 255, 255]);
      this.d.setTextColor(...BLACK);
      this.d.setFontSize(9);
      this.d.setFont('helvetica', 'bold');
      this.d.text(clean(rows[i].config), c0, this.y + 1.5);
      this.d.setFont('helvetica', 'normal');
      this.d.text(clean(rows[i].purchase_range), c1, this.y + 1.5);
      this.d.text(clean(rows[i].rent_range), c2, this.y + 1.5);
      this.y += 7.5;
    }
    this.y += 5;
  }

  // ── Scoring detail ──

  private drawScoringDetail(model: ScoringCategory[]) {
    if (!model?.length) return;

    this.check(22);
    this.y += 4;
    this.d.setFontSize(12);
    this.d.setFont('helvetica', 'bold');
    this.d.setTextColor(...BLACK);
    this.d.text('Detailed Scoring', this.m, this.y);
    this.y += 7;

    for (const cat of model) {
      this.check(20);

      this.rect(this.m, this.y - 2, this.cW, 8, [240, 242, 248], [218, 222, 232]);
      this.d.setFontSize(10);
      this.d.setFont('helvetica', 'bold');
      this.d.setTextColor(...BLACK);
      this.d.text(clean(`${cat.category} (${cat.weight_pct}%)`), this.m + 4, this.y + 2.5);

      const [ccr, ccg, ccb] = scoreColor(cat.score);
      this.d.setTextColor(ccr, ccg, ccb);
      this.d.text(`${Math.round(cat.score)}/100`, this.W - this.m - 4, this.y + 2.5, { align: 'right' });
      this.y += 10;

      const subs = cat.subcategories || [];
      let sx = this.m + 4;
      for (const sub of subs) {
        const [sr, sg, sb] = scoreColor(sub.score);
        const nameText = clean(sub.name);
        this.d.setFontSize(9);
        this.d.setFont('helvetica', 'normal');
        const nameW = this.d.getTextWidth(nameText) + 2;
        const pillW = sub.score >= 100 ? 14 : 12;
        const itemW = nameW + pillW + 2;

        if (sx + itemW > this.W - this.m) {
          this.y += 8;
          sx = this.m + 4;
          this.check(9);
        }

        this.d.setTextColor(...BLACK);
        this.d.text(nameText, sx, this.y);

        const pillX = sx + nameW;
        this.rect(pillX, this.y - 3, pillW, 4.5, scoreBgLight(sub.score), [sr, sg, sb]);
        this.d.setTextColor(sr, sg, sb);
        this.d.setFontSize(7.5);
        this.d.setFont('helvetica', 'bold');
        this.d.text(`${Math.round(sub.score)}`, pillX + pillW / 2, this.y, { align: 'center' });

        sx += itemW + 5;
      }
      this.y += 9;
    }
    this.y += 4;
  }

  // ── Comparison table ──

  private drawComparisonTable(comparisons: ComparisonRow[], currentName: string, currentComposite: number) {
    const m = this.m;
    this.check(16 + (comparisons.length + 1) * 9);

    this.y += 3;
    this.d.setFontSize(12);
    this.d.setFont('helvetica', 'bold');
    this.d.setTextColor(...BLACK);
    this.d.text('How It Compares', m, this.y);
    this.y += 7;

    const c0 = m + 3;
    const c1 = m + 44;
    const barStart = m + 64;
    const barW = 50;
    const c3 = m + 120;

    this.rect(m, this.y - 2, this.cW, 7.5, [50, 55, 70]);
    this.d.setTextColor(255);
    this.d.setFontSize(9);
    this.d.setFont('helvetica', 'bold');
    this.d.text('Neighbourhood', c0, this.y + 1.5);
    this.d.text('Score', c1, this.y + 1.5);
    this.d.text('Key Difference', c3, this.y + 1.5);
    this.y += 8;

    // Current neighbourhood
    this.rect(m, this.y - 2.5, this.cW, 8, [232, 248, 238], [180, 225, 200]);
    this.d.setFontSize(9);
    this.d.setFont('helvetica', 'bold');
    this.d.setTextColor(...BLACK);
    this.d.text(clean(currentName), c0, this.y + 1.5);
    this.scorePill(c1, this.y + 2, currentComposite, 8);
    this.scoreBar(barStart, this.y - 0.5, barW, 3, currentComposite);
    this.d.setTextColor(...BLACK);
    this.d.setFontSize(8);
    this.d.setFont('helvetica', 'normal');
    this.d.text('This report', c3, this.y + 1.5);
    this.y += 8.5;

    for (let i = 0; i < comparisons.length; i++) {
      const row = comparisons[i];
      this.rect(m, this.y - 2.5, this.cW, 8, i % 2 === 0 ? [248, 249, 252] : [255, 255, 255]);

      this.d.setFontSize(9);
      this.d.setFont('helvetica', 'bold');
      this.d.setTextColor(...BLACK);
      this.d.text(clean(row.name), c0, this.y + 1.5);

      this.scorePill(c1, this.y + 2, row.composite, 8);
      this.scoreBar(barStart, this.y - 0.5, barW, 3, row.composite);

      this.d.setTextColor(...BLACK);
      this.d.setFontSize(8);
      this.d.setFont('helvetica', 'normal');
      const diffText = `+ ${clean(row.strongest_edge)}  |  - ${clean(row.biggest_gap)}`;
      const diffLines: string[] = this.d.splitTextToSize(diffText, this.W - m - c3 - 2);
      this.d.text(diffLines[0] || '', c3, this.y + 1.5);

      this.y += 8.5;
    }
    this.y += 5;
  }
}

// ── Exported function ──

export async function generateComprehensiveReport(data: NeighborhoodScoreResponse): Promise<void> {
  const response = await fetch(apiUrl('/api/generate-report'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ score_data: data }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Report generation failed' }));
    throw new Error(err.detail || 'Report generation failed');
  }

  const report: ComprehensiveReportData = await response.json();
  new VisualReport().build(data, report);
}
