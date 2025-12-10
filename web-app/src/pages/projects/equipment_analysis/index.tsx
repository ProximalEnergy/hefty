import { useSelectProject } from '@/api/v1/operational/projects'
import { PageLoader } from '@/components/Loading'
import { Navigate, useParams } from 'react-router'

export default function EquipmentAnalysis() {
  const { projectId } = useParams<{ projectId: string }>()
  const project = useSelectProject(projectId!)

  if (project.isLoading) {
    return <PageLoader />
  }

  // Redirect to system page by default
  return (
    <Navigate to={`/projects/${projectId}/equipment-analysis/system`} replace />
  )
}
