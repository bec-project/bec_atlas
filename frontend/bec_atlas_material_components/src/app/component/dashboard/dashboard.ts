import { CommonModule } from '@angular/common';
import { Component, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { Button } from '../button/button';


@Component({
  selector: 'app-dashboard',
  imports: [CommonModule, Button, MatButtonModule, MatCardModule],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.css'],
})
export class Dashboard {
  readonly outputLabel = signal('Click a button');

  readonly showIcon = signal(true);
  readonly showLabel = signal(true);
  readonly buttonDisabled = signal(false);
  readonly buttonTogglable = signal(true);
  readonly defaultToggled = signal(false);

  readonly buttons = [
    { icon: 'settings', label: 'Settings' },
    { icon: 'home', label: 'Home' },
    { icon: 'info', label: 'Info' },
    { icon: 'favorite', label: 'Favorite' },
  ] as const;

  onButtonClick(label: string): void {
    console.log(`Button clicked: ${label}`);
    const rand = Math.floor(Math.random() * 1000);
    this.outputLabel.set(
      `You clicked the ${label} button with random number ${rand}`
    );
  }

  onButtonToggled(label: string, toggled: boolean): void {
    this.outputLabel.set(`${label} is ${toggled ? 'toggled on' : 'toggled off'}`);
  }

  toggleShowIcon(): void {
    this.showIcon.update((current) => !current);
  }

  toggleShowLabel(): void {
    this.showLabel.update((current) => !current);
  }

  toggleDisabled(): void {
    this.buttonDisabled.update((current) => !current);
  }

  toggleTogglable(): void {
    this.buttonTogglable.update((current) => !current);
    if (!this.buttonTogglable()) {
      this.defaultToggled.set(false);
    }
  }

  toggleDefaultToggled(): void {
    this.defaultToggled.update((current) => !current);
  }

}
