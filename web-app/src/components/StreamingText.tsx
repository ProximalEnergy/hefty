import { Loader, Text, TextProps } from '@mantine/core'
import { useEffect, useState } from 'react'

interface StreamingTextProps extends Omit<TextProps, 'children'> {
  text: string
  speed?: number // milliseconds per character
  onComplete?: () => void
  className?: string
}

export const StreamingText = ({
  text,
  speed = 50,
  onComplete,
  className,
  ...textProps
}: StreamingTextProps) => {
  const [displayedText, setDisplayedText] = useState('')
  const [isComplete, setIsComplete] = useState(false)
  const [showSpinner, setShowSpinner] = useState(false)

  useEffect(() => {
    if (!text) return

    setDisplayedText('')
    setIsComplete(false)
    setShowSpinner(false)

    let currentIndex = 0
    const interval = setInterval(() => {
      if (currentIndex < text.length) {
        setDisplayedText(text.slice(0, currentIndex + 1))
        currentIndex++
      } else {
        clearInterval(interval)
        setIsComplete(true)
        // Show spinner briefly after text is complete
        setShowSpinner(true)
        setTimeout(() => {
          setShowSpinner(false)
          onComplete?.()
        }, 1000) // Show spinner for 1 second after completion
      }
    }, speed)

    return () => clearInterval(interval)
  }, [text, speed, onComplete])

  return (
    <Text className={className} {...textProps}>
      {displayedText}
      {!isComplete && <span className="streaming-cursor">|</span>}
      {showSpinner && (
        <span
          style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
        >
          <Loader size="xs" />
        </span>
      )}
    </Text>
  )
}
