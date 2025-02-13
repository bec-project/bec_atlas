import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SidePanelComponent } from './side-panel.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { AppConfigService } from '../../app-config.service';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { SessionDataService } from '../../core/remote-data.service';

describe('SidePanelComponent', () => {
  let component: SidePanelComponent;
  let fixture: ComponentFixture<SidePanelComponent>;
  let sessionDataServiceMock: any;

  sessionDataServiceMock = jasmine.createSpyObj('SessionDataService', ['getSessions']);
  sessionDataServiceMock.getSessions.and.returnValue(Promise.resolve([{ _id: '1', name: 'test'}]));

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideAnimationsAsync(),
        {provide: SessionDataService, useValue: sessionDataServiceMock},
      ],
      imports: [SidePanelComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(SidePanelComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should select sessionId', async () => {
    spyOn(component.sessionChanged, 'emit');
    component.onSessionChange(null);
    expect(component.selectedSession).toBeNull();
    expect(component.sessionChanged.emit).toHaveBeenCalledWith(null);
    component.onSessionChange({ _id: '1', name: 'test'});
    expect(component.selectedSession).toEqual({ _id: '1', name: 'test'});
    expect(component.sessionChanged.emit).toHaveBeenCalledWith({ _id: '1', name: 'test'});
  });
});
