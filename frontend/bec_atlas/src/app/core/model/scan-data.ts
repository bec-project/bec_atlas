export interface ScanDataResponse {
    scan_id?: string;
    scan_number?: number;
    status?: "open" | "paused" | "aborted" | "halted" | "closed";
    session_id?: string;
    num_points?: number;
    scan_name?: string;
    scan_type?: "step" | "fly";
    dataset_number?: number;
    scan_report_devices?: string[];
    user_metadata?: { [key: string]: any };
    readout_priority?: { [key: "monitored" | "baseline" | "async" | "continuous" | "on_request" | string]: string[] };
    scan_parameters?: { [key: "exp_time" | "frames_per_trigger" | "settling_time" | "readout_time" | string]: any };
    request_inputs?: { [key: "arg_bundle" | "inputs" | "kwargs" | string]: any };
    info?: { [key: string]: any };
    timestamp?: number;
    user_data?: { [key: string]: any };
    user_rating?: number;
}
  