import { KnownMantineColor } from '@/contexts/ThemeContext'
import { useTheme } from '@/contexts/ThemeContext.utils'
import { CustomColors } from '@/utils/themes'
import { useUser } from '@clerk/react'
import { useEffect } from 'react'

const COMPANY_THEME_CONFIG: Record<string, KnownMantineColor | CustomColors> = {
  catl: 'blue',
  cleanamps_energy: 'cleanamps-energy-green',
  desri: 'desri-blue',
  excelsior: 'excelsior-blue',
  first_solar: 'red',
  goshe_energy_storage: 'goshe-energy-storage-blue',
  lightsource_bp: 'lightsource-bp-orange',
  longroad_energy: 'mccarthy-red',
  lydian_energy: 'lydian-energy-blue',
  mccarthy: 'mccarthy-red',
  oriden: 'oriden-green',
  origis_energy: 'origis-blue',
  sable_point_energy: 'sable-point-energy-green',
  strata: 'orange',
  swift_current_energy: 'swift-blue',
  terabase_energy: 'terabase-blue',
}

export const CompanyThemeManager = () => {
  const { setPrimaryColor } = useTheme()
  const { isSignedIn, user } = useUser()

  useEffect(() => {
    if (isSignedIn && user) {
      const parentCompany = user.publicMetadata.parent_company
      const parentCompanyClean =
        typeof parentCompany === 'string' ? parentCompany : ''

      const fallback: KnownMantineColor | CustomColors = 'proximal-blue'

      const themeColor = COMPANY_THEME_CONFIG[parentCompanyClean] || fallback

      setPrimaryColor(themeColor)
    }
  }, [isSignedIn, user, setPrimaryColor])

  return null // This component doesn't render anything
}
