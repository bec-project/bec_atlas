import { Deployment } from './deployment';

export interface Realm {
  _id: string;
  realm_id: string;
  name: string;
  owner_groups: Array<string>;
  access_groups: Array<string>;
  deployments: Array<Deployment>;
}
