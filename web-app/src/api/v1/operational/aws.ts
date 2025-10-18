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
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<string>({
    axiosConfig,
    queryName: 'getPresignedUrl',
    pathParams: {},
    queryParams: queryParams,
    queryOptions: queryOptions,
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
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<BucketItem[]>({
    axiosConfig,
    queryName: 'getPresignedUrl',
    pathParams: {},
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}
