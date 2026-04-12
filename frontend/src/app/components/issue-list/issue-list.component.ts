import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TopIssue } from '../../models/insights.model';

@Component({
  selector: 'app-issue-list',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="issue-list-section">
      <h2>🎯 Issue Prioritization</h2>
      <div class="issue-table-wrapper" *ngIf="issues && issues.length > 0; else noIssues">
        <table class="issue-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Issue</th>
              <th>Impact</th>
              <th>Trend</th>
              <th>Affected</th>
              <th>Avg Rating</th>
              <th>Severity</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let issue of issues"
                (click)="issueClicked.emit(issue.name)"
                class="issue-row clickable">
              <td class="rank-cell">
                <span class="rank-num">#{{ issue.rank }}</span>
              </td>
              <td class="name-cell">
                <span class="issue-name">{{ formatName(issue.name) }}</span>
              </td>
              <td>
                <div class="impact-bar-wrapper">
                  <div class="impact-bar" [style.width.%]="issue.impact" [ngClass]="getImpactClass(issue.impact)"></div>
                  <span class="impact-value">{{ issue.impact }}</span>
                </div>
              </td>
              <td class="trend-cell">
                <span class="trend-indicator" [ngClass]="issue.trend">
                  <span *ngIf="issue.trend === 'up'">↑ Worsening</span>
                  <span *ngIf="issue.trend === 'down'">↓ Improving</span>
                  <span *ngIf="issue.trend === 'stable'">→ Stable</span>
                </span>
              </td>
              <td>{{ issue.affected_users }}%</td>
              <td>
                <span [ngClass]="getRatingClass(issue.avg_rating)">
                  {{ issue.avg_rating | number:'1.1-1' }} ★
                </span>
              </td>
              <td>
                <span class="severity-pill" [ngClass]="getSeverityClass(issue.avg_severity)">
                  {{ issue.avg_severity | number:'1.1-1' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <ng-template #noIssues>
        <div class="no-data">No issues detected for this period.</div>
      </ng-template>
    </div>
  `,
  styles: [`
    .issue-list-section h2 { margin: 0 0 16px; font-size: 1.3rem; color: #2c3e50; }
    .issue-table-wrapper {
      background: white;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      overflow: hidden;
    }
    .issue-table {
      width: 100%;
      border-collapse: collapse;
    }
    .issue-table thead {
      background: #2c3e50;
      color: white;
    }
    .issue-table th {
      padding: 14px 16px;
      text-align: left;
      font-weight: 600;
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .issue-table td {
      padding: 12px 16px;
      border-bottom: 1px solid #ecf0f1;
      font-size: 0.92rem;
    }
    .issue-row.clickable { cursor: pointer; transition: background 0.2s; }
    .issue-row.clickable:hover { background: #f0f4f8; }
    .rank-cell { width: 60px; }
    .rank-num {
      background: #3498db;
      color: white;
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 0.8rem;
      font-weight: 700;
    }
    .name-cell { font-weight: 600; }
    .issue-name { color: #2c3e50; }
    .impact-bar-wrapper {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .impact-bar {
      height: 8px;
      border-radius: 4px;
      min-width: 4px;
      max-width: 120px;
      transition: width 0.5s ease;
    }
    .impact-bar.critical { background: #e74c3c; }
    .impact-bar.high { background: #f39c12; }
    .impact-bar.medium { background: #f1c40f; }
    .impact-bar.low { background: #27ae60; }
    .impact-value { font-weight: 700; font-size: 0.9rem; color: #2c3e50; }
    .trend-indicator { font-weight: 600; font-size: 0.85rem; }
    .trend-indicator.up { color: #e74c3c; }
    .trend-indicator.down { color: #27ae60; }
    .trend-indicator.stable { color: #95a5a6; }
    .severity-pill {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 12px;
      font-size: 0.8rem;
      font-weight: 700;
      color: white;
    }
    .severity-pill.critical { background: #e74c3c; }
    .severity-pill.high { background: #f39c12; }
    .severity-pill.medium { background: #f1c40f; color: #333; }
    .severity-pill.low { background: #27ae60; }
    span.rating-bad { color: #e74c3c; font-weight: 700; }
    span.rating-ok { color: #f39c12; font-weight: 700; }
    span.rating-good { color: #27ae60; font-weight: 700; }
    .no-data {
      text-align: center;
      color: #7f8c8d;
      padding: 40px;
      background: white;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
  `]
})
export class IssueListComponent {
  @Input() issues: TopIssue[] = [];
  @Output() issueClicked = new EventEmitter<string>();

  formatName(name: string): string {
    return (name || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  getImpactClass(impact: number): string {
    if (impact > 70) return 'critical';
    if (impact > 50) return 'high';
    if (impact > 30) return 'medium';
    return 'low';
  }

  getRatingClass(rating: number): string {
    if (rating < 2) return 'rating-bad';
    if (rating < 3.5) return 'rating-ok';
    return 'rating-good';
  }

  getSeverityClass(severity: number): string {
    if (severity > 7) return 'critical';
    if (severity > 5) return 'high';
    if (severity > 3) return 'medium';
    return 'low';
  }
}
