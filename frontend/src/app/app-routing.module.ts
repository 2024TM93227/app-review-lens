import { Routes } from '@angular/router';
import { DashboardComponent } from './dashboard/dashboard.component';
import { CompareComponent } from './compare/compare.component';

export const routes: Routes = [
  { path: '', component: DashboardComponent },
  { path: 'compare', component: CompareComponent }, 
  { path: '**', redirectTo: '' }
];
