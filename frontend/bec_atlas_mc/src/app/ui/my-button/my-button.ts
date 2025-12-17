import {Component, EventEmitter, Input, Output} from '@angular/core';
import {MatButton, MatButtonModule} from '@angular/material/button';

@Component({
  selector: 'app-my-button',
  imports: [MatButtonModule, MatButton],
  templateUrl: './my-button.html',
  styleUrl: './my-button.css',
})
export class MyButton {
  @Input() label = 'Click';
  @Input() disabled = false;

  @Output() clicked = new EventEmitter<void>();

  onClick(): void {
    if (!this.disabled) {
      this.clicked.emit();
    }
  }
}
