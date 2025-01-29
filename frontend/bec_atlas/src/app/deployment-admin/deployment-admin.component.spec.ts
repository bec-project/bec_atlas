import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DeploymentAdminComponent } from './deployment-admin.component';

describe('DeploymentAdminComponent', () => {
  let component: DeploymentAdminComponent;
  let fixture: ComponentFixture<DeploymentAdminComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DeploymentAdminComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(DeploymentAdminComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
