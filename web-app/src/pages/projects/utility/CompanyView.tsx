import { useUpdateSelfClerkTheme } from '@/api/admin'
import { useGetProjects } from '@/api/v1/operational/projects'
import { Box, Button, Group, Select, Stack, Text, Title } from '@mantine/core'
import { useLocalStorage } from '@mantine/hooks'
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const CompanyView = () => {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const projects = useGetProjects({ personalPortfolio: false })
  const updateThemeMutation = useUpdateSelfClerkTheme()

  const [, setExcludedProjectIds] = useLocalStorage<string[]>({
    key: 'proximal-personal-portfolio-excluded-project-ids',
    defaultValue: [],
  })

  const companies = {
    Proximal: {
      theme: 'proximal',
      projects: [],
    },
    DESRI: {
      theme: 'desri',
      projects: ['north_star', 'sigurd'],
    },
    Excelsior: {
      theme: 'excelsior',
      projects: [
        'bexar',
        'continental_v2',
        'falfurrias',
        'gregory',
        'headcamp',
        'mason',
        'monte_cristo',
        'muenster',
        'palacios',
        'sinton_pirate',
      ],
    },
    McCarthy: {
      theme: 'mccarthy',
      projects: [
        'assembly_1',
        'assembly_2',
        'assembly_3',
        'bonnybrooke',
        'centennial_flats',
        'double_black_diamond',
        'fiddlers_canyon_1',
        'fiddlers_canyon_2',
        'fiddlers_canyon_3',
        'lancaster',
        'milford_2',
        'rosamond_south_1',
        'serrano',
        'sun_pond',
        'snipesville_2',
        'south_milford',
        'sun_streams_3',
        'sun_streams_4',
      ],
    },
  }
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null)

  const handleClickProxy = async () => {
    if (selectedCompany && projects.data) {
      const companyData = companies[selectedCompany as keyof typeof companies]
      const companyProjectNames: string[] = companyData.projects

      let projectsToExclude: string[]

      if (companyProjectNames.length === 0) {
        // Proximal option: include all projects (exclude none)
        projectsToExclude = []
      } else {
        // Other companies: exclude all projects not in the company's project list
        projectsToExclude = projects.data
          .filter(
            (project) => !companyProjectNames.includes(project.name_short),
          )
          .map((project) => project.project_id)
      }

      // Update the excluded project IDs
      setExcludedProjectIds(projectsToExclude)

      // Invalidate the personal portfolio cache
      queryClient.removeQueries({
        queryKey: ['getProjectsPersonal'],
      })

      // Update the user's theme in Clerk
      try {
        await updateThemeMutation.mutateAsync({ theme: companyData.theme })
        // Redirect to portfolio on success
        navigate('/portfolio')
      } catch (error) {
        console.error('Failed to update theme:', error)
      }
    }
  }

  return (
    <Stack p="md">
      <Title order={1}>Company View</Title>
      <Group>
        <Text style={{ flex: 1 }}>
          This page allows you to quickly proxy to a company's view for the
          platform. This action will override your theme to the selected
          company's theme, and change your personal portfolio to the selected
          company's projects. You will be redirected to the portfolio homepage
          after selecting a company.
        </Text>
        <Box style={{ flex: 1 }} />
      </Group>
      <Select
        data={Object.keys(companies)}
        placeholder="Select a company"
        onChange={(value) => setSelectedCompany(value)}
      />
      <Button
        onClick={() => handleClickProxy()}
        loading={updateThemeMutation.isPending}
      >
        Proxy to Company
      </Button>
    </Stack>
  )
}

export default CompanyView
