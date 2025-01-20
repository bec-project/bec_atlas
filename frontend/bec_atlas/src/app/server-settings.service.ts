import { Injectable } from '@angular/core';
import { AppConfigService } from './app-config.service';

@Injectable({
  providedIn: 'root',
})
export class ServerSettingsService {
  constructor(private appConfigService: AppConfigService) {}

  getServerAddress() {
    return (
      this.appConfigService.getConfig().baseUrl ?? 'http://localhost/api/v1/'
    );
  }

  getSocketAddress() {
    const baseUrl =
      this.appConfigService.getConfig().baseUrl ?? 'http://localhost/api/v1/';
    if (!baseUrl.startsWith('http'))
      throw new Error('BaseURL must use the http or https protocol');
    return `ws${baseUrl.substring(4)}`;
  }
}
