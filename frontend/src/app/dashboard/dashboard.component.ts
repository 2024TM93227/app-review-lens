import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { ApiService } from '../services/api.service';
import { SentimentChartComponent } from '../components/sentiment-chart.component';
import { SummaryCardComponent } from '../components/summary-card/summary-card.component';
import { IssueListComponent } from '../components/issue-list/issue-list.component';
import { AlertsPanelComponent } from '../components/alerts/alerts-panel.component';
import { ChartsComponent } from '../components/charts/charts.component';
import { FiltersComponent, FilterState } from '../components/filters/filters.component';
import {
  InsightsV2Response,
  TopIssue,
  Alert,
  RatingTrendPoint,
} from '../models/insights.model';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css'],
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    SentimentChartComponent,
    SummaryCardComponent,
    IssueListComponent,
    AlertsPanelComponent,
    ChartsComponent,
    FiltersComponent,
  ]
})
export class DashboardComponent implements OnInit {

  monitoredApps = [
    { name: 'Swiggy', id: 'in.swiggy.android' },
    { name: 'Zomato', id: 'com.application.zomato' },
    { name: 'Uber Eats', id: 'com.ubercab.eats' },
    { name: 'Swiggy Instamart', id: 'in.swiggy.android.instamart' }
  ];

  appId: string = this.restoreAppId();

  // V2 data
  topIssues: TopIssue[] = [];
  alerts: Alert[] = [];
  ratingTrend: RatingTrendPoint[] = [];
  totalReviews = 0;
  playstoreRating: number | null = null;

  // V1 data (kept for sentiment chart)
  stats: any = {};
  recentReviews: any[] = [];
  sentimentData = { positive: 0, negative: 0, neutral: 0 };

  // Filters
  currentFilters: FilterState = { days: 30, rating: null, sentiment: null };

  loading = false;
  error = '';
  infoMessage = '';
  lastRefreshed = '';
  showAllReviews = false;
  activeTab: 'overview' | 'reviews' = 'overview';

  constructor(
    private api: ApiService,
    private router: Router,
    private route: ActivatedRoute,
  ) {}

  ngOnInit(): void {
    const qp = this.route.snapshot.queryParamMap.get('appId');
    if (qp && this.monitoredApps.some(a => a.id === qp)) {
      this.appId = qp;
    }
    this.persistAppId();
    this.loadDashboard();
  }

  private restoreAppId(): string {
    try {
      const saved = localStorage.getItem('arl_appId');
      if (saved && this.monitoredApps.some(a => a.id === saved)) {
        return saved;
      }
    } catch { /* noop */ }
    return this.monitoredApps[0].id;
  }

  private persistAppId(): void {
    try {
      localStorage.setItem('arl_appId', this.appId);
    } catch { /* noop */ }
  }

  loadDashboard() {
    if (!this.appId) {
      this.error = 'Please select an app';
      return;
    }

    this.loading = true;
    this.error = '';
    this.infoMessage = '';

    this.persistAppId();

    // V2: Load insights
    this.api.getInsightsV2(this.appId, this.currentFilters.days).subscribe({
      next: (data: InsightsV2Response) => {
        const filteredIssues = (data.top_issues || []).filter(
          issue => issue.avg_sentiment < 0.4
        );

        // Keep ranks contiguous in the UI after client-side filtering.
        this.topIssues = filteredIssues
          .sort((a, b) => b.impact - a.impact)
          .map((issue, index) => ({
            ...issue,
            rank: index + 1,
          }));
        this.alerts = data.alerts || [];
        this.ratingTrend = data.rating_trend || [];
        this.totalReviews = data.total_reviews || 0;
        this.playstoreRating = data.playstore_rating || null;
        this.loading = false;
      },
      error: () => {
        this.error = 'Failed to load insights';
        this.loading = false;
      }
    });

    // V1: Stats for sentiment chart
    this.api.getStats(this.appId).subscribe(res => {
      this.stats = res;
      this.sentimentData = {
        positive: res?.sentiment_distribution?.positive || 0,
        negative: res?.sentiment_distribution?.negative || 0,
        neutral: res?.sentiment_distribution?.neutral || 0,
      };
    });

    // Reviews (with V2 filters)
    this.api.listReviews(
      this.appId,
      this.currentFilters.sentiment || undefined,
      50,
      0,
      undefined,
      this.currentFilters.rating || undefined,
      this.currentFilters.days || undefined,
    ).subscribe(res => {
      this.recentReviews = (res.reviews || []).map((r: any) => ({
        ...r,
        sentiment: this.deriveSentiment(r),
      }));
      this.lastRefreshed = new Date().toLocaleTimeString();
    });
  }

  onFiltersChanged(filters: FilterState) {
    this.currentFilters = filters;
    this.loadDashboard();
  }

  navigateToIssue(issueName: string) {
    this.router.navigate(['/issues', this.appId, issueName], {
      queryParams: { days: this.currentFilters.days, appId: this.appId }
    });
  }

  ingestReviews() {
    this.loading = true;
    this.api.ingestReviews(this.appId).subscribe({
      next: () => {
        this.infoMessage = 'Reviews ingested successfully';
        this.loadDashboard();
      },
      error: () => {
        this.error = 'Failed to ingest reviews';
        this.loading = false;
      }
    });
  }

  toggleReviews() {
    this.showAllReviews = !this.showAllReviews;
  }

  formatLabel(label: string): string {
    return (label || '')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  }

  getSeverityClass(severity: number): string {
    if (!severity) return 'sev-low';
    if (severity > 7) return 'sev-critical';
    if (severity > 5) return 'sev-high';
    if (severity > 3) return 'sev-medium';
    return 'sev-low';
  }

  /** Re-derive sentiment from the 0-1 sentiment_score, corrected by star rating */
  private deriveSentiment(review: any): string {
    const score = review.sentiment_score;
    const rating = review.rating;

    // Rating override: rating and sentiment must be consistent
    if (typeof rating === 'number') {
      if (rating <= 2) return 'negative';
      if (rating >= 4) {
        // 4-5 star reviews should never show as negative
        if (typeof score === 'number' && score < 0.4) return 'neutral';
        return typeof score === 'number' && score > 0.6 ? 'positive' : 'neutral';
      }
      if (rating === 3) {
        if (typeof score === 'number' && score > 0.6) return 'neutral';
      }
    }

    if (typeof score === 'number') {
      if (score < 0.4) return 'negative';
      if (score > 0.6) return 'positive';
      return 'neutral';
    }
    return review.sentiment || 'neutral';
  }
}