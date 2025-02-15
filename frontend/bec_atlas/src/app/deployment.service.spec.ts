import { TestBed } from '@angular/core/testing';
import { DeploymentService } from './deployment.service';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { AppConfigService } from './app-config.service';
import { Deployment } from './core/model/deployment';
import { DeploymentDataService } from './core/remote-data.service';

describe('DeploymentService', () => {
  let service: DeploymentService;
  let deploymentDataService: jasmine.SpyObj<DeploymentDataService>;

  const mockDeployment: Deployment = {
    _id: 'test-id',
    name: 'Test Deployment',
  } as Deployment;

  beforeEach(() => {
    const spy = jasmine.createSpyObj('DeploymentDataService', [
      'getDeployment',
    ]);
    spy.getDeployment.and.returnValue(Promise.resolve(mockDeployment));

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        DeploymentService,
        AppConfigService,
        { provide: DeploymentDataService, useValue: spy },
      ],
    });
    service = TestBed.inject(DeploymentService);
    deploymentDataService = TestBed.inject(
      DeploymentDataService
    ) as jasmine.SpyObj<DeploymentDataService>;
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should update deployment when valid ID is provided', async () => {
    await service.update_deployment('test-id');
    expect(deploymentDataService.getDeployment).toHaveBeenCalledWith('test-id');
    expect(service.selectedDeployment.value).toEqual(mockDeployment);
  });

  it('should clear selected deployment when null ID is provided', async () => {
    await service.update_deployment(null);
    expect(service.selectedDeployment.value).toBeNull();
  });

  it('should save deployment to session storage when selecting deployment', () => {
    spyOn(sessionStorage, 'setItem');
    service.selectDeployment(mockDeployment);
    expect(sessionStorage.setItem).toHaveBeenCalledWith(
      'selected_deployment',
      'test-id'
    );
    expect(service.selectedDeployment.value).toEqual(mockDeployment);
  });

  it('should remove deployment from session storage when clearing selection', () => {
    spyOn(sessionStorage, 'removeItem');
    service.selectDeployment(null);
    expect(sessionStorage.removeItem).toHaveBeenCalledWith(
      'selected_deployment'
    );
    expect(service.selectedDeployment.value).toBeNull();
  });
});
