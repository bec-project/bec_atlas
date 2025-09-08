import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { BreakpointObserver } from '@angular/cdk/layout';
import { of, Subject } from 'rxjs';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { DashboardComponent } from './dashboard.component';
import { DeploymentService } from '../deployment.service';
import { AuthDataService } from '../core/remote-data.service';
import { RedisConnectorService } from '../core/redis-connector.service';
import { AppConfigService } from '../app-config.service';
import { DeploymentSelectionComponent } from '../deployment-selection/deployment-selection.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

describe('DashboardComponent', () => {
  let component: DashboardComponent;
  let fixture: ComponentFixture<DashboardComponent>;
  let mockRouter: jasmine.SpyObj<Router>;
  let mockDialog: jasmine.SpyObj<MatDialog>;
  let mockDeploymentService: jasmine.SpyObj<DeploymentService>;
  let mockAuthDataService: jasmine.SpyObj<AuthDataService>;

  beforeEach(async () => {
    const routerSpy = jasmine.createSpyObj('Router', ['navigate']);
    const deploymentSpy = jasmine.createSpyObj('DeploymentService', [
      'selectDeployment',
    ]);
    const authSpy = jasmine.createSpyObj('AuthDataService', ['logout']);
    const breakpointSpy = jasmine.createSpyObj('BreakpointObserver', [
      'observe',
    ]);
    const dialogSpy = jasmine.createSpyObj('MatDialog', ['open'], {
      openDialogs: [],
      afterOpened: new Subject(),
      afterAllClosed: new Subject(),
      _getAfterAllClosed: () => new Subject(),
    });

    breakpointSpy.observe.and.returnValue(
      of({ matches: false, breakpoints: {} })
    );
    dialogSpy.open.and.returnValue({
      afterClosed: () => of(null),
      close: () => {},
      componentInstance: {},
      id: 'test-dialog',
    } as any);

    await TestBed.configureTestingModule({
      imports: [
        DashboardComponent,
        DeploymentSelectionComponent,
        NoopAnimationsModule,
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        AppConfigService,
        { provide: Router, useValue: routerSpy },
        { provide: MatDialog, useValue: dialogSpy },
        { provide: BreakpointObserver, useValue: breakpointSpy },
        { provide: DeploymentService, useValue: deploymentSpy },
        { provide: AuthDataService, useValue: authSpy },
        { provide: RedisConnectorService, useValue: {} },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    mockRouter = TestBed.inject(Router) as jasmine.SpyObj<Router>;
    mockDialog = TestBed.inject(MatDialog) as jasmine.SpyObj<MatDialog>;
    mockDeploymentService = TestBed.inject(
      DeploymentService
    ) as jasmine.SpyObj<DeploymentService>;
    mockAuthDataService = TestBed.inject(
      AuthDataService
    ) as jasmine.SpyObj<AuthDataService>;

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize with default values', () => {
    expect(component.selectedNavItem()).toBe('analytics');
    expect(component.selectedSubItem()).toBe('reports');
    expect(component.showNavPanel()).toBe(true);
    expect(component.isMobile()).toBe(false);
  });

  it('should have navigation items', () => {
    expect(component.navItems.length).toBe(4);
    const navItemIds = component.navItems.map((item) => item.id);
    expect(navItemIds).toEqual(['analytics', 'data', 'control', 'settings']);
  });

  it('should get current navigation content', () => {
    component.selectedNavItem.set('data');
    const currentNav = component.getCurrentNavContent();

    expect(currentNav?.id).toBe('data');
    expect(currentNav?.label).toBe('Data Browser');
  });

  it('should toggle navigation panel', () => {
    component.showNavPanel.set(true);
    component.toggleNavPanel();
    expect(component.showNavPanel()).toBe(false);
  });

  it('should select navigation item', () => {
    const dataItem = component.navItems.find((item) => item.id === 'data')!;
    component.selectNavItem(dataItem);

    expect(component.selectedNavItem()).toBe('data');
    expect(component.showNavPanel()).toBe(true);
  });

  it('should navigate to child', () => {
    const child = { id: 'scan-data', label: 'Scan Data', icon: 'scatter_plot' };
    component.navigateToChild(child);

    expect(component.selectedSubItem()).toBe('scan-data');
  });

  it('should call logout and navigate', () => {
    component.logout();

    expect(mockAuthDataService.logout).toHaveBeenCalled();
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/login']);
  });

  it('should open deployment dialog', () => {
    // Spy on the actual dialog service the component uses
    spyOn(component['dialog'], 'open').and.returnValue({
      afterClosed: () => of(null),
      close: () => {},
      componentInstance: {},
      id: 'test-dialog',
    } as any);

    component.openDeploymentDialog();

    expect(component['dialog'].open).toHaveBeenCalledWith(
      DeploymentSelectionComponent,
      jasmine.objectContaining({
        disableClose: true,
        maxWidth: '95vw',
      })
    );
  });

  it('should render main layout', () => {
    const compiled = fixture.nativeElement;
    expect(compiled.querySelector('.dashboard-layout')).toBeTruthy();
    expect(compiled.querySelector('.icon-sidebar')).toBeTruthy();
  });
});
