import { Component, OnInit, ViewChild, ElementRef, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Chart, ChartConfiguration, registerables } from 'chart.js';

Chart.register(...registerables);

@Component({
  selector: 'app-sentiment-chart',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="sentiment-charts-container">
      <!-- Charts Row -->
      <div class="charts-grid">
        <!-- Pie Chart -->
        <div class="chart-card">
          <h3>Distribution</h3>
          <canvas #pieCanvas class="chart"></canvas>
        </div>
        
        <!-- Bar Chart -->
        <div class="chart-card">
          <h3>Counts</h3>
          <canvas #barCanvas class="chart"></canvas>
        </div>
      </div>

      <!-- Sentiment Stats -->
      <div class="sentiment-stats">
        <div class="stat positive-stat">
          <div class="stat-icon">🟢</div>
          <div class="stat-content">
            <div class="stat-label">Positive</div>
            <div class="stat-value">{{ sentimentData.positive }}</div>
            <div class="stat-percent">{{ getPercent(sentimentData.positive) }}%</div>
          </div>
        </div>

        <div class="stat neutral-stat">
          <div class="stat-icon">⚪</div>
          <div class="stat-content">
            <div class="stat-label">Neutral</div>
            <div class="stat-value">{{ sentimentData.neutral }}</div>
            <div class="stat-percent">{{ getPercent(sentimentData.neutral) }}%</div>
          </div>
        </div>

        <div class="stat negative-stat">
          <div class="stat-icon">🔴</div>
          <div class="stat-content">
            <div class="stat-label">Negative</div>
            <div class="stat-value">{{ sentimentData.negative }}</div>
            <div class="stat-percent">{{ getPercent(sentimentData.negative) }}%</div>
          </div>
        </div>
      </div>

      <!-- Sentiment Metadata -->

      <!-- Intelligence Note -->
      <div *ngIf="sentimentData.corrected_count > 0" class="intelligence-note">
        <span class="icon">🧠</span>
        <span class="text">AI corrected {{ sentimentData.corrected_count }} misclassifications for accuracy</span>
      </div>
    </div>
  `,
  styles: [`
    .sentiment-charts-container {
      display: flex;
      flex-direction: column;
      gap: 2rem;
      padding: 1.5rem;
      background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
      border-radius: 12px;
      box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }

    .charts-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 2rem;
    }

    .chart-card {
      background: white;
      padding: 1.5rem;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      transition: transform 0.3s ease, box-shadow 0.3s ease;
    }

    .chart-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 16px rgba(0, 0, 0, 0.12);
    }

    .chart-card h3 {
      margin: 0 0 1rem 0;
      font-size: 1.1rem;
      font-weight: 600;
      color: #2c3e50;
    }

    .chart {
      max-height: 300px;
      width: 100%;
    }

    .sentiment-stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 1rem;
    }

    .stat {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 1.5rem;
      background: white;
      border-radius: 10px;
      transition: all 0.3s ease;
    }

    .stat:hover {
      transform: scale(1.05);
    }

    .positive-stat {
      border-left: 4px solid #22c55e;
    }

    .neutral-stat {
      border-left: 4px solid #6b7280;
    }

    .negative-stat {
      border-left: 4px solid #ef4444;
    }

    .stat-icon {
      font-size: 2rem;
    }

    .stat-content {
      flex: 1;
    }

    .stat-label {
      font-size: 0.875rem;
      color: #6b7280;
      font-weight: 500;
    }

    .stat-value {
      font-size: 1.5rem;
      font-weight: 700;
      color: #2c3e50;
      margin: 0.25rem 0;
    }

    .stat-percent {
      font-size: 0.875rem;
      font-weight: 600;
      color: #3b82f6;
    }

    .sentiment-metadata {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      padding: 1.5rem;
      background: white;
      border-radius: 10px;
    }

    .metadata-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.75rem;
      border-bottom: 1px solid #e5e7eb;
    }

    .metadata-item:last-child {
      border-bottom: none;
    }

    .label {
      font-size: 0.875rem;
      color: #6b7280;
      font-weight: 500;
    }

    .value {
      font-size: 1rem;
      font-weight: 600;
      color: #2c3e50;
    }

    .value.improving {
      color: #22c55e;
    }

    .value.declining {
      color: #ef4444;
    }

    .value.stable {
      color: #f59e0b;
    }

    .intelligence-note {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 1rem;
      background: rgba(59, 130, 246, 0.1);
      border-left: 3px solid #3b82f6;
      border-radius: 6px;
      color: #1e40af;
      font-size: 0.9rem;
      font-weight: 500;
    }

    .icon {
      font-size: 1.25rem;
    }

    @media (max-width: 768px) {
      .charts-grid {
        grid-template-columns: 1fr;
      }

      .sentiment-stats {
        grid-template-columns: 1fr;
      }
    }
  `]
})
export class SentimentChartComponent implements OnInit, OnChanges {
  @Input() sentimentData: any = {
    positive: 0,
    negative: 0,
    neutral: 0,
    average_score: 0,
    confidence: 0,
    trend: 'stable',
    corrected_count: 0
  };

  @ViewChild('pieCanvas') pieCanvas!: ElementRef<HTMLCanvasElement>;
  @ViewChild('barCanvas') barCanvas!: ElementRef<HTMLCanvasElement>;

  private pieChart: Chart | null = null;
  private barChart: Chart | null = null;

  ngOnInit() {
    this.createCharts();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['sentimentData'] && !changes['sentimentData'].firstChange) {
      this.updateCharts();
    }
  }

  private createCharts() {
    setTimeout(() => {
      if (this.pieCanvas?.nativeElement) {
        this.createPieChart();
      }
      if (this.barCanvas?.nativeElement) {
        this.createBarChart();
      }
    }, 100);
  }

  private createPieChart() {
    const data = [
      this.sentimentData.positive,
      this.sentimentData.neutral,
      this.sentimentData.negative
    ];

    const config: ChartConfiguration = {
      type: 'doughnut',
      data: {
        labels: ['Positive', 'Neutral', 'Negative'],
        datasets: [{
          data: data,
          backgroundColor: ['#22c55e', '#d1d5db', '#ef4444'],
          borderColor: ['#16a34a', '#9ca3af', '#dc2626'],
          borderWidth: 2,
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              font: { size: 12, weight: 'bold' },
              padding: 15,
              usePointStyle: true
            }
          }
        }
      }
    };

    this.pieChart = new Chart(this.pieCanvas.nativeElement, config);
  }

  private createBarChart() {
    const config: ChartConfiguration = {
      type: 'bar',
      data: {
        labels: ['Positive', 'Neutral', 'Negative'],
        datasets: [{
          label: 'Count',
          data: [
            this.sentimentData.positive,
            this.sentimentData.neutral,
            this.sentimentData.negative
          ],
          backgroundColor: ['#22c55e', '#d1d5db', '#ef4444'],
          borderRadius: 6,
          borderSkipped: false,
          hoverBackgroundColor: ['#16a34a', '#9ca3af', '#dc2626']
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: false }
        },
        scales: {
          x: {
            beginAtZero: true
          }
        }
      }
    };

    this.barChart = new Chart(this.barCanvas.nativeElement, config);
  }

  private updateCharts() {
    if (this.pieChart) {
      this.pieChart.data.datasets[0].data = [
        this.sentimentData.positive,
        this.sentimentData.neutral,
        this.sentimentData.negative
      ] as any;
      this.pieChart.update();
    }

    if (this.barChart) {
      this.barChart.data.datasets[0].data = [
        this.sentimentData.positive,
        this.sentimentData.neutral,
        this.sentimentData.negative
      ] as any;
      this.barChart.update();
    }
  }

  getPercent(value: number): number {
    const total = this.sentimentData.positive + this.sentimentData.neutral + this.sentimentData.negative;
    return total > 0 ? Math.round((value / total) * 100) : 0;
  }
}
