import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = environment.apiBaseUrl || 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  // Insights endpoints
  getInsights(appId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/insights/${appId}`);
  }

  generateInsights(appId: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/insights/generate/${appId}`, {});
  }

  getTopIssues(appId: string, limit: number = 10): Observable<any> {
    return this.http.get(`${this.baseUrl}/insights/${appId}/top-issues?limit=${limit}`);
  }

  getAnomalies(appId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/insights/${appId}/anomalies`);
  }

  getEmergingIssues(appId: string, days: number = 7): Observable<any> {
    return this.http.get(`${this.baseUrl}/insights/${appId}/emerging-issues?days=${days}`);
  }

  // Reviews endpoints
  ingestReviews(appId: string, country: string = 'us', lang: string = 'en', count: number = 100): Observable<any> {
    return this.http.post(
      `${this.baseUrl}/reviews/ingest/${appId}?country=${country}&lang=${lang}&count=${count}`,
      {}
    );
  }

  listReviews(appId: string, sentiment?: string, limit: number = 50, offset: number = 0): Observable<any> {
    let url = `${this.baseUrl}/reviews/app/${appId}/list?limit=${limit}&offset=${offset}`;
    if (sentiment) {
      url += `&sentiment=${sentiment}`;
    }
    return this.http.get(url);
  }

  getStats(appId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/reviews/app/${appId}/stats`);
  }

  getTrends(appId: string, days: number = 30): Observable<any> {
    return this.http.get(`${this.baseUrl}/reviews/app/${appId}/trends?days=${days}`);
  }

  getAspects(appId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/reviews/app/${appId}/aspects`);
  }

  // Comparison endpoints
  compareAspects(apps: string[]): Observable<any> {
    return this.http.post(`${this.baseUrl}/compare/aspects`, { apps });
  }

  compareSentiment(apps: string[]): Observable<any> {
    return this.http.get(
      `${this.baseUrl}/compare/sentiment?apps=${apps.join(',')}`
    );
  }

  compareIssues(apps: string[], topN: number = 5): Observable<any> {
    return this.http.get(
      `${this.baseUrl}/compare/issues?apps=${apps.join(',')}&top_n=${topN}`
    );
  }

  identifyFeatureGaps(primaryApp: string, competitors: string[]): Observable<any> {
    return this.http.get(
      `${this.baseUrl}/compare/feature-gap?primary_app=${primaryApp}&competitor_apps=${competitors.join(',')}`
    );
  }

  // Health check
  healthCheck(): Observable<any> {
    return this.http.get(`${this.baseUrl}/`);
  }
}
