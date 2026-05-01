/**
 * Tenant logo asset for UI that mirrors `Logo.tsx` `parent_company` cases.
 */

type ParentCompanyLogoSpec = {
  filename: string
  /** Match Logo.tsx dark-mode filter for vector marks. */
  invertInDarkMode?: boolean
  /** Height passed to `<Image h>` in `Logo.tsx`; consumers may override. */
  height?: string
}

/**
 * Resolve CDN logo filename (and dark-mode hint) from Clerk `parent_company`.
 */
export function getParentCompanyLogoSpec(
  parentCompany: string | undefined,
  isDark: boolean,
): ParentCompanyLogoSpec {
  switch (parentCompany) {
    case 'mccarthy':
    case 'longroad_energy':
      return { filename: 'logo_mccarthy.png', height: '75%' }
    case 'catl':
      return { filename: 'logo_catl.svg', height: '50%' }
    case 'excelsior':
      return { filename: 'logo_excelsior.svg', height: '70%' }
    case 'cleanamps_energy':
      return { filename: 'logo_cleanamps_energy.svg', height: '35%' }
    case 'strata':
      return { filename: 'logo_strata.svg', height: '70%' }
    case 'origis_energy':
      return { filename: 'logo_origis.svg', height: '70%' }
    case 'swift_current_energy':
      return { filename: 'logo_swift.svg', height: '70%' }
    case 'first_solar':
      return { filename: 'logo_first_solar.svg', height: '70%' }
    case 'desri':
      return {
        filename: 'logo_desri.svg',
        invertInDarkMode: true,
        height: '80%',
      }
    case 'terabase_energy':
      return {
        filename: isDark ? 'logo_terabase_white.svg' : 'logo_terabase.svg',
        height: '50%',
      }
    case 'lightsource_bp':
      return { filename: 'logo_lightsource_bp.png', height: '70%' }
    case 'oriden':
      return {
        filename: 'logo_oriden.svg',
        invertInDarkMode: true,
        height: '75%',
      }
    case 'lydian_energy':
      return { filename: 'logo_lydian_energy.webp', height: '70%' }
    case 'goshe_energy_storage':
      return { filename: 'logo_goshe_energy_storage.svg', height: '70%' }
    case 'sable_point_energy':
      return {
        filename: 'logo_sable_point_energy.svg',
        invertInDarkMode: true,
        height: '65%',
      }
    case 'doral_renewables':
      return { filename: 'logo_doral_renewables.svg', height: '70%' }
    default:
      return {
        filename: isDark
          ? 'logo_color_inverse_one_line.svg'
          : 'logo_color_one_line.svg',
      }
  }
}
