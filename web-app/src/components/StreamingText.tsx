import { Text, TextProps } from '@mantine/core'
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

  useEffect(() => {
    if (!text) return

    setDisplayedText('')
    setIsComplete(false)

    let currentIndex = 0
    const interval = setInterval(() => {
      if (currentIndex < text.length) {
        setDisplayedText(text.slice(0, currentIndex + 1))
        currentIndex++
      } else {
        clearInterval(interval)
        setIsComplete(true)
        onComplete?.()
      }
    }, speed)

    return () => clearInterval(interval)
  }, [text, speed, onComplete])

  return (
    <Text className={className} {...textProps}>
      {displayedText}
      {!isComplete && <span className="streaming-cursor">|</span>}
    </Text>
  )
}
