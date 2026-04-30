export const getProjectInfoTabPath = (projectId?: string) => {
  return projectId
    ? `/projects/${projectId}/settings?tab=project-info`
    : '/projects'
}

export const getProjectOMContractorsTabPath = (projectId?: string) => {
  return projectId
    ? `/projects/${projectId}/settings?tab=om-contractors`
    : '/projects'
}
