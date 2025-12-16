import { Button, Group, Stack, Title } from '@mantine/core'

import { RichTextConfig as RichTextConfigType } from './CustomDash'

const RichTextConfig = ({
  mode,
  stack,
  onAdd,
  initialConfig,
}: {
  mode: 'create' | 'edit'
  stack: { close: (drawerId: 'rich-text-config') => void }
  onAdd: (config: RichTextConfigType) => void
  initialConfig?: RichTextConfigType
}) => {
  const addRichText = () => {
    const config: RichTextConfigType = {
      content:
        initialConfig?.content ??
        '<p>Start typing your rich text content here...</p>',
    }

    onAdd(config)
  }

  return (
    <Stack>
      {mode === 'create' && <Title>Add Rich Text</Title>}
      {mode === 'edit' && <Title>Edit Rich Text</Title>}
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
        <Button onClick={addRichText}>
          {mode === 'edit'
            ? 'Update Rich Text Component'
            : 'Add Rich Text Component'}
        </Button>
      </Group>
    </Stack>
  )
}

export default RichTextConfig
