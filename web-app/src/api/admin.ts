import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { useAuth } from '@clerk/clerk-react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

import { baseURL } from '../urlConfig'

type Permission = types.components['schemas']['Permission']
type UserWithPermissions = types.components['schemas']['UserWithPermissions']

export interface User {
  user_id: string
  name_long: string
  company_id: string
  user_type_id: number
  operational_project_ids: string[]
  image_url?: string | null
}

type Company = types.components['schemas']['Company']
type Team = types.components['schemas']['Team']
type TeamWithMembers = types.components['schemas']['TeamWithMembers']
type UserType = types.components['schemas']['UserType'] & {
  // noqa: hardcoded-name-short
  name_short: 'admin' | 'superadmin' | 'user'
}

export const useGetUserType = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: '/v1/admin/user-type',
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<UserType>({
    axiosConfig,
    queryName: 'getUserType',
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetAllPermissions = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/admin/permissions`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<Permission[]>({
    axiosConfig,
    queryName: 'getAllPermissions',
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetCompanyPermissions = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/admin/permissions/projects/${pathParams.projectId}/company`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<Permission[]>({
    axiosConfig,
    queryName: 'getCompanyPermissions',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetCompanyUsersPermissions = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/admin/permissions/projects/${pathParams.projectId}/company-users`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<UserWithPermissions[]>({
    axiosConfig,
    queryName: 'getCompanyUsersPermissions',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetUserPermissions = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/admin/permissions/projects/${pathParams.projectId}/user`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<Permission[]>({
    axiosConfig,
    queryName: 'getUserPermissions',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useUpdateUserPermissionMutation = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      userId,
      projectId,
      permissionId,
      grant,
    }: {
      userId: string
      projectId: string
      permissionId: number
      grant: boolean
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: grant ? 'post' : 'delete',
        url: `${baseURL}/v1/admin/permissions/projects/${projectId}/users/${userId}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          permission_id: permissionId,
        },
      })
    },
    onMutate: async ({ userId, projectId, permissionId, grant }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({
        queryKey: ['getCompanyUsersPermissions', { projectId }],
      })

      // Snapshot the previous value
      const previousUserPermissions = queryClient.getQueryData<
        UserWithPermissions[]
      >(['getCompanyUsersPermissions', { projectId }])

      // Optimistically update to the new value
      queryClient.setQueryData(
        ['getCompanyUsersPermissions', { projectId }],
        (old?: UserWithPermissions[]) => {
          if (!old) return old
          return old.map((user) => {
            if (user.user_id.toString() === userId) {
              const newPermissionIds = grant
                ? [...user.permission_ids, permissionId]
                : user.permission_ids.filter((id) => id !== permissionId)
              return {
                ...user,
                permission_ids: newPermissionIds,
              }
            }
            return user
          })
        },
      )

      // Return a context object with the snapshotted value
      return { previousUserPermissions }
    },
    onError: (_err, variables, context) => {
      // If the mutation fails, roll back to the previous value
      if (context?.previousUserPermissions) {
        queryClient.setQueryData(
          ['getCompanyUsersPermissions', { projectId: variables.projectId }],
          context.previousUserPermissions,
        )
      }
    },
    onSettled: (_data, _error, variables) => {
      // Always refetch after error or success to ensure we're in sync with server
      queryClient.invalidateQueries({
        queryKey: [
          'getCompanyUsersPermissions',
          { projectId: variables.projectId },
        ],
      })
    },
  })
}

export const useGetUsers = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: {
    user_ids?: string[]
    company_ids?: string[]
    include_image_urls?: boolean
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/admin/users`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<User[]>({
    axiosConfig,
    queryName: 'getUsers',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetUserSelf = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/admin/users/self`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<User>({
    axiosConfig,
    queryName: 'getUserSelf',
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetCompanies = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: { company_ids?: string[] }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/admin/companies`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<Company[]>({
    axiosConfig,
    queryName: 'getCompanies',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetCompanyTeams = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/admin/teams/company`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<Team[]>({
    axiosConfig,
    queryName: 'getCompanyTeams',
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetCompanyTeamsWithMembers = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/admin/teams/company/members`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<TeamWithMembers[]>({
    axiosConfig,
    queryName: 'getCompanyTeamsWithMembers',
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useCreateTeam = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ name_long }: { name_long: string }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'post',
        url: `${baseURL}/v1/admin/teams`,
        headers: { Authorization: `Bearer ${token}` },
        data: { name_long },
      })
    },
    onSuccess: () => {
      // Refresh both simple teams and teams-with-members caches
      queryClient.invalidateQueries({ queryKey: ['getTeamsWithMembers'] })
      queryClient.invalidateQueries({ queryKey: ['getTeams'] })
    },
  })
}

export const useGetTeamsWithMembers = ({
  queryParams,
  queryOptions = {},
}: {
  queryParams: { company_id: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/admin/teams/members`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<TeamWithMembers[]>({
    axiosConfig,
    queryName: 'getTeamsWithMembers',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useAddTeamMember = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      team_id,
      user_id,
    }: {
      team_id: string
      user_id: string
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'post',
        url: `${baseURL}/v1/admin/teams/${team_id}/members`,
        headers: { Authorization: `Bearer ${token}` },
        data: { user_id },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getTeamsWithMembers'] })
    },
  })
}

export const useRemoveTeamMember = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      team_id,
      user_id,
    }: {
      team_id: string
      user_id: string
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'delete',
        url: `${baseURL}/v1/admin/teams/${team_id}/members/${user_id}`,
        headers: { Authorization: `Bearer ${token}` },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getTeamsWithMembers'] })
    },
  })
}

export const useDeleteTeam = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ team_id }: { team_id: string }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'delete',
        url: `${baseURL}/v1/admin/teams/${team_id}`,
        headers: { Authorization: `Bearer ${token}` },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getTeamsWithMembers'] })
      queryClient.invalidateQueries({ queryKey: ['getTeams'] })
    },
  })
}

export const useRenameTeam = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      team_id,
      name_long,
    }: {
      team_id: string
      name_long: string
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'patch',
        url: `${baseURL}/v1/admin/teams/${team_id}`,
        headers: { Authorization: `Bearer ${token}` },
        data: { name_long },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getTeamsWithMembers'] })
      queryClient.invalidateQueries({ queryKey: ['getTeams'] })
    },
  })
}

interface CreateUserParams {
  first_name: string
  last_name: string
  email: string
  company_id: string
  company_name_short: string
}

export const useCreateUser = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      first_name,
      last_name,
      email,
      company_id,
      company_name_short,
    }: CreateUserParams) => {
      const token = await getToken({ template: 'default' })

      // Send all data to your backend, let it handle both Clerk and database creation
      return axios({
        method: 'post',
        url: `${baseURL}/v1/admin/users/create-with-clerk`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          first_name,
          last_name,
          email,
          company_id,
          company_name_short,
        },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getUsers'] })
    },
  })
}

export const useUpdateSelfClerkTheme = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ theme }: { theme: string }) => {
      const token = await getToken({ template: 'default' })

      return axios({
        method: 'put',
        url: `${baseURL}/v1/admin/users/self/clerk-theme`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          theme,
          vite_environment: import.meta.env.VITE_ENVIRONMENT,
        },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getUserSelf'] })
    },
  })
}

export const useUpdateSelfClerkDemoMode = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ demo_mode }: { demo_mode: boolean }) => {
      const token = await getToken({ template: 'default' })

      return axios({
        method: 'put',
        url: `${baseURL}/v1/admin/users/self/clerk-demo-mode`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          demo_mode,
          vite_environment: import.meta.env.VITE_ENVIRONMENT,
        },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getUserSelf'] })
      queryClient.invalidateQueries({ queryKey: ['getProjects'] })
      queryClient.invalidateQueries({ queryKey: ['getProjectsPersonal'] })
    },
  })
}

export const useDeleteUser = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ user_id }: { user_id: string }) => {
      const token = await getToken({ template: 'default' })

      // Send all data to your backend, let it handle both Clerk and database creation
      return axios({
        method: 'delete',
        url: `${baseURL}/v1/admin/users/${user_id}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getUsers'] })
    },
  })
}

export const useUpdateUserProjects = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      user_ids,
      operational_project_ids,
    }: {
      user_ids: string[]
      operational_project_ids: string[][]
    }) => {
      const token = await getToken({ template: 'default' })

      // Send all data to your backend, let it handle both Clerk and database creation
      return axios({
        method: 'post',
        url: `${baseURL}/v1/admin/user-projects/update-user-projects`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          user_ids,
          operational_project_ids,
        },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getUsers'] })
    },
  })
}
