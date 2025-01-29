import { ComponentFixture, TestBed } from '@angular/core/testing';

import { OverviewGridComponent } from './overview-grid.component';

describe('OverviewGridComponent', () => {
  let component: OverviewGridComponent;
  let fixture: ComponentFixture<OverviewGridComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [OverviewGridComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(OverviewGridComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
