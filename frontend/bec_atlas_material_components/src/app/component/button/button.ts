import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  input,
  output,
  signal,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { AppIcon } from './button-icon.types';

@Component({
  selector: 'app-button',
  imports: [MatButtonModule, MatIconModule],
  templateUrl: './button.html',
  styleUrl: './button.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Button {
  readonly icon = input<AppIcon>('home');
  readonly label = input<string | null>(null);
  readonly showIcon = input<boolean>(true);
  readonly showLabel = input<boolean>(true);
  readonly disabled = input<boolean>(false);
  readonly togglable = input<boolean>(false);
  readonly defaultToggled = input<boolean>(false);

  private readonly toggledState = signal(false);

  readonly isDisabled = computed(() => this.disabled());
  readonly isToggled = computed(() => this.togglable() && this.toggledState());
  readonly shouldRenderIcon = computed(
    () => this.showIcon() && Boolean(this.icon())
  );
  readonly shouldRenderLabel = computed(
    () => this.showLabel() && Boolean(this.label())
  );

  // External API for toggleChange and clicked events
  readonly toggledChange = output<boolean>();
  readonly clicked = output<void>();

  constructor() {
    effect(() => {
      if (!this.togglable()) {
        this.toggledState.set(false);
        return;
      }

      this.toggledState.set(this.defaultToggled());
    });
  }

  handleClick(): void {
    if (this.isDisabled()) {
      return;
    }

    if (this.togglable()) {
      this.toggledState.update((current) => !current);
      this.toggledChange.emit(this.toggledState());
    }

    this.clicked.emit();
  }

}
