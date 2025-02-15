import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { Session } from './model/session';
import { ServerSettingsService } from '../server-settings.service';
import { ScanDataResponse } from './model/scan-data';
import { Realm } from './model/realm';
import { Deployment } from './model/deployment';
import { ScanCountResponse } from './model/scan-count';
import { ScanUserData } from './model/scan-user-data';

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
    params: { [key: string]: string | number | Array<string> } | HttpParams,
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

  /**
   * Base method for making a PATCH request to the server
   * @param path path to the endpoint
   * @param paramId unique identifier for the resource
   * @param payload payload to send
   * @param headers additional headers
   * @returns response from the server
   */
  protected patch<T>(
    path: string,
    paramInput: Record<string, string>,
    payload: any,
    headers: HttpHeaders
  ) {
    let param = Object.keys(paramInput);
    let id = paramInput[param[0]];
    let fullPath =
      this.serverSettings.getServerAddress() + path + '?' + param[0] + '=' + id;
    console.log('Full path', fullPath, 'payload', payload);

    return this.httpClient.patch<T>(fullPath, payload, {
      headers,
    });
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
export class RealmDataService extends RemoteDataService {
  getRealmsWithDeploymentAccess(only_owner: boolean = false) {
    let headers = new HttpHeaders();
    headers = headers.set('Content-Type', 'application/json; charset=utf-8');
    return this.get<Array<Realm>>(
      'realms/deployment_access',
      { only_owner: only_owner.toString() },
      headers
    );
  }
}

@Injectable({
  providedIn: 'root',
})
export class DeploymentDataService extends RemoteDataService {
  getDeployments() {
    let headers = new HttpHeaders();
    headers = headers.set('Content-Type', 'application/json; charset=utf-8');
    return this.get<Array<Deployment>>('deployments', {}, headers);
  }

  getDeployment(deploymentId: string) {
    let headers = new HttpHeaders();
    headers = headers.set('Content-Type', 'application/json; charset=utf-8');
    return this.get<Deployment>(
      'deployments/id',
      { deployment_id: deploymentId },
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
  getScanData(
    sessionId: string,
    offset: number = 0,
    limit: number = 100,
    fields: Array<string> | null = null,
    includeUserData: boolean = false,
    sort: { [key: string]: number } | null = null
  ): Promise<Array<ScanDataResponse>> {
    let headers = new HttpHeaders();
    headers = headers.set('Content-Type', 'application/json; charset=utf-8');
    return firstValueFrom(
      this.get<Array<ScanDataResponse>>(
        'scans/session',
        {
          session_id: sessionId,
          offset: offset.toString(),
          limit: limit.toString(),
          fields: fields ? fields : '',
          sort: sort ? JSON.stringify(sort) : '',
          includeUserData: includeUserData.toString(),
        },
        headers
      )
    );
  }
  /**
   * Method for getting the scan count
   * @param sessionId Unique identifier for the session (Optional)
   * @param scanName Name of the scan (Optional)
   * @param datasetNumber Dataset number (Optional)
   * @returns response from the server with the scan count
   * @throws HttpErrorResponse if the request fails
   * @throws TimeoutError if the request takes too long
   * @throws Error if the response is not a number
   */
  getScanCount(
    sessionId: string | null = null,
    scanName: string | null = null,
    datasetNumber: number | null = null
  ): Promise<ScanCountResponse> {
    let headers = new HttpHeaders();
    let filters: { [key: string]: string | number } = {};
    headers = headers.set('Content-Type', 'application/json; charset=utf-8');
    if (sessionId !== null) {
      filters['session_id'] = sessionId;
    }
    if (scanName !== null) {
      filters['scan_name'] = scanName;
    }
    if (datasetNumber !== null) {
      filters['dataset_number'] = datasetNumber;
    }
    return firstValueFrom(
      this.get<ScanCountResponse>('scans/count', filters, headers)
    );
  }

  /**
   * Method for updating the user data for a scan
   * @param scanId Unique identifier for the scan, type string
   * @param userData User data to update, type ScanUserData
   * @returns response from the server
   * @throws HttpErrorResponse if the request fails
   * @throws TimeoutError if the request takes too long
   */
  updateUserData(scanId: string, userData: ScanUserData): Promise<string> {
    let headers = new HttpHeaders();
    headers = headers.set('Content-Type', 'application/json; charset=utf-8');
    console.log('Updating user data', userData);
    return firstValueFrom(
      this.patch<string>(
        'scans/user_data',
        { scan_id: scanId },
        userData,
        headers
      )
    );
  }
}

@Injectable({
  providedIn: 'root',
})
export class SessionDataService extends RemoteDataService {
  /**
   * Method for getting the available sessions
   * @param offset Pagination offset (default = 0)
   * @param limit Number of records to retrieve (default = 100)
   * @returns response from the server with the scan data
   * @throws HttpErrorResponse if the request fails
   * @throws TimeoutError if the request takes too long
   */
  getSessions(offset: number = 0, limit: number = 100): Promise<Session[]> {
    let headers = new HttpHeaders();
    headers = headers.set('Content-Type', 'application/json; charset=utf-8');
    return firstValueFrom(
      this.get<Session[]>(
        'sessions',
        { offset: offset.toString(), limit: limit.toString() },
        headers
      )
    );
  }
}
