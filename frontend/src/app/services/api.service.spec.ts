import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { 
  ApiService, 
  DashboardResponse, 
  JobStatusResponse,
  IngestReviewsResponse 
} from './api.service';

describe('ApiService', () => {
  let service: ApiService;
  let httpMock: HttpTestingController;
  const baseUrl = 'http://localhost:8001';

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ApiService]
    });

    service = TestBed.inject(ApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('Job Queue Endpoints', () => {
    it('should ingest reviews and return job', () => {
      const appIds = ['in.swiggy.android', 'com.application.zomato'];
      const mockResponse: IngestReviewsResponse = {
        job_id: 'job-123',
        status: 'queued',
        app_ids: appIds,
        created_at: new Date().toISOString()
      };

      service.ingestReviews(appIds).subscribe(response => {
        expect(response).toEqual(mockResponse);
        expect(response.status).toBe('queued');
      });

      const req = httpMock.expectOne(`${baseUrl}/jobs/ingest`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body.app_ids).toEqual(appIds);
      req.flush(mockResponse);
    });

    it('should get job status by ID', () => {
      const jobId = 'job-123';
      const mockResponse: JobStatusResponse = {
        job_id: jobId,
        status: 'processing',
        progress: 50,
        message: 'Ingesting reviews...',
        created_at: new Date().toISOString()
      };

      service.getJobStatus(jobId).subscribe(response => {
        expect(response.job_id).toBe(jobId);
        expect(response.progress).toBe(50);
      });

      const req = httpMock.expectOne(`${baseUrl}/jobs/${jobId}`);
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });
  });

  describe('Dashboard Endpoints', () => {
    it('should get dashboard data', () => {
      const jobId = 'job-123';
      const mockResponse: DashboardResponse = {
        job_id: jobId,
        app_id: 'in.swiggy.android',
        total_reviews: 1000,
        avg_rating: 4.2,
        rating_change: 0.3,
        top_issue: {
          issue_id: 1,
          category: 'Delivery',
          severity: 'critical',
          frequency: 250,
          trend: 0.15,
          rating_impact: -0.5,
          is_top_issue: true
        },
        issues: [],
        review_sentiment_distribution: {
          positive: 600,
          negative: 300,
          neutral: 100
        }
      };

      service.getDashboard(jobId).subscribe(response => {
        expect(response.job_id).toBe(jobId);
        expect(response.total_reviews).toBe(1000);
        expect(response.top_issue?.is_top_issue).toBe(true);
      });

      const req = httpMock.expectOne(`${baseUrl}/analysis/${jobId}/dashboard`);
      req.flush(mockResponse);
    });

    it('should handle 404 when job not found', () => {
      const jobId = 'invalid-job';

      service.getDashboard(jobId).subscribe({
        next: () => fail('should fail'),
        error: (error: any) => {
          expect(error.status).toBe(404);
        }
      });

      const req = httpMock.expectOne(`${baseUrl}/analysis/${jobId}/dashboard`);
      req.flush(
        { detail: 'Job not found' },
        { status: 404, statusText: 'Not Found' }
      );
    });
  });

  describe('App Discovery', () => {
    it('should search apps', () => {
      const mockApps = [
        { app_id: 'in.swiggy.android', name: 'Swiggy', category: 'food_delivery', rating: 4.2, review_count: 2000000, icon_url: 'https://...' },
        { app_id: 'com.application.zomato', name: 'Zomato', category: 'food_delivery', rating: 4.3, review_count: 1800000, icon_url: 'https://...' }
      ];

      service.searchApps('swiggy').subscribe(apps => {
        expect(apps.length).toBe(2);
        expect(apps[0].name).toBe('Swiggy');
      });

      const req = httpMock.expectOne(r => r.url.includes('/apps/search'));
      expect(req.request.method).toBe('GET');
      req.flush(mockApps);
    });
  });
});
