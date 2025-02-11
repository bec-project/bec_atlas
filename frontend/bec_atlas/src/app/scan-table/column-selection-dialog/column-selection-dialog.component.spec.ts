import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ColumnSelectionDialogComponent } from './column-selection-dialog.component';
import {
  MatDialogModule,
  MAT_DIALOG_DATA,
  MatDialogRef,
} from '@angular/material/dialog';

describe('ColumnSelectionDialogComponent', () => {
  let component: ColumnSelectionDialogComponent;
  let fixture: ComponentFixture<ColumnSelectionDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: [
            { name: 'column1', selected: true },
            { name: 'column2', selected: false },
          ],
        },
        {
          provide: MatDialogRef,
          useValue: {},
        },
      ],
      imports: [ColumnSelectionDialogComponent, MatDialogModule],
    }).compileComponents();

    fixture = TestBed.createComponent(ColumnSelectionDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
