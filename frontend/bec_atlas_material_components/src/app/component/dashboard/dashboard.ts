import { CommonModule } from '@angular/common';
import { Component, signal } from '@angular/core';
import { Button } from '../button/button';
import { MatCardModule } from '@angular/material/card';


@Component({
  selector: 'app-dashboard',
  imports: [CommonModule, Button, MatCardModule],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.css'],
})
export class Dashboard {

  outputLabel = signal("Click a button");

  buttons = [
    { icon : 'settings', label: 'Settings' },
    { icon : 'home', label: 'Home' },
    { icon : 'info', label: 'Info' },
    { icon : 'favorite', label: 'Favorite' },
  ];

  onButtonClick(label: string) {
    console.log(`Button clicked: ${label}`);
    const rand = Math.floor(Math.random() * 1000);
    this.outputLabel.set(`You clicked the ${label} button with random number ${rand}`);
  }

}
