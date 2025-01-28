import { Routes } from '@angular/router';
import { LoginComponent } from './login/login.component';
import { DashboardComponent } from './dashboard/dashboard.component';
import { OverviewComponent } from './overview/overview.component';
import { OverviewGridComponent } from './overview-grid/overview-grid.component';
import { ScanTableComponent } from './scan-table/scan-table.component';
import { DeploymentAdminComponent } from './deployment-admin/deployment-admin.component';

export const routes: Routes = [
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  {
    path: 'dashboard',
    component: DashboardComponent,
    children: [
      { path: 'scan-table', component: ScanTableComponent },
      { path: 'deployment-admin', component: DeploymentAdminComponent },
      { path: 'overview-grid', component: OverviewGridComponent },
    ],
  },
  { path: 'overview', component: OverviewComponent },

  { path: '**', redirectTo: 'login' },
];
