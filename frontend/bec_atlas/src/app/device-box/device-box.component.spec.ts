import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DeviceBoxComponent } from './device-box.component';
import { RedisConnectorService } from '../core/redis-connector.service';
import { AppConfigService } from '../app-config.service';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { DeploymentService } from '../deployment.service';

describe('DeviceBoxComponent', () => {
  let component: DeviceBoxComponent;
  let fixture: ComponentFixture<DeviceBoxComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        DeviceBoxComponent,
        RedisConnectorService,
        AppConfigService,
        provideHttpClient(),
        provideHttpClientTesting(),
        DeploymentService,
      ],
      imports: [DeviceBoxComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(DeviceBoxComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
