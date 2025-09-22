import { Box, Stack } from '@mantine/core'

interface LoomVideoProps {
  videoId: string
  sessionId?: string
}

const LoomVideo = ({ videoId, sessionId }: LoomVideoProps) => {
  const embedUrl = sessionId
    ? `https://www.loom.com/embed/${videoId}?sid=${sessionId}`
    : `https://www.loom.com/embed/${videoId}`

  return (
    <Box style={{ aspectRatio: '16/9' }}>
      <iframe
        src={embedUrl}
        style={{
          width: '100%',
          height: '100%',
          border: 'none',
          borderRadius: '1rem',
        }}
      />
    </Box>
  )
}

const Page = () => {
  return (
    <Stack p="md">
      <LoomVideo
        videoId="28cabf3b9558414bb79c40546da14576"
        sessionId="eb513d13-14a2-430f-8fd7-be7b2dbc32c7"
      />
    </Stack>
  )
}

export default Page
