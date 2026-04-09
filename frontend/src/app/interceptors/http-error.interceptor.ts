import { Injectable } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor,
  HttpErrorResponse
} from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { Router } from '@angular/router';

@Injectable()
export class HttpErrorInterceptor implements HttpInterceptor {
  constructor(private router: Router) {}

  intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    return next.handle(request).pipe(
      catchError((error: HttpErrorResponse) => {
        let errorMessage = 'An error occurred';

        if (error.error instanceof ErrorEvent) {
          // Client-side error
          errorMessage = `Client Error: ${error.error.message}`;
          console.error(errorMessage);
        } else {
          // Server-side error
          errorMessage = error.error?.detail || error.statusText || 'Server error';
          
          switch (error.status) {
            case 401:
              // Unauthorized - redirect to login
              console.warn('Unauthorized: Redirecting to login');
              this.router.navigate(['/login']);
              break;
            case 403:
              // Forbidden - access denied
              errorMessage = 'Access denied: You do not have permission to perform this action';
              console.warn(errorMessage);
              break;
            case 404:
              // Not found
              errorMessage = 'Resource not found: ' + errorMessage;
              console.warn(errorMessage);
              break;
            case 500:
            case 502:
            case 503:
            case 504:
              // Server errors
              errorMessage = `Server Error (${error.status}): Please try again later`;
              console.error(`Server error: ${error.status} - ${error.statusText}`);
              break;
            default:
              console.warn(`Error: ${error.status} - ${errorMessage}`);
          }
        }

        return throwError(() => ({
          status: error.status,
          message: errorMessage,
          details: error.error
        }));
      })
    );
  }
}
