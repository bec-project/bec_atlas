import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-my-button',
  imports: [MatButtonModule],
  templateUrl: './my-button.html',
  styleUrl: './my-button.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MyButton {
  readonly label = input('Click');
  readonly disabled = input(false);
  readonly clicked = output<void>();
}
