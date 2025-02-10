import { TestBed } from '@angular/core/testing';

import { RemoteDataService } from './remote-data.service';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { AppConfigService } from '../app-config.service';

describe('RemoteDataService', () => {
  let service: RemoteDataService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        RemoteDataService,
        AppConfigService,
      ],
    });
    service = TestBed.inject(RemoteDataService);
    const httpTesting = TestBed.inject(HttpTestingController);
    const appConfigService = TestBed.inject(AppConfigService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
