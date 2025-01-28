import {
  ChangeDetectionStrategy,
  Component,
  WritableSignal,
  signal,
  ViewChild,
  computed,
  resource,
  Signal,
} from '@angular/core';
import { ScanCountService, ScanDataService } from '../core/remote-data.service';
import { ScanDataResponse } from '../core/model/scan-data';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import {
  MatPaginator,
  MatPaginatorModule,
  PageEvent,
} from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { StarRatingModule } from 'angular-star-rating';
import { MatSort } from '@angular/material/sort';
import { firstValueFrom, Observable } from 'rxjs';
import { ScanCountResponse } from '../core/model/scan-count';

export interface ResourceStatus {
  status: any;
}
export interface ResourceLoaderParams {
  request: any;
  abortSignal: AbortSignal;
  previous: ResourceStatus;
}

@Component({
  selector: 'app-scan-table',
  standalone: true,
  imports: [
    CommonModule,
    MatPaginator,
    MatTableModule,
    MatIconModule,
    MatToolbarModule,
    MatCardModule,
    MatButtonModule,
    MatPaginatorModule,
    StarRatingModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './scan-table.component.html',
  styleUrl: './scan-table.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ScanTableComponent {
  tableData: Signal<ScanDataResponse[]>;
  totalScanCount: Signal<number>;
  limit = signal<number>(10);
  offset = signal<number>(0);
  sessionId = signal<string>('');

  // page: number = this.offset / this.limit;
  pageEvent: PageEvent = new PageEvent();
  sorting: number = -1;
  displayedColumns: string[] = [
    'scan_number',
    'status',
    'num_points',
    'scan_name',
    'scan_type',
    'dataset_number',
    'timestamp',
    'user_rating',
  ];
  ignoredEntries: string[] = [
    'scan_report_devices',
    'user_metadata',
    'readout_priority',
    'scan_parameters',
    'request_inputs',
    'info',
  ];

  reloadCriteria = computed(() => ({
    sessionId: this.sessionId(),
    offset: this.offset(),
    limit: this.limit(),
  }));

  loadScanDataResource = resource({
    request: () => this.reloadCriteria(),
    loader: ({ request, abortSignal }): Promise<ScanDataResponse[]> => {
      return firstValueFrom(
        this.scanData.getScanData(
          request.sessionId,
          request.offset,
          request.limit,
          this.displayedColumns,
          false,
          { scan_number: this.sorting }
        )
      );
    },
  });

  loadScanCountResource = resource({
    request: () => this.reloadCriteria(),
    loader: ({ request, abortSignal }): Promise<ScanCountResponse> => {
      return firstValueFrom(this.scanCount.getScanCount(request.sessionId));
    },
  });

  handleScanData(data: ScanDataResponse[] | []) {
    for (const entry of data) {
      if (entry.user_data && entry.user_data['user_rating']) {
        entry.user_rating = entry.user_data['user_rating'];
      }
    }
    return data;
  }

  handleCountData(data: ScanCountResponse | 0) {
    if (data === 0) {
      return 0;
    }
    return data.count;
  }

  constructor(
    private scanData: ScanDataService,
    private scanCount: ScanCountService
  ) {
    this.tableData = computed(() =>
      this.handleScanData(this.loadScanDataResource.value() || [])
    );
    this.totalScanCount = computed(() =>
      this.handleCountData(this.loadScanCountResource.value() || 0)
    );
  }

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  ngOnInit(): void {
    this.sessionId.set('6793628df62026a414d9338e');
    // this.updateUI();
  }

  handlePageEvent(event: PageEvent) {
    this.pageEvent = event;
    this.offset.set(event.pageIndex * event.pageSize);
    this.limit.set(event.pageSize);
  }
}
