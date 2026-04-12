import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface FilterState {
  days: number;
  rating: number | null;
  sentiment: string | null;
}

@Component({
  selector: 'app-filters',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="filters-bar">
      <div class="filter-group">
        <label>Time Range</label>
        <div class="btn-group">
          <button *ngFor="let d of dayOptions"
                  [class.active]="filters.days === d"
                  (click)="setDays(d)">
            {{ d }}d
          </button>
        </div>
      </div>

      <div class="filter-group">
        <label>Rating</label>
        <div class="btn-group">
          <button [class.active]="filters.rating === null" (click)="setRating(null)">All</button>
          <button *ngFor="let r of [1,2,3,4,5]"
                  [class.active]="filters.rating === r"
                  (click)="setRating(r)">
            {{ r }}★
          </button>
        </div>
      </div>

      <div class="filter-group">
        <label>Sentiment</label>
        <div class="btn-group">
          <button [class.active]="filters.sentiment === null" (click)="setSentiment(null)">All</button>
          <button class="sentiment-pos" [class.active]="filters.sentiment === 'positive'" (click)="setSentiment('positive')">Positive</button>
          <button class="sentiment-neu" [class.active]="filters.sentiment === 'neutral'" (click)="setSentiment('neutral')">Neutral</button>
          <button class="sentiment-neg" [class.active]="filters.sentiment === 'negative'" (click)="setSentiment('negative')">Negative</button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .filters-bar {
      display: flex;
      gap: 24px;
      flex-wrap: wrap;
      background: white;
      padding: 16px 20px;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      margin-bottom: 20px;
      align-items: flex-end;
    }
    .filter-group { display: flex; flex-direction: column; gap: 6px; }
    .filter-group label { font-size: 0.8rem; font-weight: 600; color: #7f8c8d; text-transform: uppercase; }
    .btn-group { display: flex; gap: 4px; }
    .btn-group button {
      padding: 6px 14px;
      border: 1px solid #ddd;
      background: #f8f9fa;
      border-radius: 4px;
      cursor: pointer;
      font-size: 0.85rem;
      font-weight: 500;
      transition: all 0.2s;
    }
    .btn-group button:hover { background: #e8ecf1; }
    .btn-group button.active {
      background: #3498db;
      color: white;
      border-color: #3498db;
    }
    .btn-group button.sentiment-pos.active { background: #27ae60; border-color: #27ae60; }
    .btn-group button.sentiment-neu.active { background: #95a5a6; border-color: #95a5a6; }
    .btn-group button.sentiment-neg.active { background: #e74c3c; border-color: #e74c3c; }
  `]
})
export class FiltersComponent implements OnInit {
  @Output() filtersChanged = new EventEmitter<FilterState>();
  @Input() initialFilters: FilterState | null = null;

  dayOptions = [7, 14, 30, 90];

  filters: FilterState = {
    days: 30,
    rating: null,
    sentiment: null,
  };

  ngOnInit(): void {
    if (this.initialFilters) {
      this.filters = { ...this.initialFilters };
    }
  }

  setDays(d: number) {
    this.filters.days = d;
    this.emit();
  }

  setRating(r: number | null) {
    this.filters.rating = r;
    this.emit();
  }

  setSentiment(s: string | null) {
    this.filters.sentiment = s;
    this.emit();
  }

  private emit() {
    this.filtersChanged.emit({ ...this.filters });
  }
}
