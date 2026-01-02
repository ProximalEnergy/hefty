import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

interface BucketItem {
  Key: string
  LastModified: string
  ETag: string
  Size: number
  StorageClass: string
}

export const useGetPresignedUrl = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/aws/retrieve-presigned-url`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<string>({
    axiosConfig,
    queryName: 'getPresignedUrl',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetBucketListdir = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/aws/listdir`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<BucketItem[]>({
    axiosConfig,
    queryName: 'getPresignedUrl',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
