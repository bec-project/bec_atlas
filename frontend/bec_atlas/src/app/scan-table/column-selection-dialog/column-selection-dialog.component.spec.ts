import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ColumnSelectionDialogComponent } from './column-selection-dialog.component';
import {
  MatDialogModule,
  MAT_DIALOG_DATA,
  MatDialogRef,
} from '@angular/material/dialog';

import { MatCheckboxChange } from '@angular/material/checkbox';

describe('ColumnSelectionDialogComponent', () => {
  let component: ColumnSelectionDialogComponent;
  let fixture: ComponentFixture<ColumnSelectionDialogComponent>;
  let dialogRefSpy: jasmine.SpyObj<MatDialogRef<ColumnSelectionDialogComponent>>;

  beforeEach(async () => {

    dialogRefSpy = jasmine.createSpyObj<MatDialogRef<ColumnSelectionDialogComponent>>(['close']);

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
          useValue: dialogRefSpy,
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

  it('should update the selected columns', () => {
    component.columns = [
      { name: 'column1', selected: true },
      { name: 'column2', selected: false },
    ];
    let checkbox_changed = new MatCheckboxChange();
    checkbox_changed.checked = true;
    component.handleCheckboxChecked(checkbox_changed, 1);
    expect(component.columns).toEqual([
      { name: 'column1', selected: true },
      { name: 'column2', selected: true },
    ]);
  });

  it('should close dialog on cancel, no data', () => {
    component.onCancelClick();
    expect(dialogRefSpy.close).toHaveBeenCalledWith(null);
  });

  it('should close dialog on apply, with data', () => {
    component.columns = [
      { name: 'column1', selected: true },
      { name: 'column2', selected: false },
    ];
    component.onApplyClick();
    expect(dialogRefSpy.close).toHaveBeenCalledWith(['column1']);
  });

});
