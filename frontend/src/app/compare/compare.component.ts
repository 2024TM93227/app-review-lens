import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { forkJoin, firstValueFrom } from 'rxjs';
import { CompareService } from '../services/compare.service';
import { ActivatedRoute, Router } from '@angular/router';

@Component({
  selector: 'app-compare',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './compare.component.html',
  styleUrls: ['./compare.component.scss']
})
export class CompareComponent {

  
  monitoredApps = [
    { id: 'in.swiggy.android', name: 'Swiggy' },
    { id: 'com.application.zomato', name: 'Zomato' },
    { id: 'com.ubercab.eats', name: 'Uber Eats' },
    { id: 'in.swiggy.android.instamart', name: 'Swiggy Instamart' }
  ];

  appA = this.monitoredApps[0].id;
  appB = this.monitoredApps[1].id;

  loading = false;
  error = '';
  isIngesting = false;
  ingestProgress = 0;
  status = '';

  comparisonRows: any[] = [];
  issueComparison: any[] = [];

  userSignals: any = {};
  actionItems: string[] = [];

  constructor(private compareService: CompareService, private router: Router,private route:ActivatedRoute) {}

  private hasAutoLoaded = false;

  ngOnInit() {
  this.route.queryParams.subscribe(params => {
    if (params['appA'] && !this.hasAutoLoaded) {
      this.hasAutoLoaded = true;

      this.appA = params['appA'];
      this.appB = this.monitoredApps.find(a => a.id !== this.appA)?.id || this.appB;

      this.compare();
    }
  });
  }
goToDashboard() {
  this.router.navigate(['/'], {
    queryParams: { app: this.appA }
  });
}

  async compare() {
    this.loading = true;
    this.error = '';
    this.status = '⏳ Ingesting reviews...';
    this.userSignals = {};
    this.actionItems = [];

    if (this.appA === this.appB) {
      this.error = 'Select two different apps';
      this.loading = false;
      return;
    }

    try {
      this.isIngesting = true;

      await firstValueFrom(this.compareService.ingestReviews(this.appA));
      this.ingestProgress = 50;

      await firstValueFrom(this.compareService.ingestReviews(this.appB));
      this.ingestProgress = 100;

      this.isIngesting = false;
      this.status = '🔄 Comparing insights...';

      this.runComparison();

    } catch {
      this.error = 'Failed to ingest';
      this.loading = false;
      this.status = '';
    }
  }

  runComparison() {
    const apps = [this.appA, this.appB];

    forkJoin({
      aspects: this.compareService.compareAspects(apps),
      issues: this.compareService.compareIssues(apps)
    }).subscribe({
      next: (res) => {

        this.issueComparison = Object.entries(res.issues.top_issues || {})
          .map(([app, issues]: any) => ({ app, issues }));

        this.comparisonRows = Object.entries(res.aspects.aspects_comparison || {})
          .map(([aspect, values]: any) => {
            const aScore = Number(values[this.appA] || 0);
            const bScore = Number(values[this.appB] || 0);

            return {
              aspect,
              aScore,
              bScore,
              winner:
                aScore === bScore
                  ? 'Tie'
                  : aScore > bScore
                  ? this.getAppName(this.appA)
                  : this.getAppName(this.appB)
            };
          });

        this.generateUserSignals();
        this.generateActionItems();

        this.status = '✅ Comparison complete';
        this.loading = false;
      },
      error: () => {
        this.error = 'Comparison failed';
        this.loading = false;
        this.status = '';
      }
    });
  }

  // 🔥 USER SIGNALS CLEANED
  generateUserSignals() {
    this.userSignals[this.appA] = this.extractSignals(this.appA);
    this.userSignals[this.appB] = this.extractSignals(this.appB);
  }

  extractSignals(appId: string) {
    const issues = this.issueComparison.find(i => i.app === appId)?.issues || [];

    const categories = issues
      .map((i: any) => i.category)
      .filter((c: string) => c && c !== 'general');

    return {
      positives: categories.slice(-2).map((c: string) => c.replace(/_/g, ' ')),
      negatives: categories.slice(0, 2).map((c: string) => c.replace(/_/g, ' '))
    };
  }

  // 🎯 SMART ACTION ITEMS
  generateActionItems() {
  this.actionItems = this.comparisonRows
    .filter(r => r.bScore - r.aScore > 0.07)
    .sort((a, b) => (b.bScore - b.aScore) - (a.bScore - a.aScore))
    .map(r => {
      const aspect = this.toTitleCase(r.aspect);

      if (aspect.toLowerCase().includes('delivery')) {
        return `Delivery Experience is weaker — focus on faster delivery and accurate ETA.`;
      } else if (aspect.toLowerCase().includes('payment')) {
        return `Payment Experience needs improvement — reduce failures and improve reliability.`;
      } else if (aspect.toLowerCase().includes('tracking')) {
        return `Order Tracking needs improvement — provide real-time updates and accuracy.`;
      } else if (aspect.toLowerCase().includes('support')) {
        return `Customer Support needs improvement — reduce response time and improve resolution quality.`;
      } else if (aspect.toLowerCase().includes('accuracy')) {
        return `Order Accuracy needs improvement — reduce wrong or missing items.`;
      } else if (aspect.toLowerCase().includes('ui')) {
        return `UI/UX can be improved — enhance usability and navigation clarity.`;
      } else if (aspect.toLowerCase().includes('offers')) {
        return `Offers & Pricing could be stronger — improve discounts and perceived value.`;
      } else {
        return `${aspect} needs improvement — users rate your competitor higher in this area.`;
      }
    });

  if (!this.actionItems.length) {
    this.actionItems.push('You are competitive across most areas. Maintain consistency.');
  }
}

  getAppName(id: string) {
    return this.monitoredApps.find(a => a.id === id)?.name || id;
  }
  toTitleCase(text: string): string {
  return text
    .replace(/_/g, ' ')                 // replace underscores
    .toLowerCase()
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
  }
}