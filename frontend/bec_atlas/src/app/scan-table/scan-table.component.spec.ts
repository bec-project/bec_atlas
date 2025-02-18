import { ComponentFixture, TestBed} from '@angular/core/testing';
import { ScanTableComponent } from './scan-table.component';
import { provideAnimationsAsync} from '@angular/platform-browser/animations/async';
import {ScanDataService, SessionDataService} from '../core/remote-data.service';
import { MatDialogModule } from '@angular/material/dialog';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule } from '@angular/material/paginator';

describe('ScanTableComponent', () => {
  let component: ScanTableComponent;
  let fixture: ComponentFixture<ScanTableComponent>;
  let scanDataServiceMock: any;
  let sessionDataServiceMock: any;

  beforeEach(async () => {

    sessionDataServiceMock = jasmine.createSpyObj('SessionDataService', ['getSessions']);
    sessionDataServiceMock.getSessions.and.returnValue(Promise.resolve([{ _id: '1', name: 'test'}]));
    scanDataServiceMock = jasmine.createSpyObj('ScanDataService', ['getScanData', 'getScanCount', 'updateUserData']);
    scanDataServiceMock.getScanCount.and.returnValue(Promise.resolve({count: 5}));
    scanDataServiceMock.getScanData.and.returnValue(Promise.resolve([
      { scan_id: '1', scan_number: 1, status: 'open'},
      { scan_id: '2', scan_number: 2, status: 'closed'},
      { scan_id: '3', scan_number: 3, status: 'closed'},
      { scan_id: '4', scan_number: 4, status: 'closed'},
      { scan_id: '5', scan_number: 5, status: 'closed'}
    ]));
    scanDataServiceMock.updateUserData.and.returnValue(Promise.resolve('1'));

    await TestBed.configureTestingModule({
      imports: [MatTableModule, MatPaginatorModule, MatDialogModule],
      providers: [
        provideAnimationsAsync(),
        // { provide: ScanDataService, useValue: MockScanDataService },
        { provide: SessionDataService, useValue: sessionDataServiceMock },
        { provide: ScanDataService, useValue: scanDataServiceMock },
      ],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ScanTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', async () => {
    await fixture.whenStable();
    expect(component).toBeTruthy();
  });

  it('should select sessionId', async () => {
    await fixture.whenStable();
    component.onSessionChange({ _id: '1', name: 'test'});
    await fixture.whenStable();
    expect(component.session()).toEqual({ _id: '1', name: 'test'});
  });

  it('should get scan data', async () => {
    component.displayedColumns.set(['scan_id', 'scan_number', 'status']);
    // await fixture.whenRenderingDone();
    component.onSessionChange({ _id: '1', name: 'test'});
    await fixture.detectChanges();
    expect(component.totalScanCount()).toEqual(5);
    expect(component.tableData().length).toEqual(5);
  });

  it('should handle offset and limit changes', async () => {
    let columns = ['scan_id', 'scan_number', 'status'];
    component.displayedColumns.set(columns);
    component.onSessionChange({ _id: '1', name: 'test'});
    component.offset.set(4);
    component.limit.set(1);
    await fixture.detectChanges();
    expect(scanDataServiceMock.getScanData).toHaveBeenCalledWith('1', 4, 1, columns, false, { scan_number: component.sorting });
    });

  it('should handle page changes', async () => {
    let columns = ['scan_id', 'scan_number', 'status'];
    component.displayedColumns.set(columns);
    component.onSessionChange({ _id: '1', name: 'test'});
    component.handlePageEvent({pageIndex: 1, pageSize: 1, length: 5});
    await fixture.detectChanges();
    expect(component.offset()).toEqual(1);
    expect(component.limit()).toEqual(1);
    expect(scanDataServiceMock.getScanData).toHaveBeenCalledWith('1', 1, 1, columns, false, { scan_number: component.sorting });
  });

  it('should handle refresh', async () => {
    component.handleRefresh();
    await fixture.detectChanges();
    expect(scanDataServiceMock.getScanData).toHaveBeenCalled();
    expect(scanDataServiceMock.getScanCount).toHaveBeenCalled();
  });

  it('should change star rating', async () => {
    let columns = ['scan_id', 'scan_number', 'status'];
    component.displayedColumns.set(columns);
    component.onSessionChange({ _id: '1', name: 'test'});
    await component.handleOnRatingChanged({rating : 3}, { scan_id: '1', scan_number: 1, status: 'open'});
    expect(scanDataServiceMock.updateUserData).toHaveBeenCalledWith('1', { user_rating: 3 , user_comments: '', system_rating: 0, system_comments: '', name: ''});
  });
});
