import { LoadingOverlay } from '@mantine/core'

export const PageLoader = () => {
  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      <LoadingOverlay visible />
    </div>
  )
}
