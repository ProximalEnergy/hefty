import { Viewer, Worker } from '@react-pdf-viewer/core'
import '@react-pdf-viewer/core/lib/styles/index.css'
import { defaultLayoutPlugin } from '@react-pdf-viewer/default-layout'
import '@react-pdf-viewer/default-layout/lib/styles/index.css'
import { searchPlugin } from '@react-pdf-viewer/search'
import '@react-pdf-viewer/search/lib/styles/index.css'
import { forwardRef, useImperativeHandle, useState } from 'react'

export interface PdfViewerHandle {
  find: (query: string) => void
}

interface PdfViewerProps {
  fileUrl: string
}

const PdfViewer = forwardRef<PdfViewerHandle, PdfViewerProps>(
  ({ fileUrl }, ref) => {
    const defaultLayoutPluginInstance = defaultLayoutPlugin()
    const searchPluginInstance = searchPlugin()
    const [isSearching, setIsSearching] = useState(false)
    const [searchStatus, setSearchStatus] = useState<string>('')

    useImperativeHandle(ref, () => ({
      find: (query: string) => {
        if (query) {
          setIsSearching(true)
          setSearchStatus(`Searching for: "${query}"`)

          // Clear previous highlights first
          searchPluginInstance.clearHighlights()

          // Normalize the search query for better results
          const normalizedQuery = query
            .replace(/\s*\n\s*/g, ' ') // Replace newlines with spaces
            .replace(/\s+/g, ' ') // Collapse multiple spaces into single space
            .trim() // Remove leading/trailing whitespace

          // Try multiple search strategies for better results
          const searchStrategies = [
            normalizedQuery, // Normalized version
            query.trim(), // Original trimmed
            query.replace(/['"]/g, '').trim(), // Remove quotes
            query
              .replace(/[^\w\s]/g, ' ')
              .replace(/\s+/g, ' ')
              .trim(), // Remove punctuation
            query.split(' ').slice(0, 5).join(' '), // First 5 words if it's long
            query.split(' ').slice(0, 3).join(' '), // First 3 words
            query.split(' ').slice(0, 2).join(' '), // First 2 words
            // For contract-specific text, try common variations
            query.replace(/\b(Agreement|Contract|Agreement)\b/gi, 'Agreement'),
            query.replace(/\b(shall|will|must)\b/gi, 'shall'),
            query.replace(/\b(Party|Parties)\b/gi, 'Party'),
            // Try without common legal words that might vary
            query
              .replace(
                /\b(the|a|an|and|or|but|in|on|at|to|for|of|with|by)\b/gi,
                '',
              )
              .replace(/\s+/g, ' ')
              .trim(),
          ]

          // Remove duplicates and empty strings
          const uniqueStrategies = [...new Set(searchStrategies)].filter(
            (str) => str.length > 0,
          )

          // Try each strategy until one works
          const trySearch = async (strategies: string[], index: number = 0) => {
            if (index >= strategies.length) {
              setIsSearching(false)
              setSearchStatus('Search completed')
              setTimeout(() => setSearchStatus(''), 3000)
              return
            }

            const currentStrategy = strategies[index]
            setSearchStatus(`Trying: "${currentStrategy}"`)

            // Perform the search using the correct API
            try {
              // First highlight the text
              if (typeof searchPluginInstance.highlight === 'function') {
                searchPluginInstance.highlight(currentStrategy)

                // Then jump to the first match after a short delay
                setTimeout(() => {
                  if (typeof searchPluginInstance.jumpToMatch === 'function') {
                    searchPluginInstance.jumpToMatch(0) // Jump to first match
                  }
                }, 100)
              } else {
                console.warn('Highlight method not available')
              }
            } catch (error) {
              console.warn(
                'Search failed for strategy:',
                currentStrategy,
                error,
              )
            }

            // Try next strategy after a short delay
            setTimeout(() => {
              trySearch(strategies, index + 1)
            }, 200)
          }

          trySearch(uniqueStrategies)
        }
      },
    }))

    return (
      <div
        style={{
          width: '100%',
          height: '1000px',
          maxHeight: '1000px',
          border: '1px solid #dee2e6',
          borderRadius: '8px',
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        {/* Search Status Indicator */}
        {searchStatus && (
          <div
            style={{
              position: 'absolute',
              top: '10px',
              right: '10px',
              backgroundColor: isSearching ? '#4dabf7' : '#51cf66',
              color: 'white',
              padding: '8px 12px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 500,
              zIndex: 1000,
              boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
              maxWidth: '300px',
              wordWrap: 'break-word',
            }}
          >
            {isSearching ? '🔍' : '✅'} {searchStatus}
          </div>
        )}

        <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
          <Viewer
            fileUrl={fileUrl}
            plugins={[defaultLayoutPluginInstance, searchPluginInstance]}
          />
        </Worker>
      </div>
    )
  },
)

PdfViewer.displayName = 'PdfViewer'

export default PdfViewer
