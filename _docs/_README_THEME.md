# Theme Customization

To add a new client theme, follow the steps below.

1. Download logo from the company website. Formats such as SVG or PNG tend to work best. If the company has different logos for light and dark theme, download both.
2. Save the logo as `logo_<company_name_short>.<ext>` in the `public` folder (if you downloaded multiple logos, add a descriptive suffix to the filenames). Note that the `company_name_short` should be the same as what is stored in the database. If the company does not exist in the database, create a new entry, making sure to follow the existing naming convention.
3. Navigate to `src/pages/layout/header/Logo.tsx` and add a `case` statement for the new company. Note, you might have to adjust the `h` prop to ensure the logo is displayed correctly. If you need to handle different logos for light and dark theme, create a custom component following the existing pattern.
4. Navigate to `src/utils/themes.ts` and add a new entry to the `CustomColors` object.
5. Navigate to `src/components/CompanyThemeManager.ts` and add a new entry to the `COMPANY_THEME_CONFIG` object.
6. Update your `parent_company` in Clerk and see the new theme in action! Make sure to test both light and dark mode.
