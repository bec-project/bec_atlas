import {
  Component,
  signal,
  ViewChild,
  computed,
  resource,
  Signal,
  inject,
} from '@angular/core';
import { ScanDataService } from '../core/remote-data.service';
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
import { MatMenuModule } from '@angular/material/menu';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDialog } from '@angular/material/dialog';
import { ColumnSelectionDialogComponent } from './column-selection-dialog/column-selection-dialog.component';

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
    MatMenuModule,
    MatCheckboxModule,
  ],
  templateUrl: './scan-table.component.html',
  styleUrl: './scan-table.component.scss',
})
export class ScanTableComponent {
  tableData: Signal<ScanDataResponse[]>;
  totalScanCount: Signal<number>;
  limit = signal<number>(10);
  offset = signal<number>(0);
  sessionId = signal<string>('');
  dialog = inject(MatDialog);
  pageEvent: PageEvent = new PageEvent();
  sorting: number = -1;
  displayedColumns = signal<string[]>([
    'scan_number',
    'status',
    'num_points',
    'scan_name',
    'scan_type',
    'dataset_number',
    'timestamp',
    'user_rating',
  ]);
  allColumns: string[] = [
    'scan_id',
    'scan_number',
    'status',
    'session_id',
    'num_points',
    'scan_name',
    'scan_type',
    'dataset_number',
    'scan_report_devices',
    'user_metadata',
    'readout_priority',
    'scan_parameters',
    'request_inputs',
    'info',
    'timestamp',
    'user_data',
    'name',
    'user_rating',
    'system_rating',
    'user_comments',
    'system_comments',
  ];
  ignoredEntries: string[] = [
    'scan_report_devices',
    'user_metadata',
    'readout_priority',
    'scan_parameters',
    'request_inputs',
    'info',
  ];

  availableColumns = computed(() =>
    this.allColumns.filter((element) => !this.ignoredEntries.includes(element))
  );

  reloadCriteria = computed(() => ({
    sessionId: this.sessionId(),
    offset: this.offset(),
    limit: this.limit(),
    column: this.displayedColumns(),
  }));

  loadScanDataResource = resource({
    request: () => this.reloadCriteria(),
    loader: ({ request, abortSignal }): Promise<ScanDataResponse[]> => {
      let columns = request.column.map((element) =>
        [
          'name',
          'user_rating',
          'system_rating',
          'user_comments',
          'system_comments',
        ].includes(element)
          ? 'user_data'
          : element
      );
      console.log('Columns', columns);
      return firstValueFrom(
        this.scanData.getScanData(
          request.sessionId,
          request.offset,
          request.limit,
          columns,
          false,
          { scan_number: this.sorting }
        )
      );
    },
  });

  loadScanCountResource = resource({
    request: () => this.reloadCriteria(),
    loader: ({ request, abortSignal }): Promise<ScanCountResponse> => {
      return firstValueFrom(this.scanData.getScanCount(request.sessionId));
    },
  });

  handleScanData(data: ScanDataResponse[] | []) {
    for (const entry of data) {
      if (entry?.user_data !== undefined) {
        entry.name = entry.user_data['name'];
        entry.system_rating = entry.user_data['system_rating'];
        entry.user_rating = entry.user_data['user_rating'];
        entry.user_comments = entry.user_data['user_comments'];
        entry.system_comments = entry.user_data['system_comments'];
      } else {
        entry.name = '';
        entry.system_rating = 0;
        entry.user_rating = 0;
        entry.user_comments = '';
        entry.system_comments = '';
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

  constructor(private scanData: ScanDataService) {
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

  handleRefresh() {
    this.loadScanCountResource.reload();
    this.loadScanDataResource.reload();
  }

  openDialog(): void {
    const dialogRef = this.dialog.open(ColumnSelectionDialogComponent, {
      data: this.availableColumns().map((element) => ({
        name: element,
        selected: this.displayedColumns().includes(element),
      })),
      disableClose: true,
    });
    dialogRef.afterClosed().subscribe((result: string[] | null) => {
      if (result !== null) {
        this.displayedColumns.set(result);
        // this.handleRefresh();
      }
    });
  }

  handleColumnSelection(event: any) {}
}
