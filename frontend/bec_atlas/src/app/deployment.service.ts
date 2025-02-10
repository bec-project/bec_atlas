import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { DeploymentDataService } from './core/remote-data.service';
import { Deployment } from './core/model/deployment';

@Injectable()
export class DeploymentService {
  selectedDeployment = new BehaviorSubject<Deployment | null>(null);

  constructor(private deploymentDataService: DeploymentDataService) {
    // check the local storage for a selected deployment
    const deployment = sessionStorage.getItem('selected_deployment');
    if (!deployment) {
      return;
    }
    this.deploymentDataService
      .getDeployment(deployment)
      .subscribe((deployment) => {
        if (deployment) {
          this.selectedDeployment.next(deployment);
        }
      });
  }

  selectDeployment(deployment: Deployment | null): void {
    // save the selected deployment to local storage
    if (!deployment) {
      sessionStorage.removeItem('selected_deployment');
      this.selectedDeployment.next(null);
      return;
    }

    sessionStorage.setItem('selected_deployment', deployment._id);

    this.selectedDeployment.next(deployment);
  }
}
