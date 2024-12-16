import { TestBed } from '@angular/core/testing';

import { RedisConnectorService } from './redis-connector.service';

describe('RedisConnectorService', () => {
  let service: RedisConnectorService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(RedisConnectorService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
