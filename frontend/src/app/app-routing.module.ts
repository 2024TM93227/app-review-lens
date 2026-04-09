import { Routes } from '@angular/router';
import { DashboardComponent } from './dashboard/dashboard.component';
import { CompareComponent } from './compare/compare.component';
import { AppSelectionComponent } from './app-selection/app-selection.component';
import { IngestionComponent } from './ingestion/ingestion.component';

export const routes: Routes = [
  { path: '', component: AppSelectionComponent },
  { path: 'ingestion', component: IngestionComponent },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'compare', component: CompareComponent }, 
  { path: '**', redirectTo: '' }
];
