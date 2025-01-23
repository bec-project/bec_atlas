import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Router } from '@angular/router';

@Component({
  selector: 'app-overview',
  imports: [MatCardModule, MatIconModule, MatTooltipModule, CommonModule],
  templateUrl: './overview.component.html',
  styleUrl: './overview.component.scss',
})
export class OverviewComponent {
  hasExperimentControlAccess: boolean = true;
  hasAdminAccess: boolean = true;

  constructor(private router: Router) {}

  selection($event: string) {
    this.router.navigateByUrl('/' + $event);
  }
}
