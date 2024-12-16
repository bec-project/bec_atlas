import { ComponentFixture, TestBed } from '@angular/core/testing';

import { GridstackTestComponent } from './gridstack-test.component';

describe('GridstackTestComponent', () => {
  let component: GridstackTestComponent;
  let fixture: ComponentFixture<GridstackTestComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GridstackTestComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(GridstackTestComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
