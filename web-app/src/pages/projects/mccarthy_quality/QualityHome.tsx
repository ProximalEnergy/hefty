import { PageError } from '@/components/Error'
import { Stack } from '@mantine/core'
import { Link, useParams } from 'react-router'

export default function QualityHome() {
  const { projectId } = useParams()

  if (projectId !== '6970fba7-6462-475f-805a-2357ee4ababb') {
    return <PageError text="Quality Data not available for this project." />
  }

  return (
    <Stack p="md">
      <Link
        to="inspections/gis"
        style={{
          color: 'inherit',
        }}
      >
        Inspections - GIS
      </Link>
      <Link
        to="observations/gis"
        style={{
          color: 'inherit',
        }}
      >
        Observations - GIS
      </Link>
      <Link
        to="inspections"
        style={{
          color: 'inherit',
        }}
      >
        Inspections
      </Link>
      <Link
        to="observations"
        style={{
          color: 'inherit',
        }}
      >
        Observations
      </Link>
    </Stack>
  )
}
