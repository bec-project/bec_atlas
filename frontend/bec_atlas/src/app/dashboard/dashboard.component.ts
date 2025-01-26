import { Component } from '@angular/core';
import { DeviceBoxComponent } from '../device-box/device-box.component';
import { QueueTableComponent } from '../queue-table/queue-table.component';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatIconModule } from '@angular/material/icon';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { ScanTableComponent } from '../scan-table/scan-table.component';
import { MatDividerModule } from '@angular/material/divider';
import { RouterModule } from '@angular/router';
import { MatExpansionModule } from '@angular/material/expansion';

@Component({
  selector: 'app-dashboard',
  imports: [
    DeviceBoxComponent,
    CommonModule,
    QueueTableComponent,
    MatExpansionModule,
    MatDividerModule,
    MatSidenavModule,
    MatIconModule,
    MatButtonModule,
    ScanTableComponent,
    RouterModule,
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent {
  // isScreenSmall = false;

  constructor(private breakpointObserver: BreakpointObserver) {}

  ngOnInit(): void {
    // this.breakpointObserver
    //   .observe([Breakpoints.Small, Breakpoints.XSmall])
    //   .subscribe((result) => {
    //     this.isScreenSmall = result.matches;
    //   });
  }
}
