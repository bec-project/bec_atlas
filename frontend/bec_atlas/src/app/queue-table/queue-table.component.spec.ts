import { ComponentFixture, TestBed } from '@angular/core/testing';

import { QueueTableComponent } from './queue-table.component';
import { RedisConnectorService } from '../core/redis-connector.service';
import { AppConfigService } from '../app-config.service';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { DeploymentService } from '../deployment.service';

describe('QueueTableComponent', () => {
  let component: QueueTableComponent;
  let fixture: ComponentFixture<QueueTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        QueueTableComponent,
        RedisConnectorService,
        AppConfigService,
        provideHttpClient(),
        provideHttpClientTesting(),
        DeploymentService,
      ],
      imports: [QueueTableComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(QueueTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
