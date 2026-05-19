import { ProjectTypeEnum } from '@/api/enumerations'
import { useSelectProject } from '@/api/v1/operational/projects'
import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import BESSProjectHome from '@/pages/projects/BESSProjectHome'
import ProjectHome from '@/pages/projects/ProjectHome'
import { useParams } from 'react-router'

/**
 * Renders the appropriate project home page based on project type.
 * BESS projects use BESSProjectHome; PV and PV+Storage use ProjectHome.
 */
const ProjectHomeRouter = () => {
  const { projectId } = useParams()
  const project = useSelectProject(projectId!)

  if (project.isLoading) return <PageLoader />
  if (project.isError) return <PageError error={project.error} />
  if (project.data === undefined) return <PageError error={undefined} />

  if (project.data.project_type_id === ProjectTypeEnum.BESS) {
    return <BESSProjectHome />
  }
  return <ProjectHome />
}

export default ProjectHomeRouter
