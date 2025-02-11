import { Component, output, Signal, signal } from '@angular/core';
import { MatSelect } from '@angular/material/select';
import { MatFormField } from '@angular/material/select';
import { MatLabel } from '@angular/material/select';
import { MatOption } from '@angular/material/select';

import { Session } from '../../core/model/session';
import { SessionDataService } from '../../core/remote-data.service';

@Component({
  selector: 'app-side-panel',
  imports: [MatSelect, MatFormField, MatLabel, MatOption],
  templateUrl: './side-panel.component.html',
  styleUrl: './side-panel.component.scss',
})
export class SidePanelComponent {
  selectedSession: Session | null = null;
  sessions: Session[] = [];

  readonly sessionChanged = output<Session | null>();

  constructor(private sessionDataService: SessionDataService) {}

  ngOnInit(): void {
    this.sessionDataService.getSessions().subscribe((sessions) => {
      this.sessions = sessions;
    });
  }

  onSessionChange(session: Session | null): void {
    this.selectedSession = session;
    this.sessionChanged.emit(session);
  }
}
