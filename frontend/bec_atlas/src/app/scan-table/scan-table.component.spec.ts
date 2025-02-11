import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ScanTableComponent } from './scan-table.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { AppConfigService } from '../app-config.service';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';

describe('ScanTableComponent', () => {
  let component: ScanTableComponent;
  let fixture: ComponentFixture<ScanTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimationsAsync(),
        AppConfigService,
      ],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ScanTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // Add more tests here
});
