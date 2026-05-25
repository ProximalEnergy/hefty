import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/react'
import { useMutation } from '@tanstack/react-query'
import axios from 'axios'

const PVCOLLADA_EXPORT_URL =
  '/v1/protected/web-application/projects/{project_id}/pvcollada/export'

const extractPvcolladaExportFilename = (headerValue: string | undefined) => {
  if (!headerValue) return null
  const quotedMatch = headerValue.match(/filename="([^"]+)"/)
  if (quotedMatch?.[1]) return quotedMatch[1]
  const fallbackMatch = headerValue.match(/filename=([^;]+)/)
  return fallbackMatch?.[1]?.trim() ?? null
}

const downloadBlob = ({ blob, filename }: { blob: Blob; filename: string }) => {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

export const useDownloadPVColladaExport = () => {
  const { getToken } = useAuth()

  return useMutation({
    mutationFn: async ({ projectId }: { projectId: string }) => {
      const token = await getToken({ template: 'default' })
      const url = PVCOLLADA_EXPORT_URL.replace(
        '{project_id}',
        encodeURIComponent(projectId),
      )

      const response = await axios({
        method: 'get',
        url: `${baseURL}${url}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        responseType: 'blob',
      })

      const headerValue = String(
        response.headers['content-disposition'] ??
          response.headers['Content-Disposition'] ??
          '',
      )
      const filename =
        extractPvcolladaExportFilename(headerValue) ??
        'project_pvcollada_2_0.pvc2'

      downloadBlob({ blob: response.data, filename })
    },
  })
}
