import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Alert } from '../../models/insights.model';

@Component({
  selector: 'app-alerts-panel',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="alerts-panel" *ngIf="alerts && alerts.length > 0">
      <h2>🚨 Alerts</h2>
      <div class="alerts-list">
        <div *ngFor="let alert of alerts"
             class="alert-card"
             [ngClass]="alert.severity">
          <div class="alert-icon">
            <span *ngIf="alert.severity === 'critical'">🔴</span>
            <span *ngIf="alert.severity === 'high'">🟠</span>
            <span *ngIf="alert.severity === 'medium'">🟡</span>
            <span *ngIf="alert.severity === 'low'">🟢</span>
          </div>
          <div class="alert-content">
            <div class="alert-message">{{ alert.message }}</div>
            <div class="alert-meta">
              <span class="severity-badge" [ngClass]="alert.severity">{{ alert.severity | uppercase }}</span>
              <span class="change-badge" *ngIf="alert.change_percentage">
                ↑ {{ alert.change_percentage }}%
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .alerts-panel { margin-bottom: 24px; }
    .alerts-panel h2 { margin: 0 0 12px; font-size: 1.3rem; color: #2c3e50; }
    .alerts-list { display: flex; flex-direction: column; gap: 10px; }
    .alert-card {
      display: flex;
      align-items: flex-start;
      gap: 14px;
      padding: 16px 20px;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      border-left: 4px solid #95a5a6;
      background: white;
    }
    .alert-card.critical { border-left-color: #e74c3c; background: #fef2f2; }
    .alert-card.high { border-left-color: #f39c12; background: #fff8f0; }
    .alert-card.medium { border-left-color: #f1c40f; background: #fffdf0; }
    .alert-card.low { border-left-color: #27ae60; background: #f0fdf4; }
    .alert-icon { font-size: 1.4rem; line-height: 1; }
    .alert-content { flex: 1; }
    .alert-message { font-size: 0.95rem; color: #2c3e50; font-weight: 500; margin-bottom: 6px; }
    .alert-meta { display: flex; gap: 10px; align-items: center; }
    .severity-badge {
      font-size: 0.7rem;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 4px;
      text-transform: uppercase;
    }
    .severity-badge.critical { background: #e74c3c; color: white; }
    .severity-badge.high { background: #f39c12; color: white; }
    .severity-badge.medium { background: #f1c40f; color: #333; }
    .severity-badge.low { background: #27ae60; color: white; }
    .change-badge { font-size: 0.8rem; color: #e74c3c; font-weight: 600; }
  `]
})
export class AlertsPanelComponent {
  @Input() alerts: Alert[] = [];
}
