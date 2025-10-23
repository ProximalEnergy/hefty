import { ProjectTypeEnum } from '@/api/_example/openapi-typescript/enums'
import { useGetProjectsOpenAPITypeScript } from '@/api/_example/openapi-typescript/projects'

export const Page = () => {
  const data = useGetProjectsOpenAPITypeScript({
    queryParams: {
      project_ids: ['1', '2', '3'],
      project_ids_excluded: ['4', '5', '6'],
      project_type_ids: [4],
      project_status_type_ids: [1, 2, 3],
      name_short: 'Project 1',
      name_long: 'Project 1',
      has_pv_pcs_modules: true,
    },
    queryOptions: {
      enabled: true,
    },
  })

  data.data?.map((project) => {
    return (
      <div>
        {project.project_type_id === ProjectTypeEnum.PV_BESS ? 'PV_BESS' : 'PV'}
      </div>
    )
  })

  return <div>{JSON.stringify(data)}</div>
}
