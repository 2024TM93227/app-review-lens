import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { HTTP_INTERCEPTORS, HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { HttpErrorInterceptor } from './http-error.interceptor';

describe('HttpErrorInterceptor', () => {
  let httpMock: HttpTestingController;
  let httpClient: HttpClient;
  let routerSpy: jasmine.SpyObj<Router>;
  const testUrl = 'http://localhost:8001/test';

  beforeEach(() => {
    routerSpy = jasmine.createSpyObj('Router', ['navigate']);

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        { provide: Router, useValue: routerSpy },
        { provide: HTTP_INTERCEPTORS, useClass: HttpErrorInterceptor, multi: true }
      ]
    });

    httpMock = TestBed.inject(HttpTestingController);
    httpClient = TestBed.inject(HttpClient);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('Error Handling', () => {
    it('should handle 401 Unauthorized and redirect to login', (done) => {
      httpClient.get(testUrl).subscribe({
        next: () => fail('should have failed with 401 error'),
        error: (error: any) => {
          expect(error.status).toBe(401);
          expect(routerSpy.navigate).toHaveBeenCalledWith(['/login']);
          done();
        }
      });

      const req = httpMock.expectOne(testUrl);
      req.flush('Unauthorized', { status: 401, statusText: 'Unauthorized' });
    });

    it('should handle 403 Forbidden with access denied message', (done) => {
      httpClient.get(testUrl).subscribe({
        next: () => fail('should have failed with 403 error'),
        error: (error: any) => {
          expect(error.status).toBe(403);
          expect(error.message).toContain('Access denied');
          done();
        }
      });

      const req = httpMock.expectOne(testUrl);
      req.flush('Forbidden', { status: 403, statusText: 'Forbidden' });
    });

    it('should handle 404 Not Found', (done) => {
      httpClient.get(testUrl).subscribe({
        next: () => fail('should have failed with 404 error'),
        error: (error: any) => {
          expect(error.status).toBe(404);
          expect(error.message).toContain('Resource not found');
          done();
        }
      });

      const req = httpMock.expectOne(testUrl);
      req.flush('Not Found', { status: 404, statusText: 'Not Found' });
    });

    it('should handle 500 Internal Server Error', (done) => {
      httpClient.get(testUrl).subscribe({
        next: () => fail('should have failed with 500 error'),
        error: (error: any) => {
          expect(error.status).toBe(500);
          expect(error.message).toContain('Server Error');
          done();
        }
      });

      const req = httpMock.expectOne(testUrl);
      req.flush('Internal Server Error', { status: 500, statusText: 'Internal Server Error' });
    });

    it('should extract detail from error response', (done) => {
      const errorDetail = 'Job not found';
      
      httpClient.get(testUrl).subscribe({
        next: () => fail('should have failed'),
        error: (error: any) => {
          expect(error.message).toContain(errorDetail);
          done();
        }
      });

      const req = httpMock.expectOne(testUrl);
      req.flush({ detail: errorDetail }, { status: 400, statusText: 'Bad Request' });
    });
  });

  describe('Successful Requests', () => {
    it('should pass through successful responses', (done) => {
      const mockData = { status: 'ok', data: 'test' };

      httpClient.get(testUrl).subscribe({
        next: (response: any) => {
          expect(response).toEqual(mockData);
          done();
        },
        error: () => fail('should not error')
      });

      const req = httpMock.expectOne(testUrl);
      req.flush(mockData);
    });
  });
});
