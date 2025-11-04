import { CustomColors } from '@/utils/themes'
import { DefaultMantineColor } from '@mantine/core'
import React, { ReactNode, useState } from 'react'

import { ThemeContext } from './ThemeContext.utils'

// Remove the generic string
type LiteralColorsOnly<T> = T extends string
  ? string extends T
    ? never
    : T
  : never

export type KnownMantineColor = LiteralColorsOnly<DefaultMantineColor>

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
