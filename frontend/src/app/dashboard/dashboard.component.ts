import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from '../services/api.service';

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
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css'],
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule]
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

  infoMessage = '';
  loading = false;
  error = '';
  lastRefreshed = '';
  activeTab = 'insights';

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

        // 🚫 REMOVE GENERAL + DEDUPLICATE DELIVERY
        this.insights = rawInsights
          .filter(i => {
            const category = (i.category || '').toLowerCase();
            const sub = (i.subcategory || '').toLowerCase();

            return (
              !category.includes('general') &&
              !sub.includes('general')
            );
          })
          .map(i => ({
            ...i,
            category: this.normalizeCategory(i)
          }));

        this.supportInsights = this.insights.filter(i =>
          i.category.includes('support')
        );

        this.loading = false;
      },
      error: err => {
        this.error = 'Failed to load insights';
        this.loading = false;
      }
    });

    // ✅ STATS
    this.api.getStats(this.appId).subscribe(res => this.stats = res);

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
    });

    // ✅ REVIEWS
    this.api.listReviews(this.appId, undefined, 10, 0).subscribe(res => {
      this.recentReviews = res.reviews || [];
      this.lastRefreshed = new Date().toLocaleTimeString();
    });
  }

  // 🔥 NORMALIZE CATEGORY (REMOVE DUPLICATES)
  normalizeCategory(i: Insight): string {
    const sub = (i.subcategory || '').toLowerCase();
    const desc = (i.description || '').toLowerCase();

    if (sub.includes('courier') || desc.includes('rude')) {
      return 'delivery_agent';
    }

    if (sub.includes('parcel') || desc.includes('missing')) {
      return 'delivery_order';
    }

    if (desc.includes('late') || desc.includes('delay')) {
      return 'delivery_speed';
    }

    return (i.category || '').toLowerCase();
  }

  // 🔥 MAIN EXPLANATION ENGINE
  getInsightExplanation(insight: Insight): string {
    const desc = (insight.description || '').toLowerCase();
    const cat = (insight.category || '').toLowerCase();

    // 🚚 DELIVERY AGENT
    if (cat === 'delivery_agent') {
      return `Users are reporting negative experiences with delivery agents such as rude behaviour, lack of professionalism, or poor communication. This impacts trust and overall customer satisfaction.`;
    }

    // 📦 ORDER ISSUES
    if (cat === 'delivery_order') {
      return `Users are facing issues with order accuracy like missing items, wrong deliveries, or damaged packages. This directly affects customer trust and repeat usage.`;
    }

    // ⏱ DELIVERY SPEED
    if (cat === 'delivery_speed') {
      return `Users are experiencing delays in delivery such as late arrivals or long waiting times. This is a critical issue as it directly affects user satisfaction and retention.`;
    }

    // 💥 BUGS
    if (desc.includes('crash') || desc.includes('bug')) {
      return `Users are encountering app crashes or technical bugs, leading to a broken user experience and potential drop-offs.`;
    }

    // 💳 PAYMENT
    if (desc.includes('payment')) {
      return `Users are facing issues during payment such as failed transactions or checkout friction, which directly impacts revenue.`;
    }

    // 🍽 QUALITY
    if (desc.includes('quality') || desc.includes('food')) {
      return `Users are unhappy with the quality of the product or service, which affects brand perception and repeat usage.`;
    }

    // 🛎 SUPPORT
    if (cat.includes('support')) {
      return `Users are dissatisfied with customer support responsiveness or issue resolution, leading to frustration and churn.`;
    }

    // ❌ NO GENERIC "GENERAL" ANYMORE
    return `This issue is being reported by multiple users and requires deeper analysis to identify the root cause and improve user experience.`;
  }

  // 🎨 PRIORITY COLOR
  getPriorityColor(score: number): string {
    if (score > 70) return 'critical';
    if (score > 50) return 'high';
    if (score > 30) return 'medium';
    return 'low';
  }

  // 🔄 ACTIONS
  ingestReviews() {
    this.loading = true;
    this.api.ingestReviews(this.appId).subscribe(() => this.loadDashboard());
  }

  generateInsights() {
    this.loading = true;
    this.api.generateInsights(this.appId).subscribe(() => this.loadDashboard());
  }

  refreshDashboard() {
    this.loadDashboard();
  }

  formatLabel(label: string): string {
    if (!label) return '';

    return label
      .replace(/_/g, ' ')                 // replace underscore with space
      .toLowerCase()                     // normalize
      .replace(/\b\w/g, char => char.toUpperCase()); // capitalize each word
  }
}