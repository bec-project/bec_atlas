export interface EndpointInfo {
  endpoint: string;
  args: Array<string>;
}

export class MessageEndpoints {
  /**
   *
   * @param device Device name
   * @returns Endpoint for device readback
   */
  static device_readback(device: string): EndpointInfo {
    const out: EndpointInfo = {
      endpoint: 'device_readback',
      args: [device],
    };
    return out;
  }

  /**
   *
   * @returns Endpoint for scan segment
   */
  static scan_segment(): EndpointInfo {
    const out: EndpointInfo = {
      endpoint: 'scan_segment',
      args: [],
    };
    return out;
  }

  /**
   *
   * @returns Endpoint for scan queue status
   */
  static scan_queue_status(): EndpointInfo {
    const out: EndpointInfo = {
      endpoint: 'scan_queue_status',
      args: [],
    };
    return out;
  }

  /**
   *
   * @returns Endpoint for device monitor 2d
   */
  static device_monitor_2d(device: string): EndpointInfo {
    const out: EndpointInfo = {
      endpoint: 'device_monitor_2d',
      args: [device],
    };
    return out;
  }
}
