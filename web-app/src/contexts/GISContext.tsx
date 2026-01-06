import { useMantineTheme } from '@mantine/core'
import { useLocalStorage } from '@mantine/hooks'
import React, { createContext } from 'react'

type Colors = { id: number; value: string }[]

// Temperature colorscale: blue (cold) to red (hot)
const COLORS_TEMPERATURE: Colors = [
  { id: 1, value: '#2166AC' }, // Blue for cold (low)
  { id: 2, value: '#4393C3' }, // Light blue
  { id: 3, value: '#FDB863' }, // Orange
  { id: 4, value: '#B2182B' }, // Red for hot (high)
]

// Define the type for the GIS context
interface GISContextType {
  showLabels: boolean
  setShowLabels: React.Dispatch<React.SetStateAction<boolean>>
  showSatellite: boolean
  setShowSatellite: React.Dispatch<React.SetStateAction<boolean>>
  colorsHighLow: Colors
  setColorsHighLow: React.Dispatch<React.SetStateAction<Colors>>
  colorsGoodBad: Colors
  setColorsGoodBad: React.Dispatch<React.SetStateAction<Colors>>
  colorsTemperature: Colors
}

// Create the GIS context with a default value of undefined
const GISContext = createContext<GISContextType | undefined>(undefined)

// Define the provider component for the GIS context
const GISProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const theme = useMantineTheme()

  const [showLabels, setShowLabels] = useLocalStorage<boolean>({
    key: 'proximal-gis-show-labels',
    defaultValue: false,
  })
  const [showSatellite, setShowSatellite] = useLocalStorage<boolean>({
    key: 'proximal-gis-show-satellite',
    defaultValue: false,
  })
  const [colorsHighLow, setColorsHighLow] = useLocalStorage<Colors>({
    key: 'proximal-gis-colors-high-low',
    defaultValue: [
      { id: 1, value: theme.colors.dark[1] },
      { id: 2, value: theme.colors.green[7] },
    ],
  })
  const [colorsGoodBad, setColorsGoodBad] = useLocalStorage<Colors>({
    key: 'proximal-gis-colors-good-bad',
    defaultValue: [
      { id: 1, value: theme.colors.red[7] },
      { id: 2, value: theme.colors.yellow[7] },
      { id: 3, value: theme.colors.green[7] },
    ],
  })

  return (
    <GISContext.Provider
      value={{
        showLabels,
        setShowLabels,
        showSatellite,
        setShowSatellite,
        colorsHighLow,
        setColorsHighLow,
        colorsGoodBad,
        setColorsGoodBad,
        colorsTemperature: COLORS_TEMPERATURE,
      }}
    >
      {children}
    </GISContext.Provider>
  )
}

export { GISContext, GISProvider }
