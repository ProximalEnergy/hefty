export enum ProjectStatusTypeId {
  ACTIVE = 1,
  ONBOARDING = 2,
  ARCHIVED = 3,
}

export interface ProjectType {
  project_status_type_id: ProjectStatusTypeId
  name_short: string
  name_long: string
}
