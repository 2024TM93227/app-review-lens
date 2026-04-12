import { Component, Input, ViewChild, ElementRef, OnChanges, SimpleChanges, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Chart, registerables } from 'chart.js';
import { RatingTrendPoint } from '../../models/insights.model';
import { TopIssue } from '../../models/insights.model';

Chart.register(...registerables);

@Component({
  selector: 'app-charts',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="charts-row">
      <div class="chart-card">
        <h3>📈 Rating Trend</h3>
        <canvas #ratingCanvas></canvas>
      </div>
      <div class="chart-card">
        <h3>📊 Issue Distribution</h3>
        <canvas #issueCanvas></canvas>
      </div>
    </div>
  `,
  styles: [`
    .charts-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      margin-bottom: 24px;
    }
    .chart-card {
      background: white;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .chart-card h3 { margin: 0 0 12px; color: #2c3e50; font-size: 1.1rem; }
    @media (max-width: 768px) {
      .charts-row { grid-template-columns: 1fr; }
    }
  `]
})
export class ChartsComponent implements OnChanges, AfterViewInit {
  @Input() ratingTrend: RatingTrendPoint[] = [];
  @Input() issues: TopIssue[] = [];

  @ViewChild('ratingCanvas') ratingCanvas!: ElementRef<HTMLCanvasElement>;
  @ViewChild('issueCanvas') issueCanvas!: ElementRef<HTMLCanvasElement>;

  private ratingChart: Chart | null = null;
  private issueChart: Chart | null = null;
  private viewReady = false;

  ngAfterViewInit(): void {
    this.viewReady = true;
    this.renderCharts();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (this.viewReady) {
      this.renderCharts();
    }
  }

  private renderCharts(): void {
    this.renderRatingChart();
    this.renderIssueChart();
  }

  private renderRatingChart(): void {
    if (!this.ratingCanvas || !this.ratingTrend.length) return;
    if (this.ratingChart) this.ratingChart.destroy();

    const labels = this.ratingTrend.map(t => t.date);
    const data = this.ratingTrend.map(t => t.avg_rating);

    this.ratingChart = new Chart(this.ratingCanvas.nativeElement, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Avg Rating',
          data,
          borderColor: '#3498db',
          backgroundColor: 'rgba(52, 152, 219, 0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 3,
          pointBackgroundColor: '#3498db',
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { min: 1, max: 5, title: { display: true, text: 'Rating' } },
        }
      }
    });
  }

  private renderIssueChart(): void {
    if (!this.issueCanvas || !this.issues.length) return;
    if (this.issueChart) this.issueChart.destroy();

    const labels = this.issues.map(i => this.formatName(i.name));
    const impacts = this.issues.map(i => i.impact);
    const colors = this.issues.map(i => {
      if (i.impact > 70) return '#e74c3c';
      if (i.impact > 50) return '#f39c12';
      if (i.impact > 30) return '#f1c40f';
      return '#27ae60';
    });

    this.issueChart = new Chart(this.issueCanvas.nativeElement, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Impact Score',
          data: impacts,
          backgroundColor: colors,
          borderRadius: 4,
        }]
      },
      options: {
        responsive: true,
        indexAxis: 'y',
        plugins: { legend: { display: false } },
        scales: {
          x: { min: 0, max: 100, title: { display: true, text: 'Impact' } },
        }
      }
    });
  }

  private formatName(name: string): string {
    return (name || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }
}
