import { useGetUserType } from '@/api/admin'
import { Stack, Text, Title } from '@mantine/core'

import { PageError } from '../Error'
import { PageLoader } from '../Loading'

type RequiresUserTypeProps = {
  requiredUserType: 'admin' | 'superadmin'
  children: React.ReactNode
  // When true, render nothing instead of a PermissionDenied message
  silent?: boolean
}

const RequiresUserType = ({
  requiredUserType,
  children,
  silent = false,
}: RequiresUserTypeProps) => {
  const userType = useGetUserType({})

  if (userType.isLoading) {
    return <PageLoader />
  }

  if (userType.error) {
    return <PageError error={userType.error} />
  }

  if (!userType.data) {
    return <PageError text="Unable to fetch user type." />
  }

  // Admin
  // Requires the user to be an admin or superadmin
  if (requiredUserType === 'admin') {
    if (
      userType.data.name_short !== 'admin' &&
      userType.data.name_short !== 'superadmin'
    ) {
      return silent ? null : (
        <PermissionDenied
          requiredUserType={requiredUserType}
          userType={userType.data.name_short}
        />
      )
    }
  }

  // Superadmin
  // Requires the user to be a superadmin
  if (requiredUserType === 'superadmin') {
    if (userType.data.name_short !== 'superadmin') {
      return silent ? null : (
        <PermissionDenied
          requiredUserType={requiredUserType}
          userType={userType.data.name_short}
        />
      )
    }
  }

  return <>{children}</>
}

const PermissionDenied = ({
  requiredUserType,
  userType,
}: {
  requiredUserType: 'admin' | 'superadmin'
  userType: 'user' | 'admin' | 'superadmin'
}) => {
  return (
    <Stack p="md">
      <Title order={3}>Permission Denied</Title>
      <Text>
        You do not have permission to access this page.
        {requiredUserType === 'admin' &&
          userType === 'user' &&
          ' Please reach out to an administrator to request access.'}
      </Text>
    </Stack>
  )
}

export default RequiresUserType
