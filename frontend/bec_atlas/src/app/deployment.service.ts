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
    this.update_deployment(deployment);
  }

  async update_deployment(deploymentId: string | null): Promise<void> {
    if (!deploymentId) {
      this.selectedDeployment.next(null);
      return;
    }

    let deployment_info = await this.deploymentDataService.getDeployment(
      deploymentId
    );
    this.selectedDeployment.next(deployment_info);
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
