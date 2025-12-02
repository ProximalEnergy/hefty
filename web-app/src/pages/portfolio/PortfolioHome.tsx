import { useGetUserType } from '@/api/admin'
import { UserTypeEnumEnum } from '@/api/enumerations'
import { useGetUserProjects } from '@/api/v1/admin/user_projects'
import { useGetProjectDataLastUpdated } from '@/api/v1/operational/project_data_last_updated'
import { ProjectStatusTypeId } from '@/api/v1/operational/project_status_types'
import { useGetProjects } from '@/api/v1/operational/projects'
import { useGetPortfolioHome } from '@/api/v1/protected/web-application/portfolio/home'
import { NoData, PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { useTipsPersonalPortfolio } from '@/components/Tips'
import { useUser } from '@clerk/clerk-react'
import {
  Box,
  Group,
  SegmentedControl,
  Stack,
  Tabs,
  TextInput,
  Title,
} from '@mantine/core'
import { useDebouncedValue } from '@mantine/hooks'
import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'

import { ActiveProjectsTab } from './tabs/active'
import { ArchivedProjectsTab } from './tabs/archived'
import { OnboardingProjectsTab } from './tabs/onboarding'

function PortfolioHome() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [debouncedSearchTerm] = useDebouncedValue(searchTerm, 300)
  useTipsPersonalPortfolio()

  // Get active tab from URL params or default to 'active'
  const activeTab = searchParams.get('tab') || 'active'

  // Get time parameter from URL params or default to '24h'
  // Valid values: '24h' or '30d'
  const timeParam = (() => {
    const param = searchParams.get('time') || '24h'
    return param === '24h' || param === '30d' ? param : '24h'
  })()

  const { user } = useUser()

  // Query user type to check if user is superadmin
  const userType = useGetUserType({
    queryOptions: {
      refetchOnWindowFocus: false,
    },
  })
  const isUserSuperadmin =
    userType?.data?.user_type_id === UserTypeEnumEnum.SUPERADMIN

  // Query projects and portfolio home data
  const projects = useGetProjects({
    queryParams: {
      deep: true,
      project_status_type_ids: [
        ProjectStatusTypeId.ACTIVE,
        ProjectStatusTypeId.ONBOARDING,
        ProjectStatusTypeId.ARCHIVED,
      ],
    },
  })

  // Get user projects with favorited status
  const userProjects = useGetUserProjects({
    pathParams: { userId: user?.id || '' },
    queryOptions: {
      enabled: !!user?.id,
    },
  })

  const portfolioHome = useGetPortfolioHome({
    queryParams: {
      project_ids: projects.data
        ?.filter(
          (project) =>
            project.project_status_type_id === ProjectStatusTypeId.ACTIVE,
        )
        ?.map((project) => project.project_id),
      time: timeParam as '24h' | '30d',
    },
    // Only run query when projects data is available
    queryOptions: { enabled: !!projects.data },
  })

  const projectDataLastUpdated = useGetProjectDataLastUpdated({
    queryParams: {
      project_ids: projects.data?.map((project) => project.project_id) || [],
    },
    // Only run query when projects data is available
    queryOptions: { enabled: !!projects.data },
  })

  // Render loading state
  if (
    projects.isLoading ||
    portfolioHome.isLoading ||
    userType.isLoading ||
    userProjects.isPending
  ) {
    return <PageLoader />
  }

  // Render error state
  if (projects.isError) {
    return <PageError error={projects.error} />
  }
  if (portfolioHome.isError) {
    return <PageError error={portfolioHome.error} />
  }
  if (userType.isError) {
    return <PageError error={userType.error} />
  }

  // Render no data state
  if (!projects.data || !portfolioHome.data) {
    return <NoData />
  }

  // Determine project counts for tab labels
  const activeProjects = projects.data.filter(
    (project) => project.project_status_type_id === ProjectStatusTypeId.ACTIVE,
  )
  const onboardingProjects = projects.data.filter(
    (project) =>
      project.project_status_type_id === ProjectStatusTypeId.ONBOARDING,
  )
  const archivedProjects = projects.data.filter(
    (project) =>
      project.project_status_type_id === ProjectStatusTypeId.ARCHIVED,
  )

  return (
    <Box p="md">
      <Tabs
        value={activeTab}
        onChange={(value) => {
          if (value) {
            const newParams = new URLSearchParams(searchParams)
            newParams.set('tab', value)
            setSearchParams(newParams)
          }
        }}
        variant="default"
      >
        <Tabs.List>
          <Tabs.Tab value="active">Active ({activeProjects.length})</Tabs.Tab>
          {isUserSuperadmin && (
            <Tabs.Tab value="onboarding">
              Onboarding ({onboardingProjects.length})
            </Tabs.Tab>
          )}
          {isUserSuperadmin && (
            <Tabs.Tab value="archived">
              Archived ({archivedProjects.length})
            </Tabs.Tab>
          )}
          {isUserSuperadmin && (
            <Tabs.Tab
              value="create"
              onClick={() => navigate('/portfolio/create-project')}
            >
              Create New Project
            </Tabs.Tab>
          )}
        </Tabs.List>

        {/* Project Search */}
        <Stack pt="md">
          <Group justify="space-between" align="center">
            <Title order={4} size="h5">
              Project Search
            </Title>
            <SegmentedControl
              value={timeParam}
              data={[
                { label: '24 hours', value: '24h' },
                { label: '30 days', value: '30d' },
              ]}
              onChange={(value) => {
                const newParams = new URLSearchParams(searchParams)
                newParams.set('time', value)
                setSearchParams(newParams)
              }}
            />
          </Group>
          <TextInput
            placeholder="Search by project name"
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.currentTarget.value)}
          />
        </Stack>

        {/* Active Projects Section */}
        <Tabs.Panel value="active">
          <ActiveProjectsTab
            projects={projects.data}
            portfolioHomeData={portfolioHome.data}
            projectDataLastUpdated={projectDataLastUpdated.data}
            userProjects={userProjects.data || []}
            searchTerm={debouncedSearchTerm}
            time={timeParam as '24h' | '30d'}
          />
        </Tabs.Panel>

        {/* Projects Under Commissioning Section */}
        {isUserSuperadmin && (
          <Tabs.Panel value="onboarding">
            <OnboardingProjectsTab
              projects={projects.data || []}
              searchTerm={debouncedSearchTerm}
            />
          </Tabs.Panel>
        )}

        {/* Archived Projects Section */}
        {isUserSuperadmin && (
          <Tabs.Panel value="archived">
            <ArchivedProjectsTab
              projects={projects.data}
              portfolioHomeData={portfolioHome.data}
              projectDataLastUpdated={projectDataLastUpdated.data}
              searchTerm={debouncedSearchTerm}
              time={timeParam as '24h' | '30d'}
            />
          </Tabs.Panel>
        )}
      </Tabs>
    </Box>
  )
}

export default PortfolioHome
