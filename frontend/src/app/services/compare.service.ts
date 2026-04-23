import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';

@Injectable({ providedIn: 'root' })
export class CompareService {
  private base = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  compareApps(apps: string[]) {
    return this.http.post<any>(`${this.base}/compare`, { apps });
  }

  compareSentiment(apps: string[]) {
    let params = new HttpParams();
    apps.forEach(app => {
      params = params.append('apps', app);
    });
    return this.http.get<any>(`${this.base}/compare/sentiment`, { params });
  }

  compareAspects(apps: string[]) {
    return this.http.post<any>(`${this.base}/compare/aspects`, { apps });
  }

  ingestReviews(appId: string, country: string = 'in', lang: string = 'en', count: number = 100) {
    return this.http.post<any>(`${this.base}/reviews/ingest/${appId}?country=${country}&lang=${lang}&count=${count}`, {});
  }

  compareIssues(apps: string[]) {
    let params = new HttpParams();
    apps.forEach(app => {
      params = params.append('apps', app);
    });
    return this.http.get<any>(`${this.base}/compare/issues`, { params });
  }

  featureGap(primaryApp: string, competitors: string[]) {
    let params = new HttpParams().set('primary_app', primaryApp);
    competitors.forEach(app => {
      params = params.append('competitor_apps', app);
    });
    return this.http.get<any>(`${this.base}/compare/feature-gap`, { params });
  }

  getTrends(appId: string, days: number = 30) {
    return this.http.get<any>(`${this.base}/reviews/app/${appId}/trends?days=${days}`);
  }

  listReviews(appId: string, days: number = 30, limit: number = 100) {
    return this.http.get<any>(`${this.base}/reviews/app/${appId}/list?days=${days}&limit=${limit}`);
  }
}
