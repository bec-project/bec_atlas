import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DeploymentSelectionComponent } from './deployment-selection.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { AppConfigService } from '../app-config.service';
import { MatDialogRef } from '@angular/material/dialog';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';

describe('DeploymentSelectionComponent', () => {
  let component: DeploymentSelectionComponent;
  let fixture: ComponentFixture<DeploymentSelectionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: MatDialogRef,
          useValue: {},
        },
        provideAnimationsAsync(),
        AppConfigService,
      ],
      imports: [DeploymentSelectionComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(DeploymentSelectionComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
