import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ScanTableComponent } from './scan-table.component';

describe('ScanTableComponent', () => {
  let component: ScanTableComponent;
  let fixture: ComponentFixture<ScanTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ScanTableComponent],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ScanTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // Add more tests here
});
