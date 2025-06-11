import { Component, inject } from '@angular/core';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatIconModule } from '@angular/material/icon';
import { BreakpointObserver } from '@angular/cdk/layout';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';
import { Router, RouterModule } from '@angular/router';
import { MatExpansionModule } from '@angular/material/expansion';
import { DeploymentService } from '../deployment.service';
import {
  MatDialog,
  MatDialogModule,
  MatDialogConfig,
} from '@angular/material/dialog';
import { DeploymentSelectionComponent } from '../deployment-selection/deployment-selection.component';
import { RedisConnectorService } from '../core/redis-connector.service';
import { AuthDataService } from '../core/remote-data.service';
import { SidePanelComponent } from '../scan-table/side-panel/side-panel.component';
import { SidepanelIconComponent } from './sidepanel-icon/sidepanel-icon.component';

@Component({
  selector: 'app-dashboard',
  imports: [
    CommonModule,
    MatExpansionModule,
    MatDividerModule,
    MatSidenavModule,
    MatIconModule,
    MatButtonModule,
    MatDialogModule,
    RouterModule,
    SidePanelComponent,
    SidepanelIconComponent,
  ],
  providers: [DeploymentService, RedisConnectorService],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent {
  // isScreenSmall = false;
  readonly dialog = inject(MatDialog);
  deployment_name: string = '';
  realm_name: string = '';
  hideExperimentPanel = true;
  selectOrSwitchButtonTitle = 'Select Deployment';

  constructor(
    private breakpointObserver: BreakpointObserver,
    private deploymentService: DeploymentService,
    private authDataService: AuthDataService,
    private router: Router
  ) {}

  ngOnInit(): void {
    // check if the user has already selected a deployment
    // if not, open the deployment selection dialog
    // this.deploymentService.selectedDeployment.subscribe((deployment) => {
    //   if (deployment) {
    //     console.log('Updating deployment name to: ', deployment.name);
    //     this.deployment_name = deployment.name;
    //     this.realm_name = deployment.realm_id;
    //     this.hideExperimentPanel = false;
    //     this.selectOrSwitchButtonTitle = 'Switch Deployment';
    //   } else {
    //     this.deployment_name = '';
    //     this.realm_name = '';
    //     this.hideExperimentPanel = true;
    //     this.selectOrSwitchButtonTitle = 'Select Deployment';
    //   }
    // });
    // this.breakpointObserver
    //   .observe([Breakpoints.Small, Breakpoints.XSmall])
    //   .subscribe((result) => {
    //     this.isScreenSmall = result.matches;
    //   });
  }

  // openDeploymentDialog() {
  //   // open deployment dialog
  //   let dialogConfig: MatDialogConfig = {
  //     disableClose: true,
  //     width: '80%',
  //   };
  //   let dialogRef = this.dialog.open(
  //     DeploymentSelectionComponent,
  //     dialogConfig
  //   );
  //   dialogRef.afterClosed().subscribe((result) => {
  //     this.deploymentService.selectDeployment(result);
  //   });
  // }

  // panelOpened() {
  //   if (!this.deploymentService.selectedDeployment.value) {
  //     this.openDeploymentDialog();
  //   }
  // }

  logout() {
    this.authDataService.logout();
    this.router.navigate(['/login']);
  }
}
