import { Box } from '@mantine/core'
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'

pdfjs.GlobalWorkerOptions.workerSrc =
  `https://unpkg.com/pdfjs-dist@${pdfjs.version}/` + 'build/pdf.worker.min.mjs'
export interface PdfViewerHandle {
  find: (query: string) => void
}

interface PdfViewerProps {
  fileUrl: string
}

interface TextItem {
  str: string
  dir: string
  transform: number[]
  width: number
  height: number
  fontName: string
  hasEOL: boolean
}

const PdfViewer = forwardRef<PdfViewerHandle, PdfViewerProps>(
  ({ fileUrl }, ref) => {
    const [numPages, setNumPages] = useState<number | null>(null)
    const [searchText, setSearchText] = useState('')
    const documentRef = useRef<HTMLDivElement | null>(null)

    // Memoize options to prevent unnecessary reloads
    const options = useMemo(
      () => ({
        cMapUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/cmaps/`,
        cMapPacked: true,
        standardFontDataUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/standard_fonts/`,
      }),
      [],
    )

    // Cleanup on unmount to prevent worker termination errors
    useEffect(() => {
      return () => {
        if (documentRef.current) {
          documentRef.current = null
        }
      }
    }, [])

    function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
      setNumPages(numPages)
    }

    useImperativeHandle(ref, () => ({
      find: (query: string) => {
        setSearchText(query)
      },
    }))

    const textRenderer = useCallback(
      (textItem: TextItem) => {
        if (!searchText) {
          return textItem.str
        }
        const regex = new RegExp(`(${searchText})`, 'gi')
        const parts = textItem.str.split(regex)
        return parts
          .map((part) => {
            if (part.toLowerCase() === searchText.toLowerCase()) {
              return `<mark>${part}</mark>`
            }
            return part
          })
          .join('')
      },
      [searchText],
    )

    // Scroll to first match when search text changes
    useEffect(() => {
      if (searchText && numPages) {
        const timer = setTimeout(() => {
          const firstMark = document.querySelector('mark')
          if (firstMark) {
            firstMark.scrollIntoView({
              behavior: 'smooth',
              block: 'center',
            })
          }
        }, 500)
        return () => clearTimeout(timer)
      }
    }, [searchText, numPages])

    return (
      <Box
        style={{
          width: '100%',
          height: '1000px',
          maxHeight: '1000px',
          border: '1px solid #dee2e6',
          borderRadius: '8px',
          overflowY: 'auto',
          position: 'relative',
        }}
      >
        <Document
          file={fileUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          options={options}
          onLoadError={(error) => console.error('PDF load error:', error)}
          inputRef={documentRef}
        >
          {Array.from({ length: numPages || 0 }, (_, index) => {
            const pageNumber = index + 1
            const pageKey = `page_${pageNumber}`
            const pageLoadErrorMessage = `Page ${pageNumber} load error:`

            return (
              <Page
                key={pageKey}
                pageNumber={pageNumber}
                renderTextLayer={true}
                renderAnnotationLayer={true}
                customTextRenderer={searchText ? textRenderer : undefined}
                onLoadError={(error) =>
                  console.warn(pageLoadErrorMessage, error)
                }
              />
            )
          })}
        </Document>
      </Box>
    )
  },
)

PdfViewer.displayName = 'PdfViewer'

export default PdfViewer
