import {
  useGetCompaniesWithProjects,
  useUpdateSelfClerkTheme,
} from '@/api/admin'
import { useGetProjects } from '@/api/v1/operational/projects'
import {
  Box,
  Button,
  Group,
  Loader,
  Select,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { useLocalStorage } from '@mantine/hooks'
import { useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router'

const PROXIMAL_NAME_SHORT = 'proximal'

const CompanyView = () => {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const projects = useGetProjects({ personalPortfolio: false })
  const companiesQuery = useGetCompaniesWithProjects()
  const updateThemeMutation = useUpdateSelfClerkTheme()

  const [, setExcludedProjectIds] = useLocalStorage<string[]>({
    key: 'proximal-personal-portfolio-excluded-project-ids',
    defaultValue: [],
  })

  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(
    null,
  )

  const selectData = useMemo(() => {
    if (!companiesQuery.data) return []

    return companiesQuery.data.map((company) => ({
      value: company.company_id,
      label: company.name_long,
    }))
  }, [companiesQuery.data])

  const selectedCompany = useMemo(() => {
    if (!selectedCompanyId || !companiesQuery.data) return null
    return companiesQuery.data.find((c) => c.company_id === selectedCompanyId)
  }, [selectedCompanyId, companiesQuery.data])

  const handleClickProxy = async () => {
    if (!selectedCompany || !projects.data) return

    const isProximal =
      selectedCompany.name_short.toLowerCase() === PROXIMAL_NAME_SHORT

    let projectsToExclude: string[]

    if (isProximal) {
      projectsToExclude = []
    } else {
      const companyProjectIdSet = new Set(selectedCompany.project_ids)
      projectsToExclude = projects.data
        .filter((project) => !companyProjectIdSet.has(project.project_id))
        .map((project) => project.project_id)
    }

    setExcludedProjectIds(projectsToExclude)

    queryClient.removeQueries({
      queryKey: ['getProjectsPersonal'],
    })

    const theme = selectedCompany.name_short.toLowerCase()
    try {
      await updateThemeMutation.mutateAsync({ theme })
      navigate('/portfolio')
    } catch (error) {
      console.error('Failed to update theme:', error)
    }
  }

  if (companiesQuery.isLoading) {
    return (
      <Stack p="md" align="center">
        <Loader />
        <Text>Loading companies...</Text>
      </Stack>
    )
  }

  return (
    <Stack p="md">
      <Title order={1}>Company View</Title>
      <Group>
        <Text style={{ flex: 1 }}>
          This page allows you to quickly proxy to a company&apos;s view for the
          platform. This action will override your theme to the selected
          company&apos;s theme, and change your personal portfolio to the
          selected company&apos;s projects. You will be redirected to the
          portfolio homepage after selecting a company.
        </Text>
        <Box style={{ flex: 1 }} />
      </Group>
      <Select
        data={selectData}
        placeholder="Select a company"
        onChange={(value) => setSelectedCompanyId(value)}
        searchable
      />
      <Button
        onClick={() => handleClickProxy()}
        loading={updateThemeMutation.isPending}
        disabled={!selectedCompany}
      >
        Proxy to Company
      </Button>
    </Stack>
  )
}

export default CompanyView
