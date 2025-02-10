import { TestBed } from '@angular/core/testing';

import { RedisConnectorService } from './redis-connector.service';
import { AppConfigService } from '../app-config.service';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { DeploymentService } from '../deployment.service';

describe('RedisConnectorService', () => {
  let service: RedisConnectorService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        RedisConnectorService,
        DeploymentService,
        AppConfigService,
      ],
    });
    service = TestBed.inject(RedisConnectorService);
    const appConfigService = TestBed.inject(AppConfigService);
    const httpTesting = TestBed.inject(HttpTestingController);
    const deploymentService = TestBed.inject(DeploymentService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
