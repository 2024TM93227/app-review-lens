import { Component, OnInit } from '@angular/core';
import { CommonModule, KeyValue } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from '../services/api.service';
import { SentimentChartComponent } from '../components/sentiment-chart.component';

interface Insight {
  id: number;
  category: string;
  subcategory: string;
  description: string;
  frequency: number;
  priority_score: number;
  rank: number;
  sentiment_score: number;
  status: string;
  last_seen?: string;
}

interface AspectSentiment {
  [key: string]: {
    positive: number;
    negative: number;
    neutral: number;
    total: number;
    positive_width?: number;
    negative_width?: number;
    neutral_width?: number;
  };
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css'],
  imports: [CommonModule, FormsModule, RouterModule, SentimentChartComponent]
})
export class DashboardComponent implements OnInit {

  monitoredApps = [
    { name: 'Swiggy', id: 'in.swiggy.android' },
    { name: 'Zomato', id: 'com.application.zomato' },
    { name: 'Uber Eats', id: 'com.ubercab.eats' },
    { name: 'Swiggy Instamart', id: 'in.swiggy.android.instamart' }
  ];

  appId: string = this.monitoredApps[0].id;

  insights: Insight[] = [];
  aspectsSentiment: AspectSentiment = {};

  stats: any = {};
  trends: any[] = [];
  recentReviews: any[] = [];
  supportInsights: Insight[] = [];

  loading: boolean = false;
  error: string = '';
  infoMessage: string = '';
  lastRefreshed: string = '';
  activeTab: string = 'insights';

  sentimentData = {
    positive: 0,
    negative: 0,
    neutral: 0
  };

  showAllReviews: boolean = false;

  // 🔥 NEW METRICS
  avgSentimentScore: number = 0;
  confidenceScore: number = 0;
  trendDirection: string = 'Stable ➖';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.loadDashboard();
  }

  loadDashboard() {
    if (!this.appId) {
      this.error = 'Please select an app';
      return;
    }

    this.loading = true;
    this.error = '';
    this.infoMessage = '';

    // ✅ INSIGHTS
    this.api.getInsights(this.appId).subscribe({
      next: data => {
        const rawInsights = data.insights || [];

        this.insights = rawInsights
          .filter((i: Insight) => {
            const category = (i.category || '').toLowerCase();
            const sub = (i.subcategory || '').toLowerCase();

            return !category.includes('general') && !sub.includes('general');
          })
          .map((i: Insight) => ({
            ...i,
            category: this.normalizeCategory(i)
          }));

        this.supportInsights = this.insights.filter(i =>
          i.category.includes('support')
        );

        this.loading = false;
      },
      error: () => {
        this.error = 'Failed to load insights';
        this.loading = false;
      }
    });

    // ✅ STATS + AVG SCORE
    this.api.getStats(this.appId).subscribe(res => {
      this.stats = res;

      const pos = res?.sentiment_distribution?.positive || 0;
      const neg = res?.sentiment_distribution?.negative || 0;
      const neu = res?.sentiment_distribution?.neutral || 0;

      const total = pos + neg + neu;

      const score = (pos * 1 + neu * 0.5 + neg * 0);

      this.avgSentimentScore = total ? score / total : 0;

      this.sentimentData = {
        positive: pos,
        negative: neg,
        neutral: neu
      };
    });

    // ✅ ASPECTS
    this.api.getAspects(this.appId).subscribe(res => {
      this.aspectsSentiment = res.aspects || {};

      Object.keys(this.aspectsSentiment).forEach(k => {
        const v = this.aspectsSentiment[k];
        const max = Math.max(v.positive, v.negative, v.neutral, 1);

        v.positive_width = (v.positive / max) * 100;
        v.negative_width = (v.negative / max) * 100;
        v.neutral_width = (v.neutral / max) * 100;
      });
    });

    // ✅ TRENDS
    this.api.getTrends(this.appId).subscribe(res => {
      this.trends = res.trend_data || [];

      if (this.trends.length >= 2) {
        const latest = this.trends[this.trends.length - 1].avg_sentiment_score;
        const previous = this.trends[this.trends.length - 2].avg_sentiment_score;

        if (latest > previous + 0.05) {
          this.trendDirection = 'Improving 📈';
        } else if (latest < previous - 0.05) {
          this.trendDirection = 'Declining 📉';
        } else {
          this.trendDirection = 'Stable ➖';
        }
      }
    });

    // ✅ REVIEWS
    this.api.listReviews(this.appId, undefined, 50, 0).subscribe(res => {
      this.recentReviews = res.reviews || [];
      this.lastRefreshed = new Date().toLocaleTimeString();
    });

    // ✅ CONFIDENCE (delay to ensure stats loaded)
    setTimeout(() => {
      this.calculateConfidence();
    }, 500);
  }

  // 🔥 CONFIDENCE SCORE
  calculateConfidence() {
    const total = this.stats?.total_reviews || 0;

    if (total === 0) {
      this.confidenceScore = 0;
      return;
    }

    const variance = Math.abs(
      (this.sentimentData.positive || 0) -
      (this.sentimentData.negative || 0)
    );

    const normalizedVariance = variance / total;

    this.confidenceScore = Math.min(
      100,
      Math.round((total / 50) * 50 + (1 - normalizedVariance) * 50)
    );
  }

  // 🔥 CATEGORY NORMALIZATION
  normalizeCategory(i: Insight): string {
    const sub = (i.subcategory || '').toLowerCase();
    const desc = (i.description || '').toLowerCase();

    if (sub.includes('courier') || desc.includes('rude')) return 'delivery_agent';
    if (sub.includes('parcel') || desc.includes('missing')) return 'delivery_order';
    if (desc.includes('late') || desc.includes('delay')) return 'delivery_speed';

    return (i.category || '').toLowerCase();
  }

  // 🔥 EXPLANATION
  getInsightExplanation(insight: Insight): string {
    const desc = (insight.description || '').toLowerCase();
    const cat = (insight.category || '').toLowerCase();

    if (cat === 'delivery_agent') return 'Delivery agent behavior affecting trust.';
    if (cat === 'delivery_order') return 'Incorrect/missing orders impacting reliability.';
    if (cat === 'delivery_speed') return 'Delivery delays hurting satisfaction.';
    if (desc.includes('crash')) return 'App crashes degrade experience.';
    if (desc.includes('payment')) return 'Payment issues affect revenue.';
    if (cat.includes('support')) return 'Support issues causing frustration.';

    return 'Recurring issue needing investigation.';
  }

  // 🎨 PRIORITY
  getPriorityColor(score: number): string {
    if (score > 70) return 'critical';
    if (score > 50) return 'high';
    if (score > 30) return 'medium';
    return 'low';
  }

  // 🔄 ACTIONS
  ingestReviews() {
    this.loading = true;
    this.api.ingestReviews(this.appId).subscribe(() => {
      this.infoMessage = 'Reviews ingested successfully';
      this.loadDashboard();
    });
  }

  generateInsights() {
    this.loading = true;
    this.api.generateInsights(this.appId).subscribe(() => {
      this.infoMessage = 'Insights generated successfully';
      this.loadDashboard();
    });
  }

  toggleReviews() {
    this.showAllReviews = !this.showAllReviews;
  }

  // 🧠 LABEL FORMAT
  formatLabel(label: string): string {
    return label
      ?.replace(/_/g, ' ')
      .toLowerCase()
      .replace(/\b\w/g, c => c.toUpperCase());
  }

  trackByKey(index: number, item: KeyValue<string, any>) {
    return item.key;
  }
}