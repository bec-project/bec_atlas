import { TestBed } from '@angular/core/testing';

import { DeploymentService } from './deployment.service';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { AppConfigService } from './app-config.service';

describe('DeploymentService', () => {
  let service: DeploymentService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        DeploymentService,
        AppConfigService,
      ],
    });
    service = TestBed.inject(DeploymentService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
