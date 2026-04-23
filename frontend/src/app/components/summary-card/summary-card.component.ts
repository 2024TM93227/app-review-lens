import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TopIssue, RatingTrendPoint } from '../../models/insights.model';

@Component({
  selector: 'app-summary-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="summary-cards">
      <div class="summary-card">
        <div class="card-icon">⭐</div>
        <div class="card-body">
          <div class="card-label">Current Rating</div>
          <div class="card-value" [ngClass]="getRatingColor()">
            {{ currentRating | number:'1.1-1' }}
          </div>
        </div>
      </div>

      <div class="summary-card">
        <div class="card-icon" [ngClass]="trendClass">
          {{ trendIcon }}
        </div>
        <div class="card-body">
          <div class="card-label">Overall Trend</div>
          <div class="card-value" [ngClass]="trendClass">{{ trendLabel }}</div>
        </div>
      </div>

      <div class="summary-card">
        <div class="card-icon">📊</div>
        <div class="card-body">
          <div class="card-label">Total Reviews</div>
          <div class="card-value">{{ totalReviews }}</div>
        </div>
      </div>

      <div class="summary-card top-issue-card" *ngIf="topIssue">
        <div class="card-icon">🔥</div>
        <div class="card-body">
          <div class="card-label">Top Issue</div>
          <div class="card-value issue-value">{{ formatName(topIssue.name) }}</div>
          <div class="card-sub">Impact: {{ topIssue.impact }} · {{ topIssue.affected_users }}% users</div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .summary-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .summary-card {
      background: white;
      padding: 20px;
      border-radius: 10px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.08);
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .card-icon { font-size: 2rem; }
    .card-body { flex: 1; }
    .card-label {
      font-size: 0.8rem;
      color: #7f8c8d;
      text-transform: uppercase;
      font-weight: 600;
      margin-bottom: 4px;
    }
    .card-value {
      font-size: 1.6rem;
      font-weight: 700;
      color: #2c3e50;
    }
    .card-value.issue-value { font-size: 1.1rem; }
    .card-sub { font-size: 0.8rem; color: #95a5a6; margin-top: 2px; }
    .card-value.rating-good, .card-icon.trend-up { color: #27ae60; }
    .card-value.rating-ok, .card-icon.trend-stable { color: #f39c12; }
    .card-value.rating-bad, .card-icon.trend-down { color: #e74c3c; }
    .trend-up { color: #27ae60; }
    .trend-stable { color: #f39c12; }
    .trend-down { color: #e74c3c; }
    .top-issue-card { border-left: 4px solid #e74c3c; }
  `]
})
export class SummaryCardComponent {
  @Input() totalReviews = 0;
  @Input() ratingTrend: RatingTrendPoint[] = [];
  @Input() topIssues: TopIssue[] = [];
  @Input() topIssue: TopIssue | null = null;
  @Input() playstoreRating: number | null = null;

  get currentRating(): number {
    // Use actual Play Store rating if available, otherwise fall back to trend average
    if (this.playstoreRating != null) return this.playstoreRating;
    if (this.ratingTrend.length === 0) return 0;
    return this.ratingTrend[this.ratingTrend.length - 1].avg_rating;
  }

  get trendIcon(): string {
    const dir = this.trendDirection;
    if (dir === 'up') return '📈';
    if (dir === 'down') return '📉';
    return '➡️';
  }

  get trendLabel(): string {
    const dir = this.trendDirection;
    if (dir === 'up') return 'Improving';
    if (dir === 'down') return 'Declining';
    return 'Stable';
  }

  get trendClass(): string {
    const dir = this.trendDirection;
    if (dir === 'up') return 'trend-up';
    if (dir === 'down') return 'trend-down';
    return 'trend-stable';
  }

  private get trendDirection(): string {
    // Prefer issue-level direction because it reflects complaint movement directly.
    if (this.topIssues.length) {
      const issueWindow = this.topIssues.slice(0, 5);
      const totalWeight = issueWindow.reduce((sum, issue) => sum + Math.max(1, issue.impact || 0), 0);

      if (totalWeight > 0) {
        const weightedDirection = issueWindow.reduce((sum, issue) => {
          const weight = Math.max(1, issue.impact || 0);
          const direction = issue.trend === 'down' ? 1 : issue.trend === 'up' ? -1 : 0;
          return sum + (direction * weight);
        }, 0);

        const score = weightedDirection / totalWeight;
        if (score >= 0.2) return 'up';
        if (score <= -0.2) return 'down';
      }
    }

    // Fallback to rating movement when issue trend signal is weak.
    if (this.ratingTrend.length < 2) return 'stable';
    const recent = this.ratingTrend[this.ratingTrend.length - 1].avg_rating;
    const prev = this.ratingTrend[this.ratingTrend.length - 2].avg_rating;
    if (recent > prev + 0.1) return 'up';
    if (recent < prev - 0.1) return 'down';
    return 'stable';
  }

  getRatingColor(): string {
    const r = this.currentRating;
    if (r >= 4) return 'rating-good';
    if (r >= 3) return 'rating-ok';
    return 'rating-bad';
  }

  formatName(name: string): string {
    return (name || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }
}
