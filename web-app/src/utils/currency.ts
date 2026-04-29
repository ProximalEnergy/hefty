interface FormatCurrencyOptions {
  minimumFractionDigits?: number
  maximumFractionDigits?: number
  placeholder?: string
}

/**
 * Formats a number as a USD currency string.
 *
 * @param value The number to format
 * @param options Formatting options
 * @returns Formatted currency string or placeholder
 */
export const formatCurrency = (
  value: number | null | undefined,
  {
    minimumFractionDigits = 0,
    maximumFractionDigits = 0,
    placeholder = '—',
  }: FormatCurrencyOptions = {},
) => {
  if (value == null) {
    return placeholder
  }

  return value.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits,
    maximumFractionDigits,
  })
}
