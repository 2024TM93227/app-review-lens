import { Component, OnInit, ViewChild, ElementRef, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Chart, ChartConfiguration, registerables } from 'chart.js';
import { TopIssue } from '../models/insights.model';

Chart.register(...registerables);

@Component({
  selector: 'app-issue-impact-chart',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="issue-impact-container">
      <!-- Bar Chart -->
      <div class="chart-card">
        <h3>Issue Impact Scores</h3>
        <canvas #barCanvas class="chart"></canvas>
      </div>

      <!-- Issue Stats -->
      <div class="issue-stats" *ngIf="issues && issues.length > 0">
        <div *ngFor="let issue of issues | slice:0:5" class="stat-card">
          <div class="stat-header">
            <h4>{{ formatLabel(issue.name) }}</h4>
            <span class="impact-badge" [ngClass]="getImpactClass(issue.impact)">
              {{ issue.impact }}
            </span>
          </div>
          <div class="stat-details">
            <div class="detail">
              <span class="label">Affected Users:</span>
              <span class="value">{{ issue.affected_users }}%</span>
            </div>
            <div class="detail">
              <span class="label">Frequency:</span>
              <span class="value">{{ issue.frequency }} mentions</span>
            </div>
            <div class="detail">
              <span class="label">Avg Rating:</span>
              <span class="value" [ngClass]="getRatingClass(issue.avg_rating)">{{ issue.avg_rating | number:'1.1-1' }}★</span>
            </div>
            <div class="detail">
              <span class="label">Trend:</span>
              <span class="trend" [ngClass]="issue.trend">
                <span *ngIf="issue.trend === 'up'">↑ Worsening</span>
                <span *ngIf="issue.trend === 'down'">↓ Improving</span>
                <span *ngIf="issue.trend === 'stable'">→ Stable</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      <div *ngIf="!issues || issues.length === 0" class="no-data">
        <p>No issues detected for this period.</p>
      </div>
    </div>
  `,
  styles: [`
    .issue-impact-container {
      display: flex;
      flex-direction: column;
      gap: 2rem;
      padding: 1.5rem;
      background: linear-gradient(135deg, #f5f7fa 0%, #e0e7ff 100%);
      border-radius: 12px;
      box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }

    .chart-card {
      background: white;
      padding: 1.5rem;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }

    .chart-card h3 {
      margin: 0 0 1rem 0;
      font-size: 1.1rem;
      font-weight: 600;
      color: #2c3e50;
    }

    .chart {
      max-height: 350px;
      width: 100%;
    }

    .issue-stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1rem;
    }

    .stat-card {
      background: white;
      padding: 1rem;
      border-radius: 10px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      border-left: 4px solid #6366f1;
      transition: all 0.3s ease;
    }

    .stat-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
    }

    .stat-header {
      display: flex;
      justify-content: space-between;
      align-items: start;
      margin-bottom: 1rem;
      gap: 0.5rem;
    }

    .stat-header h4 {
      margin: 0;
      font-size: 0.95rem;
      font-weight: 600;
      color: #2c3e50;
      flex: 1;
    }

    .impact-badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 0.85rem;
      font-weight: 700;
      color: white;
      white-space: nowrap;
    }

    .impact-badge.critical {
      background: #ef4444;
    }

    .impact-badge.high {
      background: #f97316;
    }

    .impact-badge.medium {
      background: #eab308;
      color: #1f2937;
    }

    .impact-badge.low {
      background: #22c55e;
    }

    .stat-details {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .detail {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.85rem;
    }

    .label {
      color: #6b7280;
      font-weight: 500;
    }

    .value {
      font-weight: 600;
      color: #2c3e50;
    }

    .trend {
      font-weight: 600;
      display: inline-block;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.8rem;
    }

    .trend.up {
      color: #ef4444;
      background: #fee2e2;
    }

    .trend.down {
      color: #22c55e;
      background: #dcfce7;
    }

    .trend.stable {
      color: #6b7280;
      background: #f3f4f6;
    }

    .no-data {
      text-align: center;
      padding: 2rem;
      color: #6b7280;
    }
  `]
})
export class IssueImpactChartComponent implements OnInit, OnChanges {
  @Input() issues: TopIssue[] = [];
  @ViewChild('barCanvas') barCanvas!: ElementRef;

  private barChart: Chart | null = null;

  ngOnInit() {
    this.renderCharts();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['issues'] && !changes['issues'].firstChange) {
      this.renderCharts();
    }
  }

  renderCharts() {
    setTimeout(() => {
      if (this.barCanvas && this.issues && this.issues.length > 0) {
        this.renderBarChart();
      }
    }, 0);
  }

  private renderBarChart() {
    const ctx = this.barCanvas.nativeElement.getContext('2d');
    if (!ctx) return;

    if (this.barChart) {
      this.barChart.destroy();
    }

    const topIssues = this.issues.slice(0, 8);
    const labels = topIssues.map(i => this.formatLabel(i.name));
    const data = topIssues.map(i => i.impact);
    const colors = topIssues.map(i => this.getImpactColor(i.impact));

    const config: ChartConfiguration = {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Impact Score',
            data,
            backgroundColor: colors,
            borderColor: colors.map(c => this.darkenColor(c)),
            borderWidth: 1.5,
            borderRadius: 6,
            barThickness: 40,
          }
        ]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            max: 100,
            grid: {
              color: 'rgba(0, 0, 0, 0.05)'
            }
          }
        }
      }
    };

    this.barChart = new Chart(ctx, config);
  }

  private getImpactColor(impact: number): string {
    if (impact >= 60) return '#ef4444';
    if (impact >= 40) return '#f97316';
    if (impact >= 20) return '#eab308';
    return '#22c55e';
  }

  private darkenColor(color: string): string {
    const colorMap: { [key: string]: string } = {
      '#ef4444': '#991b1b',
      '#f97316': '#92400e',
      '#eab308': '#713f12',
      '#22c55e': '#15803d',
    };
    return colorMap[color] || color;
  }

  getImpactClass(impact: number): string {
    if (impact >= 60) return 'critical';
    if (impact >= 40) return 'high';
    if (impact >= 20) return 'medium';
    return 'low';
  }

  getRatingClass(rating: number): string {
    if (rating >= 4) return 'rating-good';
    if (rating >= 3) return 'rating-ok';
    return 'rating-bad';
  }

  formatLabel(label: string): string {
    return (label || '')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  }
}
