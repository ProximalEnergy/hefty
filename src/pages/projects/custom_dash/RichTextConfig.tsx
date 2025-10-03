import { Button, Group, Stack, Title } from '@mantine/core'

import { RichTextConfig as RichTextConfigType } from './CustomDash'

const RichTextConfig = ({
  stack,
  onAdd,
}: {
  stack: { close: (drawerId: 'rich-text-config') => void }
  onAdd: (config: RichTextConfigType) => void
}) => {
  const addRichText = () => {
    const config: RichTextConfigType = {
      content: '<p>Start typing your rich text content here...</p>',
    }

    onAdd(config)
  }

  return (
    <Stack>
      <Title>Add Rich Text</Title>
      <p>
        This will add a rich text editor component to your dashboard where you
        can add formatted text, links, and other content.
      </p>

      <Group justify="flex-end">
        <Button
          variant="default"
          onClick={() => stack.close('rich-text-config')}
        >
          Return
        </Button>
        <Button onClick={addRichText}>Add Rich Text Component</Button>
      </Group>
    </Stack>
  )
}

export default RichTextConfig
