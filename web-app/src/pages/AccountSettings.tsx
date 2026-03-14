import { UserProfile, useUser } from '@clerk/react'
import { Center, Modal } from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { useEffect } from 'react'

const AccountSettings = () => {
  const { user } = useUser()
  const [opened, { open, close }] = useDisclosure(false)

  const hasTwoFactorEnabled = user?.twoFactorEnabled
  const isDemoUser = user?.publicMetadata?.demo

  useEffect(() => {
    if (!hasTwoFactorEnabled && !isDemoUser) {
      open()
    }
  }, [hasTwoFactorEnabled, open, isDemoUser])

  return (
    <Center p="md">
      <UserProfile routing="hash" />
      <Modal opened={opened} onClose={close} title="Two Factor Authentication">
        Two Factor Authentication (2FA) is required to use this application.
        Please enable 2FA by clicking the &quot;Add two-step verification&quot;
        button on the account security page.
      </Modal>
    </Center>
  )
}

export default AccountSettings
