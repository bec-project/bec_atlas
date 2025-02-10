import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DeploymentSelectionComponent } from './deployment-selection.component';

describe('DeploymentSelectionComponent', () => {
  let component: DeploymentSelectionComponent;
  let fixture: ComponentFixture<DeploymentSelectionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DeploymentSelectionComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(DeploymentSelectionComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
