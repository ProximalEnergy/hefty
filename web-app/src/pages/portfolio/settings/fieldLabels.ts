type FieldLabels = Readonly<Record<string, string>>

export const formatFieldLabel = (
  field: string,
  fieldLabels: FieldLabels = {},
) => {
  const customLabel = fieldLabels[field]

  if (customLabel) {
    return customLabel
  }

  return field
    .split('_')
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(' ')
}
