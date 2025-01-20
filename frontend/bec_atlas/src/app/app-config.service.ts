import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

export interface AppConfig {
  baseUrl?: string;
}
@Injectable()
export class AppConfigService {
  private appConfig: object | undefined = {};

  constructor(private http: HttpClient) {}

  async loadAppConfig(): Promise<void> {
    try {
      this.appConfig = await firstValueFrom(
        this.http.get('/assets/config.json')
      );
    } catch (err) {
      console.error('No config provided, applying defaults');
    }
  }

  getConfig(): AppConfig {
    return this.appConfig as AppConfig;
  }
}
