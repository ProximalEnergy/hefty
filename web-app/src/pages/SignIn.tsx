import { SignIn as ClerkSignIn } from '@clerk/react'
import { Center } from '@mantine/core'
import { useQueryClient } from '@tanstack/react-query'

export function SignIn() {
  // Clear query cache when user is signing in (and therefore after the user
  // has signed out)
  const queryClient = useQueryClient()
  queryClient.clear()

  return (
    <Center h="100vh" w="100vw">
      <ClerkSignIn />
    </Center>
  )
}
