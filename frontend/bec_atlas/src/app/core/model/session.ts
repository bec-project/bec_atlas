export interface Session {
  name: string;
  deployment_id?: string;
  _id: string;
  owner_groups?: string[];
  access_groups?: []; // This should probably be string[] as well
}
