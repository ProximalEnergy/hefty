import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import { useMutation } from '@tanstack/react-query'
import axios from 'axios'

export const useImportProjectSystem = () => {
  const { getToken } = useAuth()

  return useMutation({
    mutationFn: async ({ projectId }: { projectId: string }) => {
      const token = await getToken({ template: 'default' })

      const response = await axios({
        method: 'put',
        url: `${baseURL}/v1/commissioning/projects/${projectId}/system/import`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      return response.data
    },
  })
}
