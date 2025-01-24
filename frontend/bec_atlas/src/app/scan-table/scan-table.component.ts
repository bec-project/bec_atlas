import { ChangeDetectionStrategy, Component, WritableSignal, signal, ViewChild } from '@angular/core';
import { ScanDataService } from '../core/remote-data.service';
import { ScanDataResponse } from '../core/model/scan-data';
import { firstValueFrom } from 'rxjs';
import { CommonModule } from '@angular/common';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { StarRatingModule } from 'angular-star-rating';


@Component({
  selector: 'app-scan-table',
  standalone: true,
  imports: [CommonModule, MatPaginator, MatTableModule, MatIconModule, MatToolbarModule, MatCardModule, MatButtonModule, MatPaginatorModule, StarRatingModule],
  templateUrl: './scan-table.component.html',
  styleUrl: './scan-table.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ScanTableComponent {
  tableData: WritableSignal<ScanDataResponse[]> = signal([]);  // Initialize as empty array
  limit: number = 100;
  offset: number = 0;
  displayedColumns: string[] = ['scan_number', 'status', 'num_points', 'scan_name', 'scan_type', 'dataset_number', 'timestamp', 'user_rating'];
  ignoredEntries: string[] = ['scan_report_devices', 'user_metadata', 'readout_priority', 'scan_parameters', 'request_inputs', 'info'];

  @ViewChild(MatPaginatorModule) paginator!: MatPaginatorModule;

  constructor(private scanData: ScanDataService) {}

  ngOnInit(): void {
    let sessionId = '6793628df62026a414d9338e';
    this.updateTableData(sessionId);
  }

  async updateTableData(sessionId: string) {
    let data = await firstValueFrom(
      this.scanData.getScanData(sessionId, this.offset, this.limit, this.displayedColumns, false, { scan_number: -1 })
    );
    console.log('Received data: ', data);
    for (const entry of data) {
      if (entry.user_data && entry.user_data['user_rating'])
      {
        entry.user_rating = entry.user_data['user_rating'];
      }
    }
    console.log('Received data: ', data);
    this.tableData.set(data);  // Update the signal value
  }
}


// @Component({
//   selector: 'app-scan-table',
//   standalone: true,
//   imports: [CommonModule, MatPaginator, MatTableModule, MatIconModule, MatToolbarModule, MatCardModule, MatButtonModule, MatPaginatorModule],
//   templateUrl: './scan-table.component.html',
//   styleUrl: './scan-table.component.scss',
//   changeDetection: ChangeDetectionStrategy.OnPush,
// })
// export class ScanTableComponent {
//   tableData!: Promise<ScanDataResponse[]>;
//   limit: number = 100;
//   offset: number = 0;
//   displayedColumns: string[] = ['scan_number', 'status', "num_points", "scan_name", "scan_type", "dataset_number", "timestamp", "user_rating"];
//   ignoredEntries: string[] = ["scan_report_devices", "user_metadata", "readout_priority", "scan_parameters", "request_inputs", "info"];
//   // , "scan_name", "scan_type"]; 
  
//   @ViewChild(MatPaginatorModule) paginator!: MatPaginatorModule;

//   constructor( private scanData: ScanDataService) {

//   }

//   ngOnInit(): void {
    
//     let sessionId = "6793628df62026a414d9338e";
//     this.tableData = this.updateTableData(sessionId = "6793628df62026a414d9338e");
//     // this.tableData = this.scanData.getScanData(sessionId = "6793628df62026a414d9338e");
//   }

//   async updateTableData(sessionId: string, offset: number = 0, limit: number = 100) {
//     const data = await firstValueFrom(this.scanData.getScanData(sessionId=sessionId, offset=this.offset, limit=this.limit, this.displayedColumns, false, {"scan_number": -1}));
//     console.log("Received data: ", data);
//     // this.tableData = data;
//     return data;
//   }
// }
