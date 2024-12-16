import { Component, computed, Input, Signal } from '@angular/core';
import { RedisConnectorService } from '../core/redis-connector.service';
import { MessageEndpoints } from '../core/redis_endpoints';
import { MatCardModule } from '@angular/material/card';

@Component({
  selector: 'app-device-box',
  imports: [MatCardModule],
  templateUrl: './device-box.component.html',
  styleUrl: './device-box.component.scss',
})
export class DeviceBoxComponent {
  signal!: Signal<any>;
  readback_signal!: Signal<number>;

  @Input()
  device!: string;

  @Input()
  signal_name!: string;

  constructor(private redisConnector: RedisConnectorService) {}

  ngOnInit(): void {
    this.signal = this.redisConnector.register(
      MessageEndpoints.device_readback(this.device)
    );
    this.readback_signal = computed(() => {
      let data = this.signal();
      if (!data) {
        return 'N/A';
      }
      if (!data.data.signals[this.signal_name]) {
        return 'N/A';
      }
      if (typeof data.data.signals[this.signal_name].value === 'number') {
        return data.data.signals[this.signal_name].value.toFixed(2);
      }
      return data.data.signals[this.signal_name].value;
    });
  }
}
