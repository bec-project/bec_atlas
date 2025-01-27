import {
  ChangeDetectionStrategy,
  Component,
  WritableSignal,
  signal,
  ViewChild,
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
  // private tableData: new MatTableDataSource<ScanDataResponse[]>();  // Initialize as empty array
  // tableData: ScanDataResponse[] = [];
  tableData: WritableSignal<ScanDataResponse[]> = signal([]);
  limit: number = 10;
  offset: number = 0;
  totalScanCount: number = 0;
  page: number = this.offset / this.limit;
  pageEvent: PageEvent = new PageEvent();
  sessionId: string = '';
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

  constructor(
    private scanData: ScanDataService,
    private scanCount: ScanCountService
  ) {}

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  ngOnInit(): void {
    this.sessionId = '6793628df62026a414d9338e';
    this.updateUI();
  }

  handlePageEvent(event: PageEvent) {
    this.pageEvent = event;
    this.offset = event.pageIndex * event.pageSize;
    this.limit = event.pageSize;
    this.page = this.offset / this.limit;
    this.updateUI();
  }

  updateUI() {
    this.updateTotalScanCount(this.sessionId);
    this.updateTableData(this.sessionId);
  }

  updateTableData(sessionId: string) {
    this.scanData
      .getScanData(
        sessionId,
        this.offset,
        this.limit,
        this.displayedColumns,
        false,
        { scan_number: this.sorting }
      )
      .subscribe({
        next: (data) => {
          console.log('Received data: ', data);
          for (const entry of data) {
            if (entry.user_data && entry.user_data['user_rating']) {
              entry.user_rating = entry.user_data['user_rating'];
            }
          }
          this.tableData.set(data);
        },
        error: (error) => {
          console.error('Error fetching data: ', error);
        },
      });
  }

  updateTotalScanCount(sessionId: string) {
    this.scanCount.getScanCount(sessionId).subscribe({
      next: (data) => {
        console.log('Received data: ', data);
        this.totalScanCount = data.count;
      },
      error: (error) => {
        console.error('Error fetching data: ', error);
      },
    });
  }
}
