import { Component, computed, effect, Signal } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatToolbarModule } from '@angular/material/toolbar';
import { RedisConnectorService } from '../core/redis-connector.service';
import { MessageEndpoints } from '../core/redis_endpoints';
import { CommonModule } from '@angular/common';
import { BaseWidget } from 'gridstack/dist/angular';

@Component({
  selector: 'app-queue-table',
  imports: [MatCardModule, MatTableModule, MatToolbarModule, CommonModule],
  templateUrl: './queue-table.component.html',
  styleUrl: './queue-table.component.scss',
})
export class QueueTableComponent extends BaseWidget {
  tableSignal!: Signal<any>;
  tableData!: Signal<any>;
  displayedColumns: string[] = ['queue_id', 'scan_id', 'scan_number', 'status'];

  constructor(private redisConnector: RedisConnectorService) {
    super();
  }

  ngOnInit(): void {
    this.tableSignal = this.redisConnector.register(
      MessageEndpoints.scan_queue_status()
    );

    this.tableData = computed(() => {
      let data = this.tableSignal();
      console.log('Table data: ', data);
      if (!data) {
        return [];
      }
      return data.data.queue?.primary.info || [];
    });
  }
}
