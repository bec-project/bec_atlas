import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ColumnSelectionDialogComponent } from './column-selection-dialog.component';

describe('ColumnSelectionDialogComponent', () => {
  let component: ColumnSelectionDialogComponent;
  let fixture: ComponentFixture<ColumnSelectionDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ColumnSelectionDialogComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ColumnSelectionDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
