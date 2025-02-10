export interface Deployment {
  _id: string;
  realm_id: string;
  name: string;
  owner_groups: string[];
  access_groups: string[];
  config_templates: string[];
}
