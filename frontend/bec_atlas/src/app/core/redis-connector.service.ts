import { Injectable, signal, WritableSignal } from '@angular/core';
import { io, Socket } from 'socket.io-client';
import { Observable } from 'rxjs';
import { EndpointInfo } from './redis_endpoints';
import { ServerSettingsService } from '../server-settings.service';
import { DeploymentService } from '../deployment.service';

@Injectable()
export class RedisConnectorService {
  private socket: Socket | null = null;
  private signals: Map<string, WritableSignal<any>> = new Map();
  private signalReferenceCount: Map<string, number> = new Map();

  constructor(
    private serverSettings: ServerSettingsService,
    private deploymentService: DeploymentService
  ) {
    this.deploymentService.selectedDeployment.subscribe((deployment) => {
      this.disconnect();
      if (!deployment) {
        return;
      }
      this.connect(deployment._id);
    });
  }

  /**
   * Connect to the WebSocket server using socket.io
   */
  private connect(id: string): void {
    this.socket = io(this.serverSettings.getSocketAddress(), {
      transports: ['websocket'], // Use WebSocket only
      autoConnect: true, // Automatically connect
      reconnection: true, // Enable automatic reconnection
      timeout: 500, // Connection timeout in milliseconds
      path: '/api/v1/ws', // Path to the WebSocket server
      auth: {
        deployment: id,
      },
    });

    // this.socket.onAny((event, ...args) => {
    //   // console.log('Received event:', event, 'with data:', args);
    // });

    this.socket.on('connect', () => {
      console.log('Connected to WebSocket server');
      // this.register(MessageEndpoints.device_readback('samx'));
    });

    this.socket.on('message', (data: any) => {
      // console.log('Received message:', data);
      const dataObj = JSON.parse(data);
      const endpoint_signal = this.signals.get(dataObj.endpoint_request);
      if (endpoint_signal) {
        endpoint_signal.set(dataObj);
      }
    });

    this.socket.on('disconnect', (reason: string) => {
      console.log('Disconnected from WebSocket server:', reason);
    });

    this.socket.on('connect_error', (error: Error) => {
      console.error('Connection error:', error);
    });

    this.socket.on('reconnect_attempt', (attempt: number) => {
      console.log('Reconnection attempt:', attempt);
    });

    this.socket.on('error', (error: Error) => {
      console.error('Socket error:', error);
    });

    this.socket.on('ping', () => {
      console.log('Ping received');
    });
  }

  /**
   * Emit an event to the WebSocket server
   * @param event Event name
   * @param data Data to send
   */
  public emit(event: string, data: any): void {
    if (!this.socket) {
      console.error('Socket not connected');
      return;
    }
    this.socket.emit(event, data);
  }

  /**
   * Register an endpoint to listen for events
   * @param endpoint Endpoint to listen for
   * @returns Signal for the endpoint
   */
  public register(endpoint: EndpointInfo): WritableSignal<any> {
    // Convert endpoint to string for use as a key
    const endpoint_str = JSON.stringify(endpoint);

    let endpoint_signal: WritableSignal<any>;

    if (this.signals.has(endpoint_str)) {
      // If the signal already exists, return it
      endpoint_signal = this.signals.get(endpoint_str) as WritableSignal<any>;
    } else {
      // Otherwise, create a new signal
      endpoint_signal = signal(null);
      this.signals.set(endpoint_str, endpoint_signal);
    }

    const signalReferenceCount =
      this.signalReferenceCount.get(endpoint_str) || 0;

    if (signalReferenceCount === 0) {
      // If no references to the signal, register the endpoint
      this.emit('register', endpoint_str);
    }

    this.signals.set(endpoint_str, endpoint_signal);
    this.signalReferenceCount.set(endpoint_str, signalReferenceCount + 1);
    return endpoint_signal;
  }

  /**
   * Listen for an event from the WebSocket server
   * @param event Event name
   * @returns Observable for the event data
   */
  public on<T>(event: string): Observable<T> {
    return new Observable<T>((observer) => {
      if (!this.socket) {
        console.error('Socket not connected');
        return;
      }
      this.socket.on(event, (data: T) => {
        observer.next(data);
      });

      // Cleanup when unsubscribed
      return () => {
        if (!this.socket) {
          return;
        }
        this.socket.off(event);
      };
    });
  }

  /**
   * Disconnect from the WebSocket server
   */
  public disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      console.log('Disconnected from WebSocket server');
    }
  }
}
