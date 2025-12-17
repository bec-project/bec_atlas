import { ChangeDetectionStrategy, Component, computed, signal } from '@angular/core';
import { MyButton } from '../../components/my-button/my-button';
import { MatCardModule } from '@angular/material/card';

@Component({
  selector: 'app-home',
  imports: [MyButton, MatCardModule],
  templateUrl: './home.html',
  styleUrl: './home.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Home {
  readonly count = signal(0);

  readonly isDisabled = computed(() => this.count() >= 3);
  readonly buttonLabel = computed(() =>
    this.isDisabled() ? 'Limit reached (3)' : `Click me (${this.count()})`,
  );

  increment(): void {
    this.count.update((value) => value + 1);
  }

  reset(): void {
    this.count.set(0);
  }
}
