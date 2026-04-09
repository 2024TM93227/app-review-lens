import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService, DashboardResponse, IssueMetric } from '../services/api.service';
import { Subject, takeUntil } from 'rxjs';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  
  jobId: string = '';
  appId: string = '';
  
  loading = true;
  error: string = '';
  
  // Dashboard data - fully initialized
  totalReviews: number = 0;
  avgRating: number = 0;
  ratingChange: number = 0;
  topIssue: IssueMetric | null = null;
  issues: IssueMetric[] = [];
  sentimentDistribution: { positive: number; negative: number; neutral: number } = {
    positive: 0,
    negative: 0,
    neutral: 0
  };
  
  // Additional dashboard sections
  activeTab: string = 'overview';
  trends: any[] = [];
  recentReviews: any[] = [];
  
  // Mock data for initial UI
  monitoredApps = [
    { id: 'in.swiggy.android', name: 'Swiggy' },
    { id: 'com.application.zomato', name: 'Zomato' },
    { id: 'com.ubercab.eats', name: 'Uber Eats' }
  ];
  
  stats = {
    total_reviews: 0,
    avg_rating: 0,
    rating_change: 0
  };

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private api: ApiService
  ) {}

  ngOnInit() {
    this.route.queryParams
      .pipe(takeUntil(this.destroy$))
      .subscribe(params => {
        this.jobId = params['job'] || '';
        
        if (!this.jobId) {
          this.router.navigate(['/']);
          return;
        }

        this.loadDashboard();
      });
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadDashboard() {
    this.loading = true;
    this.error = '';
    
    this.api.getDashboard(this.jobId).subscribe({
      next: (response: DashboardResponse) => {
        this.appId = response.app_id;
        this.totalReviews = response.total_reviews;
        this.avgRating = response.avg_rating;
        this.ratingChange = response.rating_change;
        this.topIssue = response.top_issue || null;
        this.issues = response.issues || [];
        this.sentimentDistribution = response.review_sentiment_distribution || {
          positive: 0,
          negative: 0,
          neutral: 0
        };
        
        // Update stats for template
        this.stats = {
          total_reviews: this.totalReviews,
          avg_rating: this.avgRating,
          rating_change: this.ratingChange
        };
        
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load dashboard: ' + (err.error?.detail || err.message || 'Unknown error');
        this.loading = false;
      }
    });
  }

  getSeverityStyle(severity: string): string {
    switch(severity) {
      case 'critical': return 'critical';
      case 'high': return 'high';
      case 'medium': return 'medium';
      default: return 'low';
    }
  }

  getTrendArrow(trend: number): string {
    if (trend > 0) return '📈 +' + trend.toFixed(1);
    if (trend < 0) return '📉 ' + trend.toFixed(1);
    return '➡️ 0';
  }

  getSentimentPercentage(label: string): number {
    const total = this.totalReviews;
    const count = this.sentimentDistribution[label as keyof typeof this.sentimentDistribution] || 0;
    return total > 0 ? Math.round((count / total) * 100) : 0;
  }

  goBack() {
    this.router.navigate(['/']);
  }

  ingestReviews() {
    // Placeholder for ingest functionality
    console.log('Ingest reviews for', this.appId);
  }

  generateInsights() {
    // Placeholder for insights generation
    console.log('Generate insights for', this.appId);
  }

  viewIssueDetails(issueId: number) {
    // Navigate to issue deep dive
    this.router.navigate(['/issue-detail'], {
      queryParams: { job: this.jobId, issue: issueId }
    });
  }

  setActiveTab(tab: string) {
    this.activeTab = tab;
    if (tab === 'trends') {
      this.loadTrends();
    } else if (tab === 'reviews') {
      this.loadRecentReviews();
    }
  }

  loadTrends() {
    // Load trend data (placeholder)
    this.trends = [];
  }

  loadRecentReviews() {
    // Load recent reviews (placeholder)
    this.recentReviews = [];
  }
}