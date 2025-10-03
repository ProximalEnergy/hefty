import { useEffect, useState } from 'react'

const useVersionChecker = (checkInterval = 300_000) => {
  const [isOutdated, setIsOutdated] = useState(false)

  useEffect(() => {
    let initialVersion: string | null = null

    const checkVersion = async () => {
      try {
        const response = await fetch('/version.json', { cache: 'no-cache' })
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        const { version: fetchedVersion } = await response.json()

        if (!initialVersion) {
          initialVersion = fetchedVersion
        } else if (fetchedVersion !== initialVersion) {
          setIsOutdated(true)
        }
      } catch (error) {
        console.error('Error checking app version:', error)
      }
    }

    checkVersion() // Check immediately on load
    const interval = setInterval(checkVersion, checkInterval)

    return () => clearInterval(interval) // Cleanup on unmount
  }, [checkInterval])

  return isOutdated
}

export default useVersionChecker
