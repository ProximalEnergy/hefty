import { useUser } from '@clerk/clerk-react'
import { Image, Stack, Title, useComputedColorScheme } from '@mantine/core'

const ProximalLogo = () => {
  const computedColorScheme = useComputedColorScheme()

  return (
    <Image
      src={
        computedColorScheme === 'dark'
          ? '/logo_color_inverse_one_line.svg'
          : '/logo_color_one_line.svg'
      }
      my={-10}
      h="65%"
    />
  )
}

const DESRILogo = () => {
  const computedColorScheme = useComputedColorScheme()

  return (
    <Image
      src="/logo_desri.svg"
      h="80%"
      style={{
        filter:
          computedColorScheme === 'dark' ? 'brightness(0) invert(1)' : 'none',
      }}
    />
  )
}

const TerabaseLogo = () => {
  const computedColorScheme = useComputedColorScheme()
  return (
    <Image
      src={
        computedColorScheme === 'dark'
          ? '/logo_terabase_white.svg'
          : '/logo_terabase.svg'
      }
      h="50%"
    />
  )
}

const OdenLogo = () => {
  const computedColorScheme = useComputedColorScheme()
  return (
    <Image
      src="/logo_oriden.svg"
      style={{
        filter:
          computedColorScheme === 'dark' ? 'brightness(0) invert(1)' : 'none',
      }}
      h="75%"
    />
  )
}

const Logo = () => {
  const { isSignedIn, user } = useUser()

  if (isSignedIn) {
    const parentCompany = user.publicMetadata.parent_company
    switch (parentCompany) {
      case 'mccarthy':
      case 'longroad_energy':
        return (
          <>
            <Image src="/logo_mccarthy.png" h="75%" />
            <Stack gap={0}>
              <Title fs="italic" lh={1} order={2} c="#db0032">
                AMP
              </Title>
              <Title lh={1} order={5}>
                Asset Management Platform
              </Title>
            </Stack>
          </>
        )
      case 'catl':
        return <Image src="/logo_catl.svg" h="50%" />
      case 'excelsior':
        return <Image src="/logo_excelsior.svg" h="70%" />
      case 'cleanamps_energy':
        return <Image src="/logo_cleanamps_energy.svg" h="35%" />
      case 'strata':
        return <Image src="/logo_strata.svg" h="70%" />
      case 'origis_energy':
        return <Image src="/logo_origis.svg" h="70%" />
      case 'swift_current_energy':
        return <Image src="/logo_swift.svg" h="70%" />
      case 'first_solar':
        return <Image src="/logo_first_solar.svg" h="70%" />
      case 'desri':
        return <DESRILogo />
      case 'terabase_energy':
        return <TerabaseLogo />
      case 'lightsource_bp':
        return <Image src="/logo_lightsource_bp.png" h="70%" />
      case 'oriden':
        return <OdenLogo />
    }
  }

  return <ProximalLogo />
}

export default Logo
