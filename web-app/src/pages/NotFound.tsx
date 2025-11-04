import { Button, Container, Group, Text, Title } from '@mantine/core'
import { IconHome } from '@tabler/icons-react'
import { Link } from 'react-router'

export default function NotFound() {
  return (
    <Container size="md" style={{ textAlign: 'center', paddingTop: '120px' }}>
      <div
        style={{
          fontSize: '120px',
          fontWeight: 900,
          lineHeight: 1,
          marginBottom: '20px',
          color: 'var(--mantine-color-dimmed)',
        }}
      >
        404
      </div>

      <Title order={2} size="h1" mb="md">
        Page Not Found
      </Title>

      <Text c="dimmed" size="lg" mb="xl">
        The page you&apos;re looking for doesn&apos;t exist. It might have been
        moved, deleted, or you entered the wrong URL.
      </Text>

      <Group justify="center" gap="md">
        <Button
          component={Link}
          to="/portfolio"
          leftSection={<IconHome size={16} />}
          size="md"
        >
          Back to Portfolio
        </Button>
      </Group>
    </Container>
  )
}
