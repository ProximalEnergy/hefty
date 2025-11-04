import { CustomColors } from '@/utils/themes'
import { createContext, useContext } from 'react'

import { KnownMantineColor } from './ThemeContext'

interface ThemeContextType {
  primaryColor: KnownMantineColor | CustomColors
  setPrimaryColor: (color: KnownMantineColor | CustomColors) => void
}
export const ThemeContext = createContext<ThemeContextType | undefined>(
  undefined,
)
export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
