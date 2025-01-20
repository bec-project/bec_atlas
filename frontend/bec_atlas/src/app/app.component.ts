import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { DashboardComponent } from './dashboard/dashboard.component';
import { GridStackTestComponent } from './gridstack-test/gridstack-test.component';
import { CommonModule } from '@angular/common';
import { RedisConnectorService } from './core/redis-connector.service';
import { DeviceBoxComponent } from './device-box/device-box.component';
import { QueueTableComponent } from './queue-table/queue-table.component';

@Component({
  selector: 'app-root',
  imports: [
    RouterOutlet,
    DashboardComponent,
    CommonModule,
    GridStackTestComponent,
  ],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {
  title = 'bec_atlas';

  constructor(private redisConnector: RedisConnectorService) {}
}
