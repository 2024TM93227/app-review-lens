import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, throwError, timer } from 'rxjs';
import { retryWhen, mergeMap, timeout, catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';

// HTTP Retry Configuration
const RETRY_CONFIG = {
  maxRetries: 3,
  delayMs: 1000, // Initial delay in milliseconds
  backoffFactor: 2, // Exponential backoff multiplier
  timeoutMs: 30000 // 30 second timeout per request
};

// DTO Interfaces
export interface AppSearchResult {
  app_id: string;
  name: string;
  category: string;
  rating: number;
  review_count: number;
  icon_url: string;
}

export interface IngestReviewsResponse {
  job_id: string;
  status: string;
  app_ids: string[];
  created_at: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: string;
  progress: number;
  message: string;
  created_at: string;
  completed_at?: string;
}

export interface IssueMetric {
  issue_id: number;
  category: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  frequency: number;
  trend: number;
  rating_impact: number;
  is_top_issue: boolean;
}

export interface DashboardResponse {
  job_id: string;
  app_id: string;
  total_reviews: number;
  avg_rating: number;
  rating_change: number;
  top_issue: IssueMetric | null;
  issues: IssueMetric[];
  review_sentiment_distribution: { positive: number; negative: number; neutral: number };
}

export interface ComparisonResponse {
  app_a_id: string;
  app_b_id: string;
  app_a_rating: number;
  app_b_rating: number;
  aspects: Array<{ aspect: string; app_a_score: number; app_b_score: number }>;
  app_a_strengths: string[];
  app_b_weaknesses: string[];
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = environment.apiBaseUrl || 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  /**
   * Add retry logic with exponential backoff to observable
   */
  private withRetry<T>(obs: Observable<T>): Observable<T> {
    return obs.pipe(
      timeout(RETRY_CONFIG.timeoutMs),
      retryWhen(errors =>
        errors.pipe(
          mergeMap((error, index) => {
            if (index >= RETRY_CONFIG.maxRetries) {
              return throwError(() => error);
            }
            // Calculate exponential backoff: delayMs * (backoffFactor ^ attempt)
            const delayMs = RETRY_CONFIG.delayMs * Math.pow(RETRY_CONFIG.backoffFactor, index);
            console.warn(`HTTP request failed (attempt ${index + 1}/${RETRY_CONFIG.maxRetries}), retrying in ${delayMs}ms`, error);
            return timer(delayMs);
          })
        )
      ),
      catchError(error => {
        console.error('HTTP request failed after retries', error);
        return throwError(() => error);
      })
    );
  }

  // Insights endpoints
  getInsights(appId: string): Observable<any> {
    return this.withRetry(this.http.get(`${this.baseUrl}/insights/${appId}`));
  }

  generateInsights(appId: string): Observable<any> {
    return this.withRetry(this.http.post(`${this.baseUrl}/insights/generate/${appId}`, {}));
  }

  getTopIssues(appId: string, limit: number = 10): Observable<IssueMetric[]> {
    return this.withRetry(this.http.get<IssueMetric[]>(`${this.baseUrl}/insights/${appId}/top-issues?limit=${limit}`));
  }

  getAnomalies(appId: string): Observable<any> {
    return this.withRetry(this.http.get(`${this.baseUrl}/insights/${appId}/anomalies`));
  }

  getEmergingIssues(appId: string, days: number = 7): Observable<any> {
    return this.withRetry(this.http.get(`${this.baseUrl}/insights/${appId}/emerging-issues?days=${days}`));
  }

  // App Discovery endpoints
  searchApps(query: string = '', category: string = 'food_delivery', limit: number = 20): Observable<AppSearchResult[]> {
    return this.withRetry(
      this.http.get<AppSearchResult[]>(
        `${this.baseUrl}/apps/search?q=${query}&category=${category}&limit=${limit}`
      )
    );
  }

  getAppDetails(appId: string): Observable<AppSearchResult> {
    return this.withRetry(this.http.get<AppSearchResult>(`${this.baseUrl}/apps/${appId}`));
  }

  // Job Queue endpoints
  ingestReviews(appIds: string[], countries: string[] = ['IN'], languages: string[] = ['en'], maxReviews: number = 1000): Observable<IngestReviewsResponse> {
    return this.withRetry(
      this.http.post<IngestReviewsResponse>(`${this.baseUrl}/jobs/ingest`, {
        app_ids: appIds,
        countries: countries,
        languages: languages,
        max_reviews: maxReviews
      })
    );
  }

  getJobStatus(jobId: string): Observable<JobStatusResponse> {
    return this.withRetry(this.http.get<JobStatusResponse>(`${this.baseUrl}/jobs/${jobId}`));
  }

  getJobResult(jobId: string): Observable<any> {
    return this.withRetry(this.http.get(`${this.baseUrl}/jobs/${jobId}/result`));
  }

  // Analysis/Dashboard endpoints
  getDashboard(jobId: string): Observable<DashboardResponse> {
    return this.withRetry(this.http.get<DashboardResponse>(`${this.baseUrl}/analysis/${jobId}/dashboard`));
  }

  getComparison(jobId: string): Observable<ComparisonResponse> {
    return this.withRetry(this.http.get<ComparisonResponse>(`${this.baseUrl}/analysis/${jobId}/comparison`));
  }

  getIssueDetails(jobId: string, issueId: number): Observable<any> {
    return this.withRetry(this.http.get(`${this.baseUrl}/analysis/${jobId}/issues/${issueId}`));
  }

  getIssueEvidence(jobId: string, issueId: number, limit: number = 50): Observable<any> {
    return this.withRetry(this.http.get(`${this.baseUrl}/analysis/${jobId}/issues/${issueId}/evidence?limit=${limit}`));
  }

  // Health check
  healthCheck(): Observable<any> {
    return this.withRetry(this.http.get(`${this.baseUrl}/`));
  }
}
