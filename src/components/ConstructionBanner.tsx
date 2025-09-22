import { Alert } from '@mantine/core'
import { IconAlertTriangle } from '@tabler/icons-react'

const ConstructionBanner = ({ radius = true }: { radius?: boolean }) => {
  return (
    <Alert
      variant="light"
      color="yellow"
      title="Page Under Construction"
      icon={<IconAlertTriangle size={16} />}
      radius={radius ? 'md' : 0}
    >
      The Proximal Team is currently building this page. Please let us know what
      you want to see via the feedback button at the bottom of the sidebar.
    </Alert>
  )
}

export default ConstructionBanner
