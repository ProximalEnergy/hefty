import { getCompanyLogoUrl } from '@/utils/cdn'
import { useUser } from '@clerk/react'
import { Image, Stack, Title, useComputedColorScheme } from '@mantine/core'
import { useEffect } from 'react'

const ProximalLogo = () => {
  const computedColorScheme = useComputedColorScheme()
  const logoFilename =
    computedColorScheme === 'dark'
      ? 'logo_color_inverse_one_line.svg'
      : 'logo_color_one_line.svg'

  return <Image src={getCompanyLogoUrl(logoFilename)} my={-10} h="65%" />
}

const DESRILogo = () => {
  const computedColorScheme = useComputedColorScheme()

  return (
    <Image
      src={getCompanyLogoUrl('logo_desri.svg')}
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
      src={getCompanyLogoUrl(
        computedColorScheme === 'dark'
          ? 'logo_terabase_white.svg'
          : 'logo_terabase.svg',
      )}
      h="50%"
    />
  )
}

const OdenLogo = () => {
  const computedColorScheme = useComputedColorScheme()
  return (
    <Image
      src={getCompanyLogoUrl('logo_oriden.svg')}
      style={{
        filter:
          computedColorScheme === 'dark' ? 'brightness(0) invert(1)' : 'none',
      }}
      h="75%"
    />
  )
}

const MONTSERRAT_FONT_ID = 'sable-point-montserrat-font'

const SablePointEnergyLogo = () => {
  const computedColorScheme = useComputedColorScheme()

  useEffect(() => {
    if (document.getElementById(MONTSERRAT_FONT_ID)) return
    const preconnect1 = document.createElement('link')
    preconnect1.rel = 'preconnect'
    preconnect1.href = 'https://fonts.googleapis.com'
    document.head.appendChild(preconnect1)
    const preconnect2 = document.createElement('link')
    preconnect2.rel = 'preconnect'
    preconnect2.href = 'https://fonts.gstatic.com'
    preconnect2.setAttribute('crossorigin', '')
    document.head.appendChild(preconnect2)
    const link = document.createElement('link')
    link.id = MONTSERRAT_FONT_ID
    link.rel = 'stylesheet'
    link.href =
      'https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap'
    document.head.appendChild(link)
  }, [])

  return (
    <>
      <Image
        src={getCompanyLogoUrl('logo_sable_point_energy.svg')}
        h="65%"
        mr={-20}
        style={{
          filter:
            computedColorScheme === 'dark' ? 'brightness(0) invert(1)' : 'none',
        }}
      />
      <Title
        lh={1}
        order={2}
        style={{ fontFamily: 'Montserrat, sans-serif' }}
        c={computedColorScheme === 'dark' ? undefined : '#0F2B2A'}
      >
        SABLE POINT ENERGY
      </Title>
    </>
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
            <Image src={getCompanyLogoUrl('logo_mccarthy.png')} h="75%" />
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
        return <Image src={getCompanyLogoUrl('logo_catl.svg')} h="50%" />
      case 'excelsior':
        return <Image src={getCompanyLogoUrl('logo_excelsior.svg')} h="70%" />
      case 'cleanamps_energy':
        return (
          <Image src={getCompanyLogoUrl('logo_cleanamps_energy.svg')} h="35%" />
        )
      case 'strata':
        return <Image src={getCompanyLogoUrl('logo_strata.svg')} h="70%" />
      case 'origis_energy':
        return <Image src={getCompanyLogoUrl('logo_origis.svg')} h="70%" />
      case 'swift_current_energy':
        return <Image src={getCompanyLogoUrl('logo_swift.svg')} h="70%" />
      case 'first_solar':
        return <Image src={getCompanyLogoUrl('logo_first_solar.svg')} h="70%" />
      case 'desri':
        return <DESRILogo />
      case 'terabase_energy':
        return <TerabaseLogo />
      case 'lightsource_bp':
        return (
          <Image src={getCompanyLogoUrl('logo_lightsource_bp.png')} h="70%" />
        )
      case 'oriden':
        return <OdenLogo />
      case 'lydian_energy':
        return (
          <Image src={getCompanyLogoUrl('logo_lydian_energy.webp')} h="70%" />
        )
      case 'goshe_energy_storage':
        return (
          <Image
            src={getCompanyLogoUrl('logo_goshe_energy_storage.svg')}
            h="70%"
          />
        )
      case 'sable_point_energy':
        return <SablePointEnergyLogo />
    }
  }

  return <ProximalLogo />
}

export default Logo
