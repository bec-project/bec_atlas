import { ComponentFixture, TestBed } from '@angular/core/testing';

import { GridStackTestComponent } from './gridstack-test.component';

describe('GridstackTestComponent', () => {
  let component: GridStackTestComponent;
  let fixture: ComponentFixture<GridStackTestComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GridStackTestComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(GridStackTestComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
