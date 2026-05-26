import { useSelectProject } from '@/api/v1/operational/projects'

type UseDcAmperageReportContextProps = {
  projectId: string
}

export function useDcAmperageReportContext({
  projectId,
}: UseDcAmperageReportContextProps) {
  const projectQuery = useSelectProject(projectId)

  return {
    projectId,
    project: projectQuery.data,
    isLoading: projectQuery.isLoading,
    error: projectQuery.error,
  }
}
