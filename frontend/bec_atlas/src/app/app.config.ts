import {
  ApplicationConfig,
  importProvidersFrom,
  inject,
  provideAppInitializer,
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
import { QueueTableComponent } from './queue-table/queue-table.component';

const gridconstructor = () => {
  GridstackComponent.addComponentToSelectorType([
    DeviceBoxComponent,
    QueueTableComponent,
  ]);
};

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    provideAnimationsAsync(),
    provideHttpClient(withInterceptorsFromDi()),
    provideAppInitializer(() => {
      let appConfigService = inject(AppConfigService);
      return appConfigService.loadAppConfig();
    }),
    AppConfigService,
    {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true,
    },
    importProvidersFrom(StarRatingModule.forRoot()),
    provideEnvironmentInitializer(gridconstructor),
  ],
};
