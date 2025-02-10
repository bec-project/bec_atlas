import { TestBed } from '@angular/core/testing';

import { ServerSettingsService } from './server-settings.service';
import { AppConfigService } from './app-config.service';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('ServerSettingsService', () => {
  let service: ServerSettingsService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        ServerSettingsService,
        AppConfigService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(ServerSettingsService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
