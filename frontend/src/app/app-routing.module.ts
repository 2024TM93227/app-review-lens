import { Routes } from '@angular/router';
import { DashboardComponent } from './dashboard/dashboard.component';
import { CompareComponent } from './compare/compare.component';
import { IssueDetailComponent } from './components/issue-detail/issue-detail.component';

export const routes: Routes = [
  { path: '', component: DashboardComponent },
  { path: 'compare', component: CompareComponent },
  { path: 'issues/:appId/:issueName', component: IssueDetailComponent },
  { path: '**', redirectTo: '' }
];
