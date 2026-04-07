import { Box, Text, rem } from '@mantine/core'
import { type ReactNode, useLayoutEffect, useRef, useState } from 'react'

/** Same numeric input as stat cards using `fz={32}` (scaled via Mantine `rem`). */
const STAT_CARD_VALUE_FZ = 32

/** Subpixel / padding slack so bold glyphs are not clipped at the edge. */
const FIT_WIDTH_BUFFER_PX = 6

type AutoFitStatValueProps = {
  children: ReactNode
  minFontSize?: number
  fw?: number
}

/** Shrinks font size so a single-line stat value fits its container. */
export function AutoFitStatValue({
  children,
  minFontSize = 14,
  fw = 700,
}: AutoFitStatValueProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const textRef = useRef<HTMLParagraphElement>(null)
  const [fontSizePx, setFontSizePx] = useState<number | null>(null)

  useLayoutEffect(() => {
    const container = containerRef.current
    const textEl = textRef.current
    if (!container || !textEl) return

    const fit = () => {
      const available = Math.max(0, container.clientWidth - FIT_WIDTH_BUFFER_PX)
      if (available <= 0) return

      textEl.style.fontSize = rem(STAT_CARD_VALUE_FZ)
      const maxPx = Math.round(
        parseFloat(window.getComputedStyle(textEl).fontSize),
      )
      textEl.style.fontSize = rem(minFontSize)
      const minPx = Math.min(
        maxPx,
        Math.round(parseFloat(window.getComputedStyle(textEl).fontSize)),
      )

      let low = minPx
      let high = maxPx
      let best = minPx

      while (low <= high) {
        const mid = Math.floor((low + high) / 2)
        textEl.style.fontSize = `${mid}px`
        if (textEl.scrollWidth <= available) {
          best = mid
          low = mid + 1
        } else {
          high = mid - 1
        }
      }
      setFontSizePx(best)
    }

    fit()
    const ro = new ResizeObserver(fit)
    ro.observe(container)
    return () => ro.disconnect()
  }, [children, minFontSize])

  return (
    <Box
      ref={containerRef}
      w="100%"
      maw="100%"
      style={{ minWidth: 0, overflow: 'hidden' }}
    >
      <Text
        ref={textRef}
        fw={fw}
        lh={1.15}
        style={{
          fontSize:
            fontSizePx !== null ? `${fontSizePx}px` : rem(STAT_CARD_VALUE_FZ),
          whiteSpace: 'nowrap',
          width: 'max-content',
        }}
      >
        {children}
      </Text>
    </Box>
  )
}
