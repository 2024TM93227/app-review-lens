import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../services/api.service';

interface App {
  app_id: string;
  name: string;
  rating: number;
  review_count: number;
  icon_url?: string;
}

@Component({
  selector: 'app-app-selection',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app-selection.component.html',
  styleUrls: ['./app-selection.component.scss']
})
export class AppSelectionComponent implements OnInit {
  apps: App[] = [];
  searchQuery = '';
  selectedApps: string[] = [];
  loading = false;
  error = '';
  mode: 'single' | 'compare' = 'single';
  private iconFailedSet = new Set<string>();

  constructor(private api: ApiService, private router: Router) {}

  ngOnInit() {
    this.loadApps();
  }

  loadApps() {
    this.loading = true;
    this.error = '';
    this.api.searchApps(this.searchQuery).subscribe({
      next: (apps) => {
        this.apps = apps;
        console.log('Loaded apps:', this.apps);
        this.apps.forEach(app => {
          console.log(`App: ${app.name}, Icon URL: ${app.icon_url}`);
        });
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load apps';
        this.loading = false;
      }
    });
  }

  toggleApp(appId: string) {
    const index = this.selectedApps.indexOf(appId);
    if (index > -1) {
      // Deselect
      this.selectedApps.splice(index, 1);
    } else {
      // Select
      if (this.mode === 'single') {
        this.selectedApps = [appId];
      } else if (this.selectedApps.length < 2) {
        this.selectedApps.push(appId);
      }
    }
  }

  isSelected(appId: string): boolean {
    return this.selectedApps.includes(appId);
  }

  proceed() {
    if (this.selectedApps.length === 0) {
      this.error = 'Please select at least one app';
      return;
    }

    if (this.selectedApps.length === 1) {
      // Single app mode - go to ingestion
      this.router.navigate(['/ingestion'], {
        queryParams: { app: this.selectedApps[0] }
      });
    } else if (this.selectedApps.length === 2) {
      // Compare mode
      this.router.navigate(['/ingestion'], {
        queryParams: { appA: this.selectedApps[0], appB: this.selectedApps[1] }
      });
    }
  }

  switchToCompare() {
    this.mode = this.mode === 'single' ? 'compare' : 'single';
    this.selectedApps = [];
  }

  onIconLoadError(appId: string) {
    console.warn(`Icon failed to load for app: ${appId}`);
    this.iconFailedSet.add(appId);
  }

  isIconFailed(appId: string): boolean {
    return this.iconFailedSet.has(appId);
  }
}
