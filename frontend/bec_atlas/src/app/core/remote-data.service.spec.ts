import { TestBed } from '@angular/core/testing';

import {
  DeploymentDataService,
  RemoteDataService,
  ScanDataService,
  SessionDataService,
} from './remote-data.service';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { AppConfigService } from '../app-config.service';
import { ScanDataResponse } from './model/scan-data';
import { ScanUserData } from './model/scan-user-data';
import { Deployment } from './model/deployment';

describe('RemoteDataService', () => {
  let service: RemoteDataService;

  let httpTesting: HttpTestingController;
  let appConfigService: AppConfigService;

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
    httpTesting = TestBed.inject(HttpTestingController);
    appConfigService = TestBed.inject(AppConfigService);
  });

  afterEach(() => {
    httpTesting.verify(); // Verify that no unmatched requests are outstanding
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should get sessions with default parameters', async () => {
    const mockSessions = [
      {
        _id: '1',
        name: 'Session 1',
        owner_groups: ['group1'],
        access_groups: ['group2'],
      },
      { _id: '2', name: 'Session 2' },
    ];

    const sessionService = TestBed.inject(SessionDataService);
    const promise = sessionService.getSessions();

    const req = httpTesting.expectOne((request) =>
      request.url.includes('sessions')
    );
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('offset')).toBe('0');
    expect(req.request.params.get('limit')).toBe('100');

    req.flush(mockSessions);

    const result = await promise;
    expect(result).toEqual(mockSessions);
  });

  it('should get sessions with custom offset and limit', async () => {
    const mockSessions = [
      {
        _id: '1',
        name: 'Session 1',
        owner_groups: ['group1'],
        access_groups: ['group2'],
      },
      { _id: '2', name: 'Session 2' },
    ];

    const sessionService = TestBed.inject(SessionDataService);
    const promise = sessionService.getSessions(10, 5);

    const req = httpTesting.expectOne((request) =>
      request.url.includes('sessions')
    );
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('offset')).toBe('10');
    expect(req.request.params.get('limit')).toBe('5');

    req.flush(mockSessions);

    const result = await promise;
    expect(result).toEqual(mockSessions);
  });

  it('should get scan data with default parameters', async () => {
    const mockScanData: ScanDataResponse[] = [
      {
        scan_id: '1',
        scan_number: 1,
        status: 'closed',
        session_id: 'session1',
        scan_name: 'Scan 1',
        scan_type: 'step',
        dataset_number: 1,
      },
      {
        scan_id: '2',
        scan_number: 2,
        status: 'open',
        session_id: 'session1',
        scan_name: 'Scan 2',
        scan_type: 'fly',
        dataset_number: 2,
      },
    ];

    const scanService = TestBed.inject(ScanDataService);
    const promise = scanService.getScanData('session1');

    const req = httpTesting.expectOne((request) =>
      request.url.includes('scans/session')
    );
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('session_id')).toBe('session1');
    expect(req.request.params.get('offset')).toBe('0');
    expect(req.request.params.get('limit')).toBe('100');
    expect(req.request.params.get('fields')).toBe('');
    expect(req.request.params.get('sort')).toBe('');
    expect(req.request.params.get('includeUserData')).toBe('false');

    req.flush(mockScanData);

    const result = await promise;
    expect(result).toEqual(mockScanData);
  });

  it('should get scan data with custom parameters', async () => {
    const mockScanData: ScanDataResponse[] = [
      {
        scan_id: '1',
        scan_number: 1,
        status: 'closed',
        session_id: 'session1',
        scan_name: 'Scan 1',
        scan_type: 'step',
        dataset_number: 1,
        user_metadata: { important: true },
        timestamp: 1234567890,
      },
    ];

    const scanService = TestBed.inject(ScanDataService);
    const promise = scanService.getScanData(
      'session1',
      10,
      5,
      ['field1', 'field2'],
      true,
      { timestamp: -1 }
    );

    const req = httpTesting.expectOne((request) =>
      request.url.includes('scans/session')
    );
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('session_id')).toBe('session1');
    expect(req.request.params.get('offset')).toBe('10');
    expect(req.request.params.get('limit')).toBe('5');
    expect(req.request.params.getAll('fields')).toEqual(['field1', 'field2']);
    expect(req.request.params.get('sort')).toBe('{"timestamp":-1}');
    expect(req.request.params.get('includeUserData')).toBe('true');

    req.flush(mockScanData);

    const result = await promise;
    expect(result).toEqual(mockScanData);
  });

  it('should get scan count with all parameters', async () => {
    const mockResponse = { count: 42 };

    const scanService = TestBed.inject(ScanDataService);
    const promise = scanService.getScanCount('session1', 'scan1', 123);

    const req = httpTesting.expectOne((request) =>
      request.url.includes('scans/count')
    );
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('session_id')).toBe('session1');
    expect(req.request.params.get('scan_name')).toBe('scan1');
    expect(req.request.params.get('dataset_number')).toBe('123');

    req.flush(mockResponse);

    const result = await promise;
    expect(result).toEqual(mockResponse);
  });

  it('should get scan count with no parameters', async () => {
    const mockResponse = { count: 100 };

    const scanService = TestBed.inject(ScanDataService);
    const promise = scanService.getScanCount();

    const req = httpTesting.expectOne((request) =>
      request.url.includes('scans/count')
    );
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('session_id')).toBeNull();
    expect(req.request.params.get('scan_name')).toBeNull();
    expect(req.request.params.get('dataset_number')).toBeNull();

    req.flush(mockResponse);

    const result = await promise;
    expect(result).toEqual(mockResponse);
  });

  it('should update user data', async () => {
    const mockResponse = 'success';
    const mockUserData: ScanUserData = {
      name: 'Test Scan',
      user_rating: 3,
      system_rating: 0,
    };

    const scanService = TestBed.inject(ScanDataService);
    const promise = scanService.updateUserData('scan1', mockUserData);

    const req = httpTesting.expectOne((request) =>
      request.url.includes('scans/user_data')
    );
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual(mockUserData);

    req.flush(mockResponse);

    const result = await promise;
    expect(result).toBe(mockResponse);
  });

  it('should get deployments', async () => {
    const mockDeployments: Deployment[] = [
      {
        _id: '1',
        realm_id: 'realm1',
        name: 'Deployment 1',
        owner_groups: ['group1'],
        access_groups: ['group2'],
        config_templates: ['template1'],
      },
      {
        _id: '2',
        realm_id: 'realm2',
        name: 'Deployment 2',
        owner_groups: ['group3'],
        access_groups: ['group4'],
        config_templates: ['template2'],
      },
    ];

    const deploymentService = TestBed.inject(DeploymentDataService);
    const promise = deploymentService.getDeployments();

    const req = httpTesting.expectOne((request) =>
      request.url.includes('deployments')
    );
    expect(req.request.method).toBe('GET');
    expect(req.request.params.keys().length).toBe(0);

    req.flush(mockDeployments);

    const result = await promise;
    expect(result).toEqual(mockDeployments);
  });

  it('should get deployment by id', async () => {
    const mockDeployment: Deployment = {
      _id: '1',
      realm_id: 'realm1',
      name: 'Deployment 1',
      owner_groups: ['group1'],
      access_groups: ['group2'],
      config_templates: ['template1'],
    };

    const deploymentService = TestBed.inject(DeploymentDataService);
    const promise = deploymentService.getDeployment('1');

    const req = httpTesting.expectOne((request) =>
      request.url.includes('deployments/id')
    );
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('deployment_id')).toBe('1');

    req.flush(mockDeployment);

    const result = await promise;
    expect(result).toEqual(mockDeployment);
  });
});
