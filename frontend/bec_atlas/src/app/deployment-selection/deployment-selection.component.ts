import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { RealmDataService } from '../core/remote-data.service';
import { Realm } from '../core/model/realm';
import { Deployment } from '../core/model/deployment';

@Component({
  selector: 'app-deployment-selection',
  imports: [
    MatCardModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatSelectModule,
    ReactiveFormsModule,
    CommonModule,
  ],
  templateUrl: './deployment-selection.component.html',
  styleUrl: './deployment-selection.component.scss',
})
export class DeploymentSelectionComponent {
  form: FormGroup;
  beamlines: Realm[] = [];
  deployments: Deployment[] = [];
  selectedDeployment: Deployment | null = null;

  constructor(
    private fb: FormBuilder,
    private realmDataService: RealmDataService,
    private dialogRef: MatDialogRef<DeploymentSelectionComponent>
  ) {
    this.form = this.fb.group({
      beamline: [''],
      deployment: [''],
    });
  }

  ngOnInit(): void {
    // fetch deployments
    this.realmDataService
      .getRealmsWithDeploymentAccess(true)
      .subscribe((realms) => {
        console.log(realms);
        this.beamlines = realms;
        // this.deployments = deployments;
      });
    this.form.get('beamline')?.valueChanges.subscribe((beamlineId) => {
      if (beamlineId) {
        let beamline = this.beamlines.find((realm) => realm._id === beamlineId);
        this.deployments = beamline?.deployments ?? [];
      }
    });
    this.form.get('deployment')?.valueChanges.subscribe((deploymentId) => {
      if (deploymentId) {
        let selectedDeployment = this.deployments.find(
          (deployment) => deployment._id === deploymentId
        );
        if (selectedDeployment) {
          this.selectedDeployment = selectedDeployment;
        } else {
          this.selectedDeployment = null;
        }
      }
    });
  }

  applySelection() {
    this.dialogRef.close(this.selectedDeployment);
  }
}
