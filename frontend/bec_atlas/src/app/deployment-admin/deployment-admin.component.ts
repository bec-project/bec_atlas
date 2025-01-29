import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatButtonModule } from '@angular/material/button';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';

interface Beamline {
  id: string;
  name: string;
}

interface Deployment {
  id: string;
  name: string;
  beamlineId: string;
}

interface ACLEntry {
  userId: string;
  username: string;
  accessLevel: string;
  lastModified: Date;
}

@Component({
  selector: 'app-deployment-admin',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatSelectModule,
    MatFormFieldModule,
    MatButtonModule,
    ReactiveFormsModule,
    MatTableModule,
    MatIconModule,
  ],
  templateUrl: './deployment-admin.component.html',
  styleUrl: './deployment-admin.component.scss',
})
export class DeploymentAdminComponent implements OnInit {
  form: FormGroup;
  beamlines: Beamline[] = [
    { id: 'x10sa', name: 'X10SA' },
    { id: 'x12sa', name: 'X12SA' },
  ];
  deployments: Deployment[] = [];
  aclEntries: ACLEntry[] = [];
  displayedColumns: string[] = [
    'username',
    'accessLevel',
    'lastModified',
    'actions',
  ];

  constructor(private fb: FormBuilder) {
    this.form = this.fb.group({
      beamline: [''],
      deployment: [''],
    });
  }

  ngOnInit() {
    // Subscribe to beamline selection changes
    this.form.get('beamline')?.valueChanges.subscribe((beamlineId) => {
      if (beamlineId) {
        this.loadDeployments(beamlineId);
      }
    });

    // Subscribe to deployment selection changes
    this.form.get('deployment')?.valueChanges.subscribe((deploymentId) => {
      if (deploymentId) {
        this.loadACLEntries(deploymentId);
      }
    });
  }

  loadDeployments(beamlineId: string) {
    // TODO: Replace with actual API call
    this.deployments = [
      { id: 'dep1', name: 'Production', beamlineId },
      { id: 'dep2', name: 'Development', beamlineId },
    ];
  }

  loadACLEntries(deploymentId: string) {
    // TODO: Replace with actual API call
    this.aclEntries = [
      {
        userId: '1',
        username: 'john.doe',
        accessLevel: 'admin',
        lastModified: new Date(),
      },
      {
        userId: '2',
        username: 'jane.smith',
        accessLevel: 'user',
        lastModified: new Date(),
      },
    ];
  }

  addUser() {
    // TODO: Implement user addition logic
  }

  removeUser(userId: string) {
    // TODO: Implement user removal logic
  }

  updateAccessLevel(userId: string, newLevel: string) {
    // TODO: Implement access level update logic
  }
}
