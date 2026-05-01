import { Box, Group, Text, type TextInputProps, Tooltip } from '@mantine/core'
import { type ReactElement, cloneElement } from 'react'

import { CLAIM_EMAIL_LABEL_COL_W } from './email'

interface Props {
  label: string
  fieldId: string
  hint?: string
  children: ReactElement<TextInputProps>
}

/** Inline-label form row used by Step 5 (Review) email fields. */
export default function ClaimEmailFieldRow({
  label,
  fieldId,
  hint,
  children,
}: Props) {
  const control = cloneElement(children, { id: fieldId } satisfies Pick<
    TextInputProps,
    'id'
  >)
  const row = (
    <Group gap="sm" align="center" wrap="nowrap">
      <Text
        component="label"
        htmlFor={fieldId}
        size="sm"
        fw={500}
        style={{ width: CLAIM_EMAIL_LABEL_COL_W, flexShrink: 0 }}
      >
        {label}
      </Text>
      <Box style={{ flex: 1, minWidth: 0 }}>{control}</Box>
    </Group>
  )
  if (!hint) return row
  return (
    <Tooltip label={hint} multiline w={300} position="top-start">
      {row}
    </Tooltip>
  )
}
