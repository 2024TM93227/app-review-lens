import { Component, OnInit, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { ApiService } from '../../services/api.service';
import { IssueDetailResponse, IssueDetailReview } from '../../models/insights.model';
import { Chart, registerables } from 'chart.js';

Chart.register(...registerables);

const HIGHLIGHT_KEYWORDS = [
  'late', 'cold', 'crash', 'wrong', 'missing', 'slow', 'refund', 'worst',
  'terrible', 'never', 'always', 'horrible', 'disgusting', 'broken', 'error',
  'bug', 'freeze', 'rude', 'useless', 'scam', 'charged', 'failed', 'delay',
];

@Component({
  selector: 'app-issue-detail',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="issue-detail-container">
      <header class="app-header">
        <div class="app-header-box">
          <h1>App Review Lens</h1>
          <p>Issue Deep Dive</p>
        </div>
      </header>

      <div class="back-bar">
        <a [routerLink]="['/']" [queryParams]="{ appId: appId }" class="back-link">← Back to Dashboard</a>
      </div>

      <div *ngIf="loading" class="loading-spinner">
        <div class="spinner"></div>
        <p>Loading issue details...</p>
      </div>

      <div *ngIf="error" class="error-banner">❌ {{ error }}</div>

      <div *ngIf="!loading && detail" class="detail-content">

        <!-- Issue Summary -->
        <div class="summary-section">
          <h2>{{ formatName(detail.issue_name) }}</h2>
          <div class="summary-cards">
            <div class="summary-card affected">
              <div class="card-label">Affected Users</div>
              <div class="card-value">{{ detail.affected_users_pct }}%</div>
            </div>
            <div class="summary-card rating">
              <div class="card-label">Avg Rating</div>
              <div class="card-value" [ngClass]="getRatingClass(detail.avg_rating)">
                {{ detail.avg_rating | number:'1.1-1' }} ★
              </div>
            </div>
            <div class="summary-card severity">
              <div class="card-label">Avg Severity</div>
              <div class="card-value">{{ detail.avg_severity | number:'1.1-1' }}/10</div>
            </div>
            <div class="summary-card frequency">
              <div class="card-label">Mentions</div>
              <div class="card-value">{{ detail.frequency }}</div>
            </div>
          </div>

          <!-- Sentiment Breakdown -->
          <div class="breakdown-bar">
            <div class="breakdown-segment positive"
                 [style.width.%]="getBreakdownPct('positive')">
              {{ detail.sentiment_breakdown.positive }}
            </div>
            <div class="breakdown-segment neutral"
                 [style.width.%]="getBreakdownPct('neutral')">
              {{ detail.sentiment_breakdown.neutral }}
            </div>
            <div class="breakdown-segment negative"
                 [style.width.%]="getBreakdownPct('negative')">
              {{ detail.sentiment_breakdown.negative }}
            </div>
          </div>
          <div class="breakdown-legend">
            <span class="legend-item"><span class="dot positive"></span> Positive</span>
            <span class="legend-item"><span class="dot neutral"></span> Neutral</span>
            <span class="legend-item"><span class="dot negative"></span> Negative</span>
          </div>
        </div>

        <!-- Trend Chart -->
        <div class="chart-section">
          <h3>📈 Sentiment Trend</h3>
          <canvas #trendCanvas></canvas>
        </div>

        <!-- AI Insight -->
        <div class="ai-insight-box">
          <div class="ai-header">🧠 AI Insight</div>
          <p>{{ detail.ai_insight }}</p>
        </div>

        <!-- Recommendation (data-driven) -->
        <div class="recommendation-box" *ngIf="detail.recommendation">
          <div class="rec-header">🛠 Recommended Action</div>
          <div class="rec-action">{{ detail.recommendation }}</div>
          <p class="rec-detail">{{ detail.recommendation_detail }}</p>
          <div class="rec-meta">
            <span class="rec-owner">👤 Owner: {{ detail.recommendation_owner }}</span>
          </div>
          <div class="rec-complaints" *ngIf="detail.top_complaints && detail.top_complaints.length">
            <span class="rec-complaints-label">Top user complaints:</span>
            <span *ngFor="let c of detail.top_complaints" class="complaint-chip">{{ c }}</span>
          </div>
        </div>

        <!-- Reviews List -->
        <div class="reviews-section">
          <h3>📋 Reviews ({{ detail.reviews.length }})</h3>
          <div class="review-list">
            <div *ngFor="let review of detail.reviews; let i = index"
                 class="review-card"
                 [ngClass]="getSeverityClass(review.severity)">
              <div class="review-header">
                <span class="review-rating" [ngClass]="getRatingClass(review.rating)">
                  {{ review.rating }} ★
                </span>
                <span class="review-sentiment" [ngClass]="review.sentiment">
                  {{ review.sentiment }}
                </span>
                <span class="review-severity">
                  Severity: {{ review.severity | number:'1.1-1' }}
                </span>
                <span class="review-date" *ngIf="review.timestamp">
                  {{ review.timestamp | date:'mediumDate' }}
                </span>
                <span class="review-version" *ngIf="review.app_version">
                  v{{ review.app_version }}
                </span>
              </div>
              <p class="review-text" [innerHTML]="highlightKeywords(review.text)"></p>
            </div>
          </div>
        </div>
      </div>

      <footer class="app-footer">
        <div class="app-footer-box">
          <p>App Review Lens • Issue Detail View</p>
        </div>
      </footer>
    </div>
  `,
  styles: [`
    .issue-detail-container {
      padding: 100px 24px 80px;
      background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
      min-height: 100vh;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    .app-header, .app-footer {
      position: fixed; left: 0; width: 100%; text-align: center; z-index: 100;
      background: linear-gradient(135deg, #2f4fa2 0%, #1d3b7f 100%);
      color: white;
    }
    .app-header { top: 0; padding: 0.4rem 0; }
    .app-footer { bottom: 0; padding: 0.3rem 0; }
    .app-header-box, .app-footer-box { padding: 6px 24px; }
    .app-header-box h1 { margin: 0; font-size: 1.6rem; }
    .app-header-box p, .app-footer-box p { margin: 4px 0 0; color: #f3f4f9; }

    .back-bar { margin-bottom: 20px; }
    .back-link {
      color: #3498db; text-decoration: none; font-weight: 600; font-size: 0.95rem;
    }
    .back-link:hover { text-decoration: underline; }

    .loading-spinner { text-align: center; padding: 40px; background: white; border-radius: 8px; }
    .spinner {
      border: 4px solid #f3f3f3; border-top: 4px solid #3498db;
      border-radius: 50%; width: 40px; height: 40px;
      animation: spin 1s linear infinite; margin: 0 auto;
    }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    .error-banner {
      background: #e74c3c; color: white; padding: 15px; border-radius: 4px;
      margin-bottom: 20px; font-weight: 600;
    }

    .summary-section {
      background: white; padding: 24px; border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 20px;
    }
    .summary-section h2 { margin: 0 0 16px; font-size: 1.5rem; color: #2c3e50; }
    .summary-cards {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px;
      margin-bottom: 20px;
    }
    .summary-card {
      padding: 16px; border-radius: 8px; text-align: center;
      border-left: 4px solid #3498db;
    }
    .summary-card.affected { background: #ebf5fb; border-left-color: #3498db; }
    .summary-card.rating { background: #fef5e7; border-left-color: #f39c12; }
    .summary-card.severity { background: #fdedec; border-left-color: #e74c3c; }
    .summary-card.frequency { background: #eafaf1; border-left-color: #27ae60; }
    .card-label { font-size: 0.8rem; color: #7f8c8d; text-transform: uppercase; font-weight: 600; }
    .card-value { font-size: 1.8rem; font-weight: 700; color: #2c3e50; margin-top: 4px; }
    .card-value.rating-bad { color: #e74c3c; }
    .card-value.rating-ok { color: #f39c12; }
    .card-value.rating-good { color: #27ae60; }

    .breakdown-bar {
      display: flex; height: 28px; border-radius: 4px; overflow: hidden;
      margin-bottom: 8px;
    }
    .breakdown-segment {
      display: flex; align-items: center; justify-content: center;
      color: white; font-size: 0.8rem; font-weight: 600; min-width: 24px;
    }
    .breakdown-segment.positive { background: #27ae60; }
    .breakdown-segment.neutral { background: #95a5a6; }
    .breakdown-segment.negative { background: #e74c3c; }
    .breakdown-legend { display: flex; gap: 16px; font-size: 0.85rem; }
    .legend-item { display: flex; align-items: center; gap: 4px; }
    .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
    .dot.positive { background: #27ae60; }
    .dot.neutral { background: #95a5a6; }
    .dot.negative { background: #e74c3c; }

    .chart-section {
      background: white; padding: 24px; border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 20px;
    }
    .chart-section h3 { margin: 0 0 16px; color: #2c3e50; }

    .ai-insight-box {
      background: #eef7ff; border-left: 4px solid #3498db;
      padding: 20px 24px; border-radius: 8px; margin-bottom: 20px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .ai-header { font-weight: 700; font-size: 1rem; color: #2c3e50; margin-bottom: 8px; }
    .ai-insight-box p { margin: 0; color: #34495e; line-height: 1.6; }

    .recommendation-box {
      background: #f0fdf4; border-left: 4px solid #27ae60;
      padding: 20px 24px; border-radius: 8px; margin-bottom: 20px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .rec-header { font-weight: 700; font-size: 1rem; color: #2c3e50; margin-bottom: 6px; }
    .rec-action { font-size: 1.1rem; font-weight: 700; color: #27ae60; margin-bottom: 8px; }
    .rec-detail { margin: 0 0 10px; color: #34495e; line-height: 1.6; font-size: 0.92rem; }
    .rec-meta { margin-bottom: 10px; }
    .rec-owner { font-size: 0.85rem; font-weight: 600; color: #7158e2; }
    .rec-complaints { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
    .rec-complaints-label { font-size: 0.82rem; font-weight: 600; color: #7f8c8d; margin-right: 4px; }
    .complaint-chip {
      background: #fff3cd; color: #856404; font-size: 0.78rem; font-weight: 600;
      padding: 3px 10px; border-radius: 12px; border: 1px solid #ffc107;
    }

    .reviews-section { margin-bottom: 20px; }
    .reviews-section h3 { margin: 0 0 12px; color: #2c3e50; }
    .review-list { display: flex; flex-direction: column; gap: 10px; }
    .review-card {
      background: white; padding: 16px 20px; border-radius: 8px;
      border-left: 4px solid #95a5a6;
      box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    .review-card.sev-critical { border-left-color: #e74c3c; }
    .review-card.sev-high { border-left-color: #f39c12; }
    .review-card.sev-medium { border-left-color: #f1c40f; }
    .review-card.sev-low { border-left-color: #27ae60; }
    .review-header {
      display: flex; gap: 12px; flex-wrap: wrap; align-items: center;
      margin-bottom: 8px; font-size: 0.85rem;
    }
    .review-rating { font-weight: 700; }
    .review-rating.rating-bad { color: #e74c3c; }
    .review-rating.rating-ok { color: #f39c12; }
    .review-rating.rating-good { color: #27ae60; }
    .review-sentiment { font-weight: 600; text-transform: capitalize; }
    .review-sentiment.positive { color: #27ae60; }
    .review-sentiment.negative { color: #e74c3c; }
    .review-sentiment.neutral { color: #95a5a6; }
    .review-severity { color: #7f8c8d; }
    .review-date { color: #95a5a6; }
    .review-version { background: #ecf0f1; padding: 2px 8px; border-radius: 4px; color: #7f8c8d; font-size: 0.8rem; }
    .review-text { margin: 0; color: #34495e; line-height: 1.55; }
    :host ::ng-deep .keyword-highlight {
      background: #fff3cd; padding: 1px 4px; border-radius: 3px; font-weight: 600;
    }
  `]
})
export class IssueDetailComponent implements OnInit, AfterViewInit {
  @ViewChild('trendCanvas') trendCanvas!: ElementRef<HTMLCanvasElement>;

  detail: IssueDetailResponse | null = null;
  loading = true;
  error = '';
  appId = '';
  private chart: Chart | null = null;

  constructor(private route: ActivatedRoute, private api: ApiService) {}

  ngOnInit(): void {
    this.appId = this.route.snapshot.paramMap.get('appId') || '';
    const appId = this.appId;
    const issueName = this.route.snapshot.paramMap.get('issueName') || '';
    const days = +(this.route.snapshot.queryParamMap.get('days') || '30');

    this.api.getIssueDetail(appId, issueName, days).subscribe({
      next: data => {
        this.detail = data;
        this.loading = false;
        setTimeout(() => this.renderChart(), 100);
      },
      error: err => {
        this.error = err.error?.detail || 'Failed to load issue details';
        this.loading = false;
      }
    });
  }

  ngAfterViewInit(): void {}

  formatName(name: string): string {
    return (name || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  getRatingClass(rating: number): string {
    if (rating < 2) return 'rating-bad';
    if (rating < 3.5) return 'rating-ok';
    return 'rating-good';
  }

  getSeverityClass(severity: number): string {
    if (severity > 7) return 'sev-critical';
    if (severity > 5) return 'sev-high';
    if (severity > 3) return 'sev-medium';
    return 'sev-low';
  }

  getBreakdownPct(type: 'positive' | 'negative' | 'neutral'): number {
    if (!this.detail) return 0;
    const total = this.detail.sentiment_breakdown.positive
      + this.detail.sentiment_breakdown.negative
      + this.detail.sentiment_breakdown.neutral;
    if (total === 0) return 0;
    return Math.max(5, (this.detail.sentiment_breakdown[type] / total) * 100);
  }

  highlightKeywords(text: string): string {
    if (!text) return '';
    let result = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    for (const kw of HIGHLIGHT_KEYWORDS) {
      const regex = new RegExp(`\\b(${kw})\\b`, 'gi');
      result = result.replace(regex, '<span class="keyword-highlight">$1</span>');
    }
    return result;
  }

  private renderChart(): void {
    if (!this.detail?.trend_data?.length || !this.trendCanvas) return;

    if (this.chart) this.chart.destroy();

    const labels = this.detail.trend_data.map(t => t.date);
    const sentimentData = this.detail.trend_data.map(t => t.avg_sentiment_score);
    const negCounts = this.detail.trend_data.map(t => t.negative_count);

    this.chart = new Chart(this.trendCanvas.nativeElement, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Avg Sentiment',
            data: sentimentData,
            borderColor: '#3498db',
            backgroundColor: 'rgba(52, 152, 219, 0.1)',
            fill: true,
            tension: 0.3,
            yAxisID: 'y',
          },
          {
            label: 'Negative Count',
            data: negCounts,
            borderColor: '#e74c3c',
            backgroundColor: 'rgba(231, 76, 60, 0.1)',
            fill: true,
            tension: 0.3,
            yAxisID: 'y1',
          }
        ]
      },
      options: {
        responsive: true,
        interaction: { intersect: false, mode: 'index' },
        scales: {
          y: { position: 'left', title: { display: true, text: 'Sentiment' }, min: 0, max: 1 },
          y1: { position: 'right', title: { display: true, text: 'Negative Count' }, grid: { drawOnChartArea: false } },
        }
      }
    });
  }
}
