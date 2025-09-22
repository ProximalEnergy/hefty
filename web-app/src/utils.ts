import { DatetimeDataFrame } from './hooks/types'

export const NOTIFICATION_ERROR_MESSAGE =
  'If the problem persists, please contact support at support@proximal.energy.'

export function dfSum(data: DatetimeDataFrame): { [key: string]: number } {
  const columns = data.columns
  const values = data.data
  const sums: { [key: string]: number } = {}
  columns.forEach((column, i) => {
    sums[column] = values.reduce((acc, row) => acc + row[i], 0)
  })
  return sums
}

export function dfMean(data: DatetimeDataFrame): { [key: string]: number } {
  const columns = data.columns
  const values = data.data
  const sums = dfSum(data)
  const means: { [key: string]: number } = {}
  columns.forEach((column) => {
    means[column] = sums[column] / values.length
  })
  return means
}

export function downloadCSV(csvString: string, filename: string): void {
  // Create a Blob from the CSV string
  const blob = new Blob([csvString], {
    type: 'text/csv;charset=utf-8;',
  })

  // Create a link element, use it to download the Blob, then remove it
  const link = document.createElement('a')
  if (link.download !== undefined) {
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', filename)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }
}
