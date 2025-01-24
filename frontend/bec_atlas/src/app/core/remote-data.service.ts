import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { ServerSettingsService } from '../server-settings.service';
import { ScanDataResponse } from './model/scan-data';

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

@Injectable({
  providedIn: 'root',
})
export class ScanDataService extends RemoteDataService {
  /**
   * Method for getting the scan data
   * @param sessionId Unique identifier for the session
   * @param offset Pagination offset (default = 0)
   * @param limit Number of records to retrieve (default = 100)
   * @param fields List of fields to include in the response
   * @param includeUserData Whether to include user-related data
   * @param sort Sort order for the records as a dictionary
   * @returns response from the server with the scan data
   * @throws HttpErrorResponse if the request fails
   * @throws TimeoutError if the request takes too long
   */
  getScanData(sessionId: string, offset:number = 0, limit:number = 100, fields: Array<string> |null = null, includeUserData: boolean = false, sort: { [key: string]: number } | null = null) {
    let headers = new HttpHeaders();
    headers = headers.set('Content-Type', 'application/json; charset=utf-8');
    return this.get<Array<ScanDataResponse>>(
      "scans/session",
      { 
        session_id : sessionId, 
        offset : offset.toString(), 
        limit : limit.toString(), 
        fields: fields ? fields.join(',') : "",
        sort: sort ? JSON.stringify(sort) : "",
        includeUserData: includeUserData.toString() 
      },
      headers
    )
  }
}
