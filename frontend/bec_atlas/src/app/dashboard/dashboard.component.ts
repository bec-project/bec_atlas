import { Component, signal, OnInit } from '@angular/core';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatIconModule } from '@angular/material/icon';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { Router, RouterModule } from '@angular/router';
import { MatTooltipModule } from '@angular/material/tooltip';
import { DeploymentService } from '../deployment.service';
import {
  MatDialog,
  MatDialogModule,
  MatDialogConfig,
} from '@angular/material/dialog';
import { DeploymentSelectionComponent } from '../deployment-selection/deployment-selection.component';
import { RedisConnectorService } from '../core/redis-connector.service';
import { AuthDataService } from '../core/remote-data.service';

interface NavItem {
  id: string;
  label: string;
  icon: string;
  route?: string;
  children?: NavItem[];
}

@Component({
  selector: 'app-dashboard',
  imports: [
    CommonModule,
    MatSidenavModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    MatDialogModule,
    RouterModule,
  ],
  providers: [DeploymentService, RedisConnectorService],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit {
  // Signals for responsive design
  isMobile = signal(false);

  // UI state
  selectedNavItem = signal<string>('analytics');
  selectedSubItem = signal<string>('');
  showNavPanel = signal<boolean>(true);

  // Navigation items with their content
  navItems: NavItem[] = [
    {
      id: 'analytics',
      label: 'Analytics',
      icon: 'analytics',
      route: '/dashboard/analytics',
      children: [
        { id: 'reports', label: 'Reports', icon: 'assessment' },
        { id: 'metrics', label: 'Metrics', icon: 'speed' },
        { id: 'dashboards', label: 'Dashboards', icon: 'dashboard' },
        { id: 'exports', label: 'Data Exports', icon: 'file_download' },
      ],
    },
    {
      id: 'data',
      label: 'Data Browser',
      icon: 'table_chart',
      children: [
        {
          id: 'scan-data',
          label: 'Scan Data',
          icon: 'scatter_plot',
          route: '/dashboard/scan-table',
        },
        {
          id: 'device-data',
          label: 'Device Data',
          icon: 'developer_board',
          route: '/dashboard/device-data',
        },
        { id: 'historical', label: 'Historical Data', icon: 'history' },
        { id: 'realtime', label: 'Real-time Data', icon: 'timeline' },
      ],
    },
    {
      id: 'control',
      label: 'Experiment Control',
      icon: 'science',
      children: [
        {
          id: 'overview',
          label: 'Control Panel',
          icon: 'tune',
          route: '/dashboard/overview-grid',
        },
        {
          id: 'admin',
          label: 'Admin',
          icon: 'admin_panel_settings',
          route: '/dashboard/deployment-admin',
        },
        { id: 'automation', label: 'Automation', icon: 'auto_fix_high' },
        { id: 'sequences', label: 'Sequences', icon: 'playlist_play' },
      ],
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: 'settings',
      route: '/dashboard/settings',
      children: [
        { id: 'user-settings', label: 'User Settings', icon: 'person' },
        {
          id: 'system-config',
          label: 'System Configuration',
          icon: 'settings_applications',
        },
        { id: 'security', label: 'Security', icon: 'security' },
        { id: 'integrations', label: 'Integrations', icon: 'extension' },
      ],
    },
  ];

  // Get current navigation content
  getCurrentNavContent() {
    return this.navItems.find((item) => item.id === this.selectedNavItem());
  }

  // Navigate to child route
  navigateToChild(child: NavItem): void {
    this.selectedSubItem.set(child.id);
    if (child.route) {
      this.router.navigate([child.route]);
    }
  }

  constructor(
    private breakpointObserver: BreakpointObserver,
    private deploymentService: DeploymentService,
    private authDataService: AuthDataService,
    private router: Router,
    private dialog: MatDialog
  ) {
    // Setup responsive breakpoints
    this.breakpointObserver
      .observe([Breakpoints.Handset])
      .subscribe((result) => this.isMobile.set(result.matches));
  }

  ngOnInit(): void {
    // Initialize any needed data
    // Set default selected navigation item
    this.selectedNavItem.set('analytics');
    this.selectedSubItem.set('reports');
  }

  selectNavItem(item: NavItem): void {
    // If clicking the same item, toggle the panel
    if (this.selectedNavItem() === item.id) {
      this.toggleNavPanel();
    } else {
      // If clicking a different item, switch content and ensure panel is open
      this.selectedNavItem.set(item.id);
      this.showNavPanel.set(true);
    }

    if (item.route) {
      this.router.navigate([item.route]);
    }
  }

  toggleNavPanel(): void {
    this.showNavPanel.update((visible) => !visible);
  }

  openDeploymentDialog(): void {
    const dialogConfig: MatDialogConfig = {
      disableClose: true,
      width: this.isMobile() ? '95vw' : '600px',
      maxWidth: '95vw',
    };

    const dialogRef = this.dialog.open(
      DeploymentSelectionComponent,
      dialogConfig
    );
    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        this.deploymentService.selectDeployment(result);
      }
    });
  }

  logout(): void {
    this.authDataService.logout();
    this.router.navigate(['/login']);
  }
}
