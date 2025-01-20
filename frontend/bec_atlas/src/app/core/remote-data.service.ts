import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { ServerSettingsService } from '../server-settings.service';

@Injectable({
  providedIn: 'root',
})
export class RemoteDataService {
  constructor(
    private httpClient: HttpClient,
    private serverSettings: ServerSettingsService
  ) {}

  /**
   * Base method for making a POST request to the server
   * @param path path to the endpoint
   * @param payload payload to send
   * @param headers additional headers
   * @returns response from the server
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  protected post<T>(path: string, payload: any, headers: HttpHeaders) {
    return this.httpClient.post<T>(
      this.serverSettings.getServerAddress() + path,
      payload,
      {
        headers,
      }
    );
  }

  /**
   * Base method for making a GET request to the server
   * @param path path to the endpoint
   * @param params query parameters
   * @param headers additional headers
   * @returns response from the server
   */
  protected get<T>(
    path: string,
    params: { [key: string]: string },
    headers: HttpHeaders
  ) {
    return this.httpClient.get<T>(
      this.serverSettings.getServerAddress() + path,
      {
        headers,
        params,
      }
    );
  }
}

@Injectable({
  providedIn: 'root',
})
export class AuthDataService extends RemoteDataService {
  /**
   * Method for logging into BEC
   * @param principal username or email
   * @param password password
   * @returns response from the server with the token
   * @throws HttpErrorResponse if the request fails
   * @throws TimeoutError if the request takes too long
   */
  login(username: string, password: string) {
    let headers = new HttpHeaders();
    headers = headers.set('Content-Type', 'application/json; charset=utf-8');
    return this.post<string>(
      'user/login',
      { username: username, password: password },
      headers
    );
  }
}
