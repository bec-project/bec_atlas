import { Component, computed, effect, signal } from '@angular/core';
import { MyButton } from './components/my-button/my-button';
import { MatCardModule } from '@angular/material/card';

@Component({
  selector: 'app-root',
  imports: [MyButton, MatCardModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  readonly count = signal(0);

  isDisabled = computed(() => this.count() >= 3);
  buttonLabel = computed(() =>
    this.isDisabled() ? 'Limit reached HEHE (3)' : `Click me (${this.count()})`
  );

  constructor() {
    effect(() => {
      // Runs whenever count changes
      console.log('count =', this.count());
    });
  }

  increment(): void {
    this.count.update((v) => v + 1);
  }

  reset(): void {
    this.count.set(0);
  }
}
