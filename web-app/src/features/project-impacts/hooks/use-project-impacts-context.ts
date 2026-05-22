import { useSelectProject } from '@/api/v1/operational/projects'
import { ProjectImpactsContext } from '@/features/project-impacts/types/project-impacts-types'

type UseProjectImpactsContextProps = {
  projectId: string | undefined
}

export function useProjectImpactsContext({
  projectId,
}: UseProjectImpactsContextProps): ProjectImpactsContext {
  const projectQuery = useSelectProject(projectId)
  return {
    projectId: projectId ?? '',
    project: projectQuery.data,
    isLoading: projectQuery.isLoading,
    error: projectQuery.error,
  }
}
