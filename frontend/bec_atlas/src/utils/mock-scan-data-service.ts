
import { Injectable, Input } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { Observable, of } from "rxjs";
// import * as path from "path";
// import * as fs from "fs";
import { ScanDataService } from "../app/core/remote-data.service";
import { ScanDataResponse } from "../app/core/model/scan-data";
import { ScanCountResponse } from "../app/core/model/scan-count";
import { ScanUserData } from "../app/core/model/scan-user-data";
import data from "./bec_atlas.scans.json";


@Injectable({
    providedIn: 'root'
})
export class MockScanDataService {
    private scanDataResponse: any |null=null;
    //  this.convertMongoIds(this.scanDataResponsePath);
    
    totalCounts: number=1;

    // convertMongoIds(jsonPath:string="./bec_atlas.scans.json"):ScanDataResponse {
    //     const rawJson = fs.readFileSync(jsonPath, 'utf8');
    //     return JSON.parse(rawJson, (key, value) => {
    //         if (key === '_id' && typeof value === 'object' && value.$oid) {
    //           return value.$oid; // Convert MongoDB ObjectId to string
    //         }
    //         return value;
    //       });
    // };

    // private filterFields(data: ScanDataResponse, fields: Array<keyof ScanDataResponse> | null): Partial<ScanDataResponse> {
    //     if (!fields || fields.length === 0) return data;
    
    //     return fields.reduce((filtered, field) => {
    //         if (field in data) {
    //             (filtered as Record<string, any>)[field] = data[field]; // Type-safe access
    //         }
    //         return filtered;
    //     }, {} as Partial<ScanDataResponse>);
    // };


    // getScanData(
    //     sessionId: string,
    //     offset: number=0,
    //     limit: number=100,
    //     fields: Array<keyof ScanDataResponse> | null=null,
    //     includeUserData: boolean=false,
    //     sort: { [key: string]: number } | null=null
    // ): Observable<Array<ScanDataResponse>> {
    //     const filteredData = this.filterFields(this.scanDataResponse?, fields);

    //     let data: ScanDataResponse[] = Array.from({ length: this.totalCounts } , (_, index) => ({
    //         ...filteredData,
    //         _id: '${this.scanDataResponse._id}_${index}',}))
    //     const paginatedData = data.slice(offset, offset + limit);

    //     return of(paginatedData);
    // }

    // getScanCount(scanId: string, userData: ScanUserData): Observable<string> {
    //     return of('1');
    // };

}