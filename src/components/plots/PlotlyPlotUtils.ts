import { MantineColorsTuple, MantineTheme } from '@mantine/core'
import chroma from 'chroma-js'

// Function to calculate color distance using CIELAB color space
function getColorDistance(color1: string, color2: string): number {
  const lab1 = chroma(color1).lab()
  const lab2 = chroma(color2).lab()

  // Calculate Euclidean distance in LAB color space
  return Math.sqrt(
    Math.pow(lab1[0] - lab2[0], 2) +
      Math.pow(lab1[1] - lab2[1], 2) +
      Math.pow(lab1[2] - lab2[2], 2),
  )
}

// Function to find the closest color to the primary color
function findClosestColor(
  colors: Record<string, MantineColorsTuple>,
  primaryColor: string,
): string | null {
  const primaryColorHex = colors[primaryColor]?.[7] // Get the main shade of the primary color
  if (!primaryColorHex) return null

  let minDistance = Infinity
  let closestColor: string | null = null

  Object.entries(colors).forEach(([colorName, colorShades]) => {
    if (colorName === primaryColor) return // Skip the primary color itself
    const colorHex = colorShades[7] // Get the main shade of each color
    const distance = getColorDistance(primaryColorHex, colorHex)

    if (distance < minDistance) {
      minDistance = distance
      closestColor = colorName
    }
  })

  return closestColor
}

export const traceColors = (theme: MantineTheme) => {
  // Mantine colors we want to keep
  const mantineColorsToKeep = ['red', 'violet', 'blue', 'green', 'orange']

  // Mantine colors we want to keep plus the primary color
  // If the primary color is already a Mantine color, we don't need to add it to the list
  const colorsToKeep = mantineColorsToKeep.includes(theme.primaryColor)
    ? mantineColorsToKeep
    : [...mantineColorsToKeep, theme.primaryColor]

  // Create an object that maps each color to the array of shades from Mantine
  // NOTE - This includes our custom colors as well
  let colors = Object.entries(theme.colors).reduce<
    Record<string, typeof theme.colors.dark>
  >((obj, [key, value]) => {
    if (colorsToKeep.includes(key)) {
      obj[key] = value
    }
    return obj
  }, {})

  // If we added a custom color to the list, remove the closest Mantine color
  if (!mantineColorsToKeep.includes(theme.primaryColor)) {
    const closestColor = findClosestColor(colors, theme.primaryColor)
    if (closestColor) {
      delete colors[closestColor]
    }
  }

  // Move the primary color to the front of the list so it is used when there is only one trace
  const primaryColor = theme.colors[theme.primaryColor]
  delete colors[theme.primaryColor]
  colors = {
    [theme.primaryColor]: primaryColor,
    ...colors,
  }

  // Specify which of the 10 shades we want to use for each color
  const lastColors = Object.values(colors).map((color) => [
    color[7],
    color[6],
    color[5],
  ])

  // Rearrange the colors so that they "descend" by shade
  const orderedColors = []
  for (let i = 0; i < 3; i++) {
    for (const set of lastColors) {
      orderedColors.push(set[i])
    }
  }

  return orderedColors
}
