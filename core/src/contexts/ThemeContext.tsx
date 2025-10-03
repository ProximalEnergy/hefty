import { CustomColors } from '@/utils/themes'
import { DefaultMantineColor } from '@mantine/core'
import React, { ReactNode, createContext, useContext, useState } from 'react'

// Remove the generic string
type LiteralColorsOnly<T> = T extends string
  ? string extends T
    ? never
    : T
  : never

export type KnownMantineColor = LiteralColorsOnly<DefaultMantineColor>

interface ThemeContextType {
  primaryColor: KnownMantineColor | CustomColors
  setPrimaryColor: (color: KnownMantineColor | CustomColors) => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}

interface ThemeProviderProps {
  children: ReactNode
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const [primaryColor, setPrimaryColor] = useState<
    KnownMantineColor | CustomColors
  >('proximal-blue')

  return (
    <ThemeContext.Provider value={{ primaryColor, setPrimaryColor }}>
      {children}
    </ThemeContext.Provider>
  )
}
