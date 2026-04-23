import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { catchError, firstValueFrom, forkJoin, Observable, of } from 'rxjs';
import { CompareService } from '../services/compare.service';

interface AppOption {
  id: string;
  name: string;
}

interface TrendPoint {
  date: string;
  avg_sentiment_score: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  total_count: number;
}

interface FeatureComparisonRow {
  feature: string;
  aScore: number;
  bScore: number;
  aLabel: string;
  bLabel: string;
  winner: string;
  delta: number;
  explanation: string;
}

interface PainPointRow {
  issue: string;
  aCount: number;
  bCount: number;
  aNegPct: number;
  bNegPct: number;
  winner: string;
  delta: number;
  explanation: string;
}

interface AppSummary {
  appId: string;
  name: string;
  totalReviews: number;
  avgRating: number;
  avgSentiment: number;
  sentimentLabel: string;
  sentimentClass: string;
  trendLabel: string;
  trendClass: string;
  trendDirection: 'improving' | 'declining' | 'stable';
  recentVolume: number;
  previousVolume: number;
  volumeChange: number;
  recentSentiment: number;
  previousSentiment: number;
  compositeScore: number;
  strengths: string[];
  weaknesses: string[];
  mismatchSignals: string[];
  localeSignals: string[];
  versionSignals: string[];
}

interface OpportunityCard {
  title: string;
  detail: string;
  app: string;
  severity: 'high' | 'medium' | 'low';
  evidence?: string;
}

interface ContextSignal {
  title: string;
  detail: string;
}

interface ReviewRecord {
  rating: number;
  sentiment: string;
  sentiment_score: number;
  issue_category?: string;
  app_version?: string;
  locale?: string;
  timestamp?: string;
  text?: string;
}

interface TrendWindow {
  recentSentiment: number;
  previousSentiment: number;
  recentVolume: number;
  previousVolume: number;
  volumeChange: number;
  direction: 'improving' | 'declining' | 'stable';
}

@Component({
  selector: 'app-compare',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './compare.component.html',
  styleUrls: ['./compare.component.scss']
})
export class CompareComponent implements OnInit {
  monitoredApps: AppOption[] = [
    { id: 'in.swiggy.android', name: 'Swiggy' },
    { id: 'com.application.zomato', name: 'Zomato' },
    { id: 'com.ubercab.eats', name: 'Uber Eats' },
    { id: 'in.swiggy.android.instamart', name: 'Swiggy Instamart' }
  ];

  appA = this.monitoredApps[0].id;
  appB = this.monitoredApps[1].id;

  loading = false;
  error = '';
  isIngesting = false;
  ingestProgress = 0;
  status = '';

  featureRows: FeatureComparisonRow[] = [];
  painPointRows: PainPointRow[] = [];
  appSummaries: AppSummary[] = [];
  opportunities: OpportunityCard[] = [];
  contextSignals: ContextSignal[] = [];
  executiveSummary = '';
  actionItems: string[] = [];
  overallWinner = '';
  overallMargin = 0;
  readonly compareLocaleLabel = 'IND';

  private hasAutoLoaded = false;

  constructor(
    private compareService: CompareService,
    private router: Router,
    private route: ActivatedRoute,
  ) {}

  ngOnInit(): void {
    this.route.queryParams.subscribe(params => {
      if (params['appA'] && !this.hasAutoLoaded) {
        this.hasAutoLoaded = true;
        this.appA = params['appA'];
        this.appB = this.monitoredApps.find(app => app.id !== this.appA)?.id || this.appB;
        this.compare();
      }
    });
  }

  goToDashboard(): void {
    this.router.navigate(['/'], {
      queryParams: { app: this.appA }
    });
  }

  async compare(): Promise<void> {
    if (this.appA === this.appB) {
      this.error = 'Select two different apps';
      this.loading = false;
      return;
    }

    this.loading = true;
    this.error = '';
    this.status = '⏳ Ingesting reviews...';
    this.ingestProgress = 0;
    this.isIngesting = true;
    this.featureRows = [];
    this.painPointRows = [];
    this.appSummaries = [];
    this.opportunities = [];
    this.contextSignals = [];
    this.executiveSummary = '';
    this.actionItems = [];
    this.overallWinner = '';
    this.overallMargin = 0;

    try {
      await firstValueFrom(this.compareService.ingestReviews(this.appA, 'in'));
      this.ingestProgress = 50;
      await firstValueFrom(this.compareService.ingestReviews(this.appB, 'in'));
      this.ingestProgress = 100;
      this.isIngesting = false;
      this.status = '🔄 Comparing insights...';
      this.runComparison();
    } catch {
      this.error = 'Failed to ingest';
      this.loading = false;
      this.isIngesting = false;
      this.status = '';
    }
  }

  private safeGet<T>(source: Observable<T>, fallback: T): Observable<T> {
    return source.pipe(catchError(() => of(fallback)));
  }

  runComparison(): void {
    const apps = [this.appA, this.appB];

    forkJoin({
      sentiment: this.safeGet(this.compareService.compareSentiment(apps), { comparison: {} } as any),
      aspects: this.safeGet(this.compareService.compareAspects(apps), { aspects_comparison: {}, detailed_data: {} } as any),
      issues: this.safeGet(this.compareService.compareIssues(apps), { top_issues: {} } as any),
      trendsA: this.safeGet(this.compareService.getTrends(this.appA, 30), { trend_data: [] } as any),
      trendsB: this.safeGet(this.compareService.getTrends(this.appB, 30), { trend_data: [] } as any),
      reviewsA: this.safeGet(this.compareService.listReviews(this.appA, 30, 120), { reviews: [] } as any),
      reviewsB: this.safeGet(this.compareService.listReviews(this.appB, 30, 120), { reviews: [] } as any),
    }).subscribe({
      next: (res: any) => {
        const sentimentMap = res.sentiment?.comparison || {};
        const aspectMap = res.aspects?.aspects_comparison || {};
        const issueMap = res.issues?.top_issues || {};
        const trendsA = res.trendsA?.trend_data || [];
        const trendsB = res.trendsB?.trend_data || [];
        const reviewsA = res.reviewsA?.reviews || [];
        const reviewsB = res.reviewsB?.reviews || [];

        this.featureRows = this.buildFeatureRows(aspectMap);
        this.painPointRows = this.buildPainPointRows(issueMap);
        this.appSummaries = this.buildAppSummaries(
          sentimentMap,
          trendsA,
          trendsB,
          reviewsA,
          reviewsB,
          this.featureRows,
          issueMap,
        );
        this.opportunities = this.buildOpportunities(this.featureRows, this.painPointRows)
          .sort((a, b) => this.severityRank(a.severity) - this.severityRank(b.severity));
        this.contextSignals = this.buildContextSignals(reviewsA, reviewsB);
        this.overallWinner = this.getOverallWinner(this.appSummaries);
        this.overallMargin = this.getOverallMargin(this.appSummaries);
        this.executiveSummary = this.buildExecutiveSummary(this.appSummaries, this.featureRows, this.opportunities);
        this.actionItems = this.opportunities.slice(0, 4).map(item => item.detail);
        this.status = '✅ Comparison complete';
        this.loading = false;
      },
      error: () => {
        this.error = 'Comparison failed';
        this.loading = false;
        this.status = '';
      }
    });
  }

  private buildFeatureRows(aspectMap: Record<string, Record<string, number>>): FeatureComparisonRow[] {
    return Object.entries(aspectMap)
      .map(([feature, values]) => {
        const aScore = Number(values?.[this.appA] || 0);
        const bScore = Number(values?.[this.appB] || 0);

        return {
          feature,
          aScore,
          bScore,
          aLabel: this.featureLabel(aScore),
          bLabel: this.featureLabel(bScore),
          winner: this.pickWinner(aScore, bScore, this.appA, this.appB),
          delta: Math.abs(aScore - bScore),
          explanation: this.buildFeatureExplanation(feature, aScore, bScore),
        };
      })
      .sort((a, b) => b.delta - a.delta);
  }

  private buildPainPointRows(issueMap: Record<string, Array<any>>): PainPointRow[] {
    const rowsA = issueMap?.[this.appA] || [];
    const rowsB = issueMap?.[this.appB] || [];
    const categories = new Set<string>();

    rowsA.forEach(row => categories.add(row.category));
    rowsB.forEach(row => categories.add(row.category));

    return Array.from(categories)
      .map(category => {
        const rowA = rowsA.find(row => row.category === category) || {};
        const rowB = rowsB.find(row => row.category === category) || {};
        const aNegPct = Number(rowA.negative_percentage || 0);
        const bNegPct = Number(rowB.negative_percentage || 0);
        const aCount = Number(rowA.mention_count || 0);
        const bCount = Number(rowB.mention_count || 0);

        return {
          issue: category,
          aCount,
          bCount,
          aNegPct,
          bNegPct,
          winner: this.pickWinnerLowIsGood(aNegPct, bNegPct, this.appA, this.appB),
          delta: Math.abs(aNegPct - bNegPct),
          explanation: this.buildPainPointExplanation(category, aNegPct, bNegPct, aCount, bCount),
        };
      })
      .sort((a, b) => b.delta - a.delta);
  }

  private buildAppSummaries(
    sentimentMap: Record<string, any>,
    trendsA: TrendPoint[],
    trendsB: TrendPoint[],
    reviewsA: ReviewRecord[],
    reviewsB: ReviewRecord[],
    featureRows: FeatureComparisonRow[],
    issueMap: Record<string, Array<any>>,
  ): AppSummary[] {
    return [
      this.createAppSummary(this.appA, trendsA, reviewsA, sentimentMap[this.appA], featureRows, issueMap[this.appA] || []),
      this.createAppSummary(this.appB, trendsB, reviewsB, sentimentMap[this.appB], featureRows, issueMap[this.appB] || []),
    ];
  }

  private createAppSummary(
    appId: string,
    trendData: TrendPoint[],
    reviews: ReviewRecord[],
    sentimentSnapshot: any,
    featureRows: FeatureComparisonRow[],
    issueRows: Array<any>,
  ): AppSummary {
    const name = this.getAppName(appId);
    const avgRating = Number(sentimentSnapshot?.avg_rating ?? this.average(reviews.map(review => Number(review.rating || 0)))) || 0;
    const avgSentiment = Number(sentimentSnapshot?.avg_sentiment_score ?? this.average(reviews.map(review => Number(review.sentiment_score || 0.5)))) || 0;
    const totalReviews = Number(sentimentSnapshot?.total_reviews ?? reviews.length) || 0;
    const window = this.calculateTrendWindow(trendData);

    return {
      appId,
      name,
      totalReviews,
      avgRating,
      avgSentiment,
      sentimentLabel: this.sentimentLabel(avgSentiment),
      sentimentClass: this.sentimentClass(avgSentiment),
      trendLabel: window.direction === 'improving' ? 'Improving' : window.direction === 'declining' ? 'Declining' : 'Stable',
      trendClass: window.direction === 'improving' ? 'trend-up' : window.direction === 'declining' ? 'trend-down' : 'trend-stable',
      trendDirection: window.direction,
      recentVolume: window.recentVolume,
      previousVolume: window.previousVolume,
      volumeChange: window.volumeChange,
      recentSentiment: window.recentSentiment,
      previousSentiment: window.previousSentiment,
      compositeScore: this.computeCompositeScore(avgRating, avgSentiment, window, issueRows),
      strengths: this.extractStrengths(appId, featureRows),
      weaknesses: this.extractWeaknesses(appId, featureRows),
      mismatchSignals: this.buildMismatchSignals(reviews),
      localeSignals: this.topSignals(
        reviews
          .map(review => review.locale)
          .filter((value): value is string => !!value && value.toUpperCase() !== 'EN_US'),
        2,
      ),
      versionSignals: this.topSignals(reviews.map(review => review.app_version).filter(Boolean) as string[], 2),
    };
  }

  private buildOpportunities(featureRows: FeatureComparisonRow[], painPointRows: PainPointRow[]): OpportunityCard[] {
    const cards: OpportunityCard[] = [];
    const appAName = this.getAppName(this.appA);
    const appBName = this.getAppName(this.appB);

    // Align opportunities directly with the feature comparison table:
    // only rows where App B currently leads are treated as App A gap opportunities.
    const gapRows = featureRows
      .filter(row => row.winner === appBName && row.delta >= 0.04)
      .sort((a, b) => b.delta - a.delta)
      .slice(0, 3);

    gapRows.forEach(row => {
      const gap = row.delta.toFixed(2);
      cards.push({
        title: `Close ${this.formatLabel(row.feature)} gap`,
        detail: `${appBName} currently leads on ${this.formatLabel(row.feature)}. Prioritize this area in the next sprint and target at least a ${Math.max(0.02, row.delta / 2).toFixed(2)} score lift to reduce churn risk.`,
        app: appAName,
        severity: row.delta > 0.12 ? 'high' : 'medium',
        evidence: `${appAName}: ${row.aScore.toFixed(2)} vs ${appBName}: ${row.bScore.toFixed(2)} (gap ${gap})`,
      });
    });

    // Align with pain-point table: rows where App B has higher negative complaint rate.
    const attackRows = painPointRows
      .filter(row => row.bNegPct - row.aNegPct >= 4 && row.bCount >= 5)
      .sort((a, b) => (b.bNegPct - b.aNegPct) - (a.bNegPct - a.aNegPct))
      .slice(0, 3);

    attackRows.forEach(row => {
      const pctGap = (row.bNegPct - row.aNegPct).toFixed(1);
      cards.push({
        title: `Attack competitor weakness in ${this.formatLabel(row.issue)}`,
        detail: `${appBName} users report more pain in ${this.formatLabel(row.issue)}. Promote ${appAName}'s stronger experience in campaigns and tighten onboarding around this flow to capture switchers.`,
        app: appAName,
        severity: row.bNegPct > 30 ? 'high' : 'medium',
        evidence: `${appAName}: ${row.aNegPct.toFixed(1)}% negative vs ${appBName}: ${row.bNegPct.toFixed(1)}% negative (${pctGap}pt gap)`,
      });
    });

    const dedup = new Map<string, OpportunityCard>();
    cards.forEach(card => {
      const key = card.title.toLowerCase();
      if (!dedup.has(key)) {
        dedup.set(key, card);
      }
    });
    const finalCards = Array.from(dedup.values()).slice(0, 6);

    if (!finalCards.length) {
      const strongestGap = featureRows
        .filter(row => row.winner === appBName)
        .sort((a, b) => b.delta - a.delta)[0];
      finalCards.push({
        title: 'No clear gap identified',
        detail: strongestGap
          ? `Closest actionable gap is ${this.formatLabel(strongestGap.feature)}. Run a focused experiment to lift ${appAName} from ${strongestGap.aScore.toFixed(2)} toward ${appBName}'s ${strongestGap.bScore.toFixed(2)}.`
          : 'Both apps are currently close; watch weekly shifts in sentiment and complaint frequency to find openings.',
        app: appAName,
        severity: 'low',
      });
    }

    return finalCards;
  }

  private buildContextSignals(reviewsA: ReviewRecord[], reviewsB: ReviewRecord[]): ContextSignal[] {
    const appANegativeHighRating = reviewsA.filter(review => Number(review.rating || 0) >= 4 && review.sentiment === 'negative').length;
    const appBNegativeHighRating = reviewsB.filter(review => Number(review.rating || 0) >= 4 && review.sentiment === 'negative').length;
    const appALowRatingPositive = reviewsA.filter(review => Number(review.rating || 0) <= 2 && review.sentiment === 'positive').length;
    const appBLowRatingPositive = reviewsB.filter(review => Number(review.rating || 0) <= 2 && review.sentiment === 'positive').length;

    return [
      {
        title: 'Rating vs review mismatch',
        detail: `${this.getAppName(this.appA)} has ${appANegativeHighRating} high-rating negative reviews, while ${this.getAppName(this.appB)} has ${appBNegativeHighRating}. This is an early warning signal when stars still look healthy.`,
      },
      {
        title: 'Low-rating praise check',
        detail: `${this.getAppName(this.appA)} has ${appALowRatingPositive} low-rating positive outliers, while ${this.getAppName(this.appB)} has ${appBLowRatingPositive}. That often signals mixed journeys or inconsistent labeling.`,
      },
    ];
  }

  private buildExecutiveSummary(appSummaries: AppSummary[], featureRows: FeatureComparisonRow[], opportunities: OpportunityCard[]): string {
    if (appSummaries.length < 2) {
      return 'No comparison data available yet.';
    }

    const winner = this.getOverallWinner(appSummaries);
    const strongestFeature = featureRows[0];
    const topOpportunity = opportunities[0];

    if (winner === 'Tie') {
      return `The two apps are close overall. ${this.getAppName(this.appA)} leads on ${appSummaries[0].strengths[0] || 'some feature areas'}, while ${this.getAppName(this.appB)} is stronger on ${appSummaries[1].strengths[0] || 'other feature areas'}. The clearest opportunity is ${topOpportunity?.title || 'closing the most visible feature gap'}.`;
    }

    return `${winner} is ahead overall. ${strongestFeature ? `${this.formatLabel(strongestFeature.feature)} is the clearest differentiator` : 'The strongest signal is balanced feature performance'}. ${topOpportunity ? topOpportunity.detail : 'Monitor trend momentum and complaint frequency to keep the lead.'}`;
  }

  private calculateTrendWindow(trendData: TrendPoint[]): TrendWindow {
    const recentWindow = trendData.slice(-7);
    const previousWindow = trendData.slice(-14, -7);
    const recentSentiment = recentWindow.length ? this.average(recentWindow.map(point => point.avg_sentiment_score)) : 0;
    const previousSentiment = previousWindow.length ? this.average(previousWindow.map(point => point.avg_sentiment_score)) : recentSentiment;
    const recentVolume = recentWindow.reduce((sum, point) => sum + Number(point.total_count || 0), 0);
    const previousVolume = previousWindow.reduce((sum, point) => sum + Number(point.total_count || 0), 0);
    const sentimentDelta = recentSentiment - previousSentiment;
    const volumeChange = previousVolume > 0 ? (recentVolume - previousVolume) / previousVolume : 0;

    let direction: 'improving' | 'declining' | 'stable' = 'stable';
    if (sentimentDelta > 0.03) {
      direction = 'improving';
    } else if (sentimentDelta < -0.03) {
      direction = 'declining';
    } else if (Math.abs(volumeChange) > 0.2) {
      direction = volumeChange > 0 ? 'declining' : 'improving';
    }

    return {
      recentSentiment,
      previousSentiment,
      recentVolume,
      previousVolume,
      volumeChange,
      direction,
    };
  }

  private computeCompositeScore(avgRating: number, avgSentiment: number, window: TrendWindow, issueRows: Array<any>): number {
    const sentimentScore = this.clamp(avgSentiment, 0, 1) * 40;
    const ratingScore = this.clamp(avgRating / 5, 0, 1) * 10;
    const trendScore = this.clamp(0.5 + (window.recentSentiment - window.previousSentiment) * 3 + window.volumeChange * 0.1, 0, 1) * 20;

    const issueTotals = issueRows.reduce(
      (acc, row) => {
        acc.total += Number(row.mention_count || 0);
        acc.weighted += Number(row.negative_percentage || 0) * Number(row.mention_count || 0);
        return acc;
      },
      { total: 0, weighted: 0 }
    );

    const averageNegativePct = issueTotals.total > 0 ? issueTotals.weighted / issueTotals.total : 0;
    const issueScore = (1 - this.clamp(averageNegativePct / 100, 0, 1)) * 30;

    return Number((sentimentScore + ratingScore + trendScore + issueScore).toFixed(1));
  }

  private extractStrengths(appId: string, featureRows: FeatureComparisonRow[]): string[] {
    return featureRows
      .filter(row => row.winner === this.getAppName(appId) && row.delta > 0.03)
      .slice(0, 3)
      .map(row => `${this.formatLabel(row.feature)} (${row.delta.toFixed(2)})`);
  }

  private extractWeaknesses(appId: string, featureRows: FeatureComparisonRow[]): string[] {
    return featureRows
      .filter(row => row.winner !== this.getAppName(appId) && row.delta > 0.03)
      .slice(0, 3)
      .map(row => `${this.formatLabel(row.feature)} (${row.delta.toFixed(2)})`);
  }

  private buildMismatchSignals(reviews: ReviewRecord[]): string[] {
    const highRatingNegatives = reviews.filter(review => Number(review.rating || 0) >= 4 && review.sentiment === 'negative').length;
    const lowRatingPositives = reviews.filter(review => Number(review.rating || 0) <= 2 && review.sentiment === 'positive').length;
    return [
      `${highRatingNegatives} high-rating reviews still read as negative`,
      `${lowRatingPositives} low-rating reviews still read as positive`,
    ];
  }

  private topSignals(values: string[], limit: number): string[] {
    const counts = new Map<string, number>();
    values.forEach(value => counts.set(value, (counts.get(value) || 0) + 1));
    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, limit)
      .map(([value, count]) => `${value} (${count})`);
  }

  private buildFeatureExplanation(feature: string, aScore: number, bScore: number): string {
    const winner = aScore > bScore ? this.getAppName(this.appA) : this.getAppName(this.appB);
    const loser = aScore > bScore ? this.getAppName(this.appB) : this.getAppName(this.appA);
    return `${winner} leads on ${this.formatLabel(feature)} by ${Math.abs(aScore - bScore).toFixed(2)} sentiment score points versus ${loser}.`;
  }

  private buildPainPointExplanation(issue: string, aNegPct: number, bNegPct: number, aCount: number, bCount: number): string {
    const leader = aNegPct < bNegPct ? this.getAppName(this.appA) : this.getAppName(this.appB);
    return `${leader} has the lower pain level for ${this.formatLabel(issue)} by ${Math.abs(aNegPct - bNegPct).toFixed(1)}% negative mentions (${aCount} vs ${bCount} reviews mentioning it).`;
  }

  private getOverallWinner(appSummaries: AppSummary[]): string {
    if (appSummaries.length < 2) {
      return 'Tie';
    }

    const [first, second] = appSummaries;
    const diff = first.compositeScore - second.compositeScore;
    if (Math.abs(diff) < 2) {
      return 'Tie';
    }
    return diff > 0 ? first.name : second.name;
  }

  private getOverallMargin(appSummaries: AppSummary[]): number {
    if (appSummaries.length < 2) {
      return 0;
    }
    return Number(Math.abs(appSummaries[0].compositeScore - appSummaries[1].compositeScore).toFixed(1));
  }

  private featureLabel(score: number): string {
    if (score > 0.15) {
      return 'Strong';
    }
    if (score < -0.15) {
      return 'Weak';
    }
    return 'Mixed';
  }

  private sentimentLabel(score: number): string {
    if (score >= 0.6) {
      return 'Positive';
    }
    if (score >= 0.4) {
      return 'Mixed';
    }
    return 'Negative';
  }

  private sentimentClass(score: number): string {
    if (score >= 0.6) {
      return 'sentiment-good';
    }
    if (score >= 0.4) {
      return 'sentiment-mid';
    }
    return 'sentiment-bad';
  }

  private pickWinner(aScore: number, bScore: number, aName: string, bName: string): string {
    if (Math.abs(aScore - bScore) < 0.03) {
      return 'Tie';
    }
    return aScore > bScore ? this.getAppName(aName) : this.getAppName(bName);
  }

  private pickWinnerLowIsGood(aScore: number, bScore: number, aName: string, bName: string): string {
    if (Math.abs(aScore - bScore) < 2) {
      return 'Tie';
    }
    return aScore < bScore ? this.getAppName(aName) : this.getAppName(bName);
  }

  private severityRank(severity: OpportunityCard['severity']): number {
    if (severity === 'high') {
      return 0;
    }
    if (severity === 'medium') {
      return 1;
    }
    return 2;
  }

  private average(values: number[]): number {
    if (!values.length) {
      return 0;
    }
    return values.reduce((sum, value) => sum + value, 0) / values.length;
  }

  private clamp(value: number, min: number, max: number): number {
    return Math.max(min, Math.min(max, value));
  }

  getAppName(id: string): string {
    return this.monitoredApps.find(app => app.id === id)?.name || id;
  }

  formatLabel(text: string): string {
    return (text || '')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  }

  get featureGapCountForAppA(): number {
    const appBName = this.getAppName(this.appB);
    return this.featureRows.filter(row => row.winner === appBName && row.delta >= 0.04).length;
  }

  get painGapCountForAppA(): number {
    return this.painPointRows.filter(row => row.bNegPct - row.aNegPct >= 4 && row.bCount >= 5).length;
  }

  get consistencyBadgeLabel(): string {
    return `Consistency Check: Aligned (${this.compareLocaleLabel})`;
  }

  getSentimentScoreTooltip(app: AppSummary): string {
    return [
      `Overall sentiment score is the average of review sentiment_score values (0 to 1).`,
      `Label thresholds: Positive >= 0.60, Mixed 0.40-0.59, Negative < 0.40.`,
      `Current ${app.name} score: ${app.avgSentiment.toFixed(3)}.`
    ].join(' ');
  }

  getCompositeScoreTooltip(): string {
    return [
      `Composite score = Sentiment (40) + Rating (10) + Trend (20) + Issue quality (30).`,
      `Sentiment: clamp(avgSentiment, 0..1) x 40.`,
      `Rating: clamp(avgRating/5, 0..1) x 10.`,
      `Trend: clamp(0.5 + 3 x sentimentDelta + 0.1 x volumeChange, 0..1) x 20.`,
      `Issue quality: (1 - clamp(weightedNegativePct/100, 0..1)) x 30.`
    ].join(' ');
  }

  getFeatureScoreFormulaTooltip(): string {
    return `Feature sentiment score = positive_ratio - negative_ratio. Range is typically -1 to +1; higher is better.`;
  }

  getFeatureCellTooltip(row: FeatureComparisonRow, side: 'a' | 'b'): string {
    const appName = side === 'a' ? this.getAppName(this.appA) : this.getAppName(this.appB);
    const value = side === 'a' ? row.aScore : row.bScore;
    return `${appName} ${this.formatLabel(row.feature)} score: ${value.toFixed(2)}. Computed as positive_ratio - negative_ratio for this feature.`;
  }
}
