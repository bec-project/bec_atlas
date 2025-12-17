import { ChangeDetectionStrategy, Component, computed, signal } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MyButton } from '../../components/my-button/my-button';

@Component({
  selector: 'app-about',
  imports: [MatCardModule, MyButton],
  templateUrl: './about.html',
  styleUrl: './about.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class About {
  private readonly clickCount = signal(0);

  readonly message = computed(() => {
    const count = this.clickCount();
    return count === 0 ? 'About page placeholder' : `About button clicked ${count} time${count === 1 ? '' : 's'}`;
  });

  click(): void {
    this.clickCount.update((value) => value + 1);
  }
}
