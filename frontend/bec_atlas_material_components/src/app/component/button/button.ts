import { Component, input, Input, Output, signal} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { AppIcon } from './button-icon.types';

@Component({
  selector: 'app-button',
  imports: [MatButtonModule, MatIconModule],
  templateUrl: './button.html',
  styleUrl: './button.css',
})
export class Button {
  icon = input<AppIcon>('home');
  label = input<string | null>(null);

  active = signal<boolean>(true);
  
  @Output() toggled = signal(false);

  onClick() {
    if (this.active())
      this.toggled.set(!this.toggled());
  }

}
