import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService, IngestReviewsResponse, JobStatusResponse } from '../services/api.service';
import { Subject, timer } from 'rxjs';
import { takeUntil, switchMap } from 'rxjs/operators';

@Component({
  selector: 'app-ingestion',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ingestion.component.html',
  styleUrls: ['./ingestion.component.scss']
})
export class IngestionComponent implements OnInit, OnDestroy {
  appA: string = '';
  appB: string = '';
  jobId: string = '';
  progress: number = 0;
  status: string = 'Queued';
  message: string = 'Preparing to ingest reviews...';
  loading = false; // Do not start ingestion automatically; wait for user click
  error = '';
  maxReviews = 200; // default lower value for faster fetch & analysis
  
  private destroy$ = new Subject<void>();
  private webSocket: WebSocket | null = null;
  private pollFallbackInterval = 5000; // Fallback to polling every 5 seconds if WebSocket fails
  private maxWaitTime = 600000; // 10 minutes maximum wait time
  private startTime: number = 0;

  steps = [
    { name: 'Queuing', icon: '📋' },
    { name: 'Collecting Reviews', icon: '🔍' },
    { name: 'Analysing Feedback', icon: '🧠' },
    { name: 'Detecting Issues', icon: '⚠️' }
  ];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private api: ApiService
  ) {}

  ngOnInit() {
    // Get app IDs from query params
    this.route.queryParams.subscribe(params => {
      this.appA = params['app'] || params['appA'] || '';
      this.appB = params['appB'] || '';

      if (!this.appA) {
        this.router.navigate(['/']);
        return;
      }

      // Wait for user to click "Start Ingestion" to begin fetching and analysis
    });
  }

  startIngestion() {
    const app_ids = this.appB ? [this.appA, this.appB] : [this.appA];

    this.loading = true;
    this.message = 'Queuing ingestion job...';

    this.api.ingestReviews(app_ids, ['IN'], ['en'], this.maxReviews).subscribe({
      next: (response: IngestReviewsResponse) => {
        this.jobId = response.job_id;
        this.startTime = Date.now();
        // Server-side WebSocket was disabled; use polling for status
        this.fallbackToPolling();
      },
      error: (err) => {
        this.error = 'Failed to start ingestion: ' + (err.error?.detail || err.message);
        this.loading = false;
      }
    });
  }

  connectWebSocket() {
    // WebSocket connection removed — server uses polling. Keep method placeholder.
  }

  private handleWebSocketMessage(message: string) {
    try {
      const data = JSON.parse(message);
      
      if (data.event === 'progress') {
        this.status = data.status || this.status;
        this.progress = data.progress || this.progress;
        this.message = data.message || this.message;

        if (this.status === 'completed') {
          this.handleCompletion();
        } else if (this.status === 'failed' || this.status === 'cancelled') {
          this.error = `Ingestion ${this.status}: ${data.message}`;
          this.loading = false;
          this.closeWebSocket();
        }
      }

      // Check for timeout
      const elapsedTime = Date.now() - this.startTime;
      if (elapsedTime > this.maxWaitTime) {
        this.error = `Ingestion timeout: Operation exceeded ${this.maxWaitTime / 1000 / 60} minutes`;
        this.loading = false;
        this.closeWebSocket();
      }
    } catch (e) {
      console.warn('Failed to parse WebSocket message', message, e);
    }
  }

  private fallbackToPolling() {
    console.log('Falling back to HTTP polling for job status');
    
    timer(this.pollFallbackInterval, this.pollFallbackInterval)
      .pipe(
        switchMap(() => this.api.getJobStatus(this.jobId)),
        takeUntil(this.destroy$)
      )
      .subscribe({
        next: (response: JobStatusResponse) => {
          this.status = response.status;
          this.progress = response.progress;
          this.message = response.message;

          // Check for timeout
          const elapsedTime = Date.now() - this.startTime;
          if (elapsedTime > this.maxWaitTime) {
            this.error = `Ingestion timeout: Operation exceeded ${this.maxWaitTime / 1000 / 60} minutes`;
            this.loading = false;
            this.closeWebSocket();
            return;
          }

          if (response.status === 'completed') {
            this.handleCompletion();
          } else if (response.status === 'failed' || response.status === 'cancelled') {
            this.error = `Ingestion ${response.status}: ${response.message}`;
            this.loading = false;
            this.closeWebSocket();
          }
        },
        error: (err) => {
          console.warn('Polling failed', err);
          this.error = 'Error polling job status: ' + (err.error?.detail || err.message);
          this.loading = false;
        }
      });
  }

  private handleCompletion() {
    this.loading = false;
    this.closeWebSocket();
    
    // Navigate to dashboard after a short delay for UI update
    setTimeout(() => {
      this.router.navigate(['/dashboard'], {
        queryParams: { job: this.jobId }
      });
    }, 1500);
  }

  private closeWebSocket() {
    if (this.webSocket) {
      if (this.webSocket.readyState === WebSocket.OPEN) {
        this.webSocket.close();
      }
      this.webSocket = null;
    }
  }

  getCurrentStep(): number {
    const progressPercentPerStep = 100 / this.steps.length;
    return Math.floor(this.progress / progressPercentPerStep);
  }

  ngOnDestroy() {
    this.closeWebSocket();
    this.destroy$.next();
    this.destroy$.complete();
  }
}
