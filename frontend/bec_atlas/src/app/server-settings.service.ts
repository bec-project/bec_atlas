import { Injectable } from '@angular/core';
import { AppConfigService } from './app-config.service';

@Injectable({
  providedIn: 'root',
})
export class ServerSettingsService {
  constructor(private appConfigService: AppConfigService) {}

  getServerAddress() {
    return (
      this.appConfigService.getConfig().baseUrl ?? 'http://localhost/api/v1'
    );
  }

  getSocketAddress() {
    let out = this.appConfigService.getConfig().wsUrl ?? 'http://localhost';
    console.log(out);
    return out;
  }
}
