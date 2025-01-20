import { Component } from '@angular/core';
import { DeviceBoxComponent } from '../device-box/device-box.component';
import { QueueTableComponent } from '../queue-table/queue-table.component';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatIconModule } from '@angular/material/icon';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-dashboard',
  imports: [
    DeviceBoxComponent,
    CommonModule,
    QueueTableComponent,
    MatSidenavModule,
    MatIconModule,
    MatButtonModule,
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
