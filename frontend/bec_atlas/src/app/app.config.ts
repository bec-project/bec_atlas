import {
  APP_INITIALIZER,
  ApplicationConfig,
  importProvidersFrom,
  provideEnvironmentInitializer,
  provideZoneChangeDetection,
} from '@angular/core';
import { provideRouter } from '@angular/router';

import { routes } from './app.routes';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { AppConfigService } from './app-config.service';
import {
  HTTP_INTERCEPTORS,
  provideHttpClient,
  withInterceptorsFromDi,
} from '@angular/common/http';
import { AuthInterceptor } from './core/auth.interceptor';
import { StarRatingModule } from 'angular-star-rating';
import { GridstackComponent } from 'gridstack/dist/angular';
import { DeviceBoxComponent } from './device-box/device-box.component';

const appConfigInitializerFn = (appConfig: AppConfigService) => {
  return () => appConfig.loadAppConfig();
};

const gridconstructor = () => {
  GridstackComponent.addComponentToSelectorType([DeviceBoxComponent]);
};

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    provideAnimationsAsync(),
    provideHttpClient(withInterceptorsFromDi()),
    AppConfigService,
    {
      provide: APP_INITIALIZER,
      useFactory: appConfigInitializerFn,
      deps: [AppConfigService],
      multi: true,
    },
    {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true,
    },
    importProvidersFrom(StarRatingModule.forRoot()),
    provideEnvironmentInitializer(gridconstructor),
  ],
};
