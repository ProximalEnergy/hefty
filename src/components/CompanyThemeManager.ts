import { useTheme } from '@/contexts/ThemeContext'
import { KnownMantineColor } from '@/contexts/ThemeContext'
import { CustomColors } from '@/utils/themes'
import { useUser } from '@clerk/clerk-react'
import { useEffect } from 'react'

const COMPANY_THEME_CONFIG: Record<string, KnownMantineColor | CustomColors> = {
  catl: 'blue',
  cleanamps_energy: 'cleanamps-energy-green',
  desri: 'desri-blue',
  excelsior: 'excelsior-blue',
  first_solar: 'red',
  mccarthy: 'mccarthy-red',
  longroad_energy: 'mccarthy-red',
  origis_energy: 'origis-blue',
  strata: 'orange',
  swift_current_energy: 'swift-blue',
  terabase_energy: 'terabase-blue',
  lightsource_bp: 'lightsource-bp-orange',
  oriden: 'oriden-green',
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
