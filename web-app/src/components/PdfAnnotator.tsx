import {
  ActionIcon,
  Box,
  Group,
  SegmentedControl,
  Select,
  Stack,
  Text,
} from '@mantine/core'
import { IconCursorText, IconPointer, IconTrash } from '@tabler/icons-react'
import { PDFDocument, type PDFFont, StandardFonts, rgb } from 'pdf-lib'
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

pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`

interface Annotation {
  id: string
  page: number
  x: number
  y: number
  text: string
  fontSize: number
}

export interface PdfAnnotationDraft {
  page: number
  x: number
  y: number
  text: string
  fontSize?: number
}

export interface PdfPageImagePayload {
  page_number: number
  image_base64: string
  media_type: string
}

export interface AcroFieldSpec {
  name: string
  type: string
  page: number
  x: number
  y: number
  width: number
  height: number
  rect: number[]
  pdfPageX: number
  pdfPageY: number
  pdfPageWidth: number
  pdfPageHeight: number
  value: string
  label?: string
  labelSource?: 'left' | 'above'
}

export interface PdfAnnotatorHandle {
  isReady: () => boolean
  hasAcroForm: () => boolean
  getAcroFieldSpecs: () => AcroFieldSpec[]
  mergeAcroValues: (values: Record<string, string>) => void
  exportFilledPdf: () => Promise<Uint8Array>
  addAnnotations: (items: PdfAnnotationDraft[]) => void
  hasOverlayAnnotations: () => boolean
  clearOverlayAnnotations: () => void
  renderPageImagesForAssist: (
    maxPages: number,
  ) => Promise<PdfPageImagePayload[]>
}

interface PdfAnnotatorProps {
  fileUrl: string
}

const PDF_RENDER_WIDTH = 612
const FONT_SIZES = ['8', '10', '12', '14', '16', '20', '24']
const SIGNATURE_FONT_OPTIONS = [
  {
    value: 'script',
    label: 'Signature',
    css: '"Brush Script MT", "Segoe Script", cursive',
    pdf: StandardFonts.TimesRomanItalic,
  },
  {
    value: 'serif',
    label: 'Serif italic',
    css: 'Georgia, "Times New Roman", serif',
    pdf: StandardFonts.TimesRomanItalic,
  },
  {
    value: 'plain',
    label: 'Plain',
    css: 'Helvetica, Arial, sans-serif',
    pdf: StandardFonts.Helvetica,
  },
] as const

type SignatureFontValue = (typeof SIGNATURE_FONT_OPTIONS)[number]['value']

interface PdfTextItem {
  text: string
  x: number
  y: number
  width: number
}

interface PdfWidgetAnnotation {
  fieldName?: unknown
  fieldType?: unknown
  fieldValue?: unknown
  rect?: unknown
  subtype?: unknown
}

/** Same loader extras as `<Document options>` so fonts/CMaps render correctly. */
function assistPdfDocumentParams(data: Uint8Array) {
  return {
    data,
    cMapUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/cmaps/`,
    cMapPacked: true,
    standardFontDataUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/standard_fonts/`,
  }
}

function asString(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function isSignatureField(field: AcroFieldSpec) {
  const fieldName = field.name.toLowerCase()
  return field.type.toLowerCase() === 'sig' || fieldName.includes('sign')
}

function signatureFontOption(value: SignatureFontValue | undefined) {
  return (
    SIGNATURE_FONT_OPTIONS.find((option) => option.value === value) ??
    SIGNATURE_FONT_OPTIONS[0]
  )
}

function signaturePreviewRect(field: AcroFieldSpec) {
  if (field.rect.length !== 4 || field.pdfPageWidth <= 0) {
    return {
      x: field.x,
      y: field.y,
      width: field.width,
      height: field.height,
    }
  }

  const x1 = field.rect[0]!
  const y1 = field.rect[1]!
  const x2 = field.rect[2]!
  const y2 = field.rect[3]!
  const scale = PDF_RENDER_WIDTH / field.pdfPageWidth
  return {
    x: (Math.min(x1, x2) - field.pdfPageX) * scale,
    y: (field.pdfPageY + field.pdfPageHeight - Math.max(y1, y2)) * scale,
    width: Math.abs(x2 - x1) * scale,
    height: Math.abs(y2 - y1) * scale,
  }
}

function pageRenderMetrics(pageEl: HTMLDivElement) {
  const pageRect = pageEl.getBoundingClientRect()
  const canvasRect =
    pageEl.querySelector('canvas')?.getBoundingClientRect() ?? pageRect
  const scale = canvasRect.width / PDF_RENDER_WIDTH || 1
  return {
    offsetX: canvasRect.left - pageRect.left,
    offsetY: canvasRect.top - pageRect.top,
    scale,
    dragScale: PDF_RENDER_WIDTH / canvasRect.width || 1,
  }
}

function extractPdfTextItems(textContent: unknown, viewport: unknown) {
  const vp = viewport as {
    scale?: number
    convertToViewportPoint?: (x: number, y: number) => [number, number]
  }
  const content = textContent as { items?: unknown[] }
  const scale = typeof vp.scale === 'number' ? vp.scale : 1
  if (!Array.isArray(content.items) || !vp.convertToViewportPoint) return []

  const out: PdfTextItem[] = []
  for (const rawItem of content.items) {
    const item = rawItem as {
      str?: unknown
      transform?: unknown
      width?: unknown
    }
    const text = asString(item.str).trim()
    if (!text || !Array.isArray(item.transform)) continue
    const tx = Number(item.transform[4])
    const ty = Number(item.transform[5])
    if (!Number.isFinite(tx) || !Number.isFinite(ty)) continue
    const [x, y] = vp.convertToViewportPoint(tx, ty)
    const rawWidth = Number(item.width)
    out.push({
      text,
      x,
      y,
      width: Number.isFinite(rawWidth) ? rawWidth * scale : 0,
    })
  }
  return out
}

function nearbyFieldLabel(field: AcroFieldSpec, textItems: PdfTextItem[]) {
  const fieldMidY = field.y + field.height / 2
  const labelItems = textItems
    .map((item) => {
      const itemEndX = item.x + item.width
      const dy = Math.abs(item.y - fieldMidY)
      const text = item.text.replace(/\s+/g, ' ').trim()
      if (!text || text.length > 80) return null

      const leftGap = field.x - itemEndX
      const isLeftLabel =
        leftGap >= -4 && leftGap <= 180 && dy <= Math.max(12, field.height)
      const horizontalOverlap =
        Math.min(itemEndX, field.x + field.width) - Math.max(item.x, field.x)
      const verticalGap = field.y - item.y
      const isAboveLabel =
        verticalGap >= -4 &&
        verticalGap <= 28 &&
        horizontalOverlap >= Math.min(field.width, item.width) * 0.35
      if (!isLeftLabel && !isAboveLabel) return null
      return {
        text,
        source: isLeftLabel ? ('left' as const) : ('above' as const),
        score: dy + Math.max(0, leftGap) / 8,
      }
    })
    .filter(
      (
        item,
      ): item is { text: string; source: 'left' | 'above'; score: number } =>
        item !== null,
    )

  const primarySource = labelItems.some((item) => item.source === 'left')
    ? 'left'
    : 'above'
  const candidates = labelItems
    .filter((item) => item.source === primarySource)
    .sort((a, b) => a.score - b.score)
    .slice(0, 2)
    .map((item) => item.text)

  if (candidates.length === 0) return undefined
  return { text: candidates.join(' '), source: primarySource }
}

async function extractAcroFieldSpecs(
  bytes: Uint8Array,
  valueByName: Map<string, string>,
) {
  const loadingTask = pdfjs.getDocument(assistPdfDocumentParams(bytes.slice()))
  const pdf = await loadingTask.promise
  const specs: AcroFieldSpec[] = []

  for (let pageNum = 1; pageNum <= pdf.numPages; pageNum += 1) {
    const page = await pdf.getPage(pageNum)
    const rawPageView = (page as { view?: unknown }).view
    const pageView =
      Array.isArray(rawPageView) && rawPageView.length === 4
        ? rawPageView.map(Number)
        : [0, 0, 0, 0]
    const baseViewport = page.getViewport({
      scale: 1,
      rotation: page.rotate,
    })
    const pdfPageX = Number.isFinite(pageView[0]) ? pageView[0]! : 0
    const pdfPageY = Number.isFinite(pageView[1]) ? pageView[1]! : 0
    const pdfPageWidth =
      Number.isFinite(pageView[2]) && Number.isFinite(pageView[0])
        ? Math.abs(pageView[2]! - pageView[0]!)
        : baseViewport.width
    const pdfPageHeight =
      Number.isFinite(pageView[3]) && Number.isFinite(pageView[1])
        ? Math.abs(pageView[3]! - pageView[1]!)
        : baseViewport.height
    const viewport = page.getViewport({
      scale: PDF_RENDER_WIDTH / baseViewport.width,
      rotation: page.rotate,
    }) as {
      convertToViewportRectangle?: (rect: number[]) => number[]
    }
    const textContent = await page.getTextContent()
    const textItems = extractPdfTextItems(textContent, viewport)
    const annotations = (await page.getAnnotations({
      intent: 'display',
    })) as PdfWidgetAnnotation[]

    for (const annotation of annotations) {
      const name = asString(annotation.fieldName).trim()
      const rawRect = annotation.rect
      if (!name || !Array.isArray(rawRect) || rawRect.length !== 4) continue
      const rect = rawRect.map(Number)
      if (rect.some((n) => !Number.isFinite(n))) continue
      const viewRect = viewport.convertToViewportRectangle?.(rect)
      if (!viewRect || viewRect.length !== 4) continue

      const x = Math.min(viewRect[0], viewRect[2])
      const y = Math.min(viewRect[1], viewRect[3])
      const width = Math.abs(viewRect[2] - viewRect[0])
      const height = Math.abs(viewRect[3] - viewRect[1])
      const field: AcroFieldSpec = {
        name,
        type: asString(annotation.fieldType) || asString(annotation.subtype),
        page: pageNum,
        x,
        y,
        width,
        height,
        rect,
        pdfPageX,
        pdfPageY,
        pdfPageWidth,
        pdfPageHeight,
        value: valueByName.get(name) ?? asString(annotation.fieldValue).trim(),
      }
      const label = nearbyFieldLabel(field, textItems)
      field.label = label?.text
      field.labelSource = label?.source as AcroFieldSpec['labelSource']
      specs.push(field)
    }

    page.cleanup()
  }

  return specs
}

const PdfAnnotator = forwardRef<PdfAnnotatorHandle, PdfAnnotatorProps>(
  function PdfAnnotator({ fileUrl }, ref) {
    const [pdfBytes, setPdfBytes] = useState<Uint8Array | null>(null)
    const [ready, setReady] = useState(false)
    const [numPages, setNumPages] = useState(0)
    const [hasAcroForm, setHasAcroForm] = useState(false)
    const [formFields, setFormFields] = useState<AcroFieldSpec[]>([])
    const [annotations, setAnnotations] = useState<Annotation[]>([])
    const [signatureFontByName, setSignatureFontByName] = useState<
      Record<string, SignatureFontValue>
    >({})
    const [signaturePlacementByName, setSignaturePlacementByName] = useState<
      Record<string, { x: number; y: number }>
    >({})
    const [signatureNativeRectByName, setSignatureNativeRectByName] = useState<
      Record<string, { x: number; y: number; width: number; height: number }>
    >({})
    const [error, setError] = useState<string | null>(null)
    const [tool, setTool] = useState<'pointer' | 'text'>('pointer')
    const [fontSize, setFontSize] = useState('12')
    const [activeAnnotation, setActiveAnnotation] = useState<string | null>(
      null,
    )
    const activeAnnotationRef = useRef<string | null>(null)
    const [dragging, setDragging] = useState<{
      id: string
      startX: number
      startY: number
      origX: number
      origY: number
    } | null>(null)
    const [draggingSignature, setDraggingSignature] = useState<{
      name: string
      page: number
      startX: number
      startY: number
      origX: number
      origY: number
    } | null>(null)
    const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map())
    const pdfBytesRef = useRef<Uint8Array | null>(null)
    const formFieldsRef = useRef(formFields)
    const signatureFontByNameRef = useRef(signatureFontByName)
    const signaturePlacementByNameRef = useRef(signaturePlacementByName)
    const signatureNativeRectByNameRef = useRef(signatureNativeRectByName)
    const hasAcroFormRef = useRef(hasAcroForm)
    const readyRef = useRef(ready)
    const annotationsRef = useRef<Annotation[]>([])
    const formFieldValueKey = useMemo(
      () => formFields.map((f) => `${f.name}:${f.value}`).join('|'),
      [formFields],
    )

    useEffect(() => {
      pdfBytesRef.current = pdfBytes
    }, [pdfBytes])
    useEffect(() => {
      formFieldsRef.current = formFields
    }, [formFields])
    useEffect(() => {
      signatureFontByNameRef.current = signatureFontByName
    }, [signatureFontByName])
    useEffect(() => {
      signaturePlacementByNameRef.current = signaturePlacementByName
    }, [signaturePlacementByName])
    useEffect(() => {
      signatureNativeRectByNameRef.current = signatureNativeRectByName
    }, [signatureNativeRectByName])
    useEffect(() => {
      hasAcroFormRef.current = hasAcroForm
    }, [hasAcroForm])
    useEffect(() => {
      readyRef.current = ready
    }, [ready])
    useEffect(() => {
      annotationsRef.current = annotations
    }, [annotations])

    useEffect(() => {
      if (!hasAcroForm) return
      const valueByName = new Map(formFields.map((f) => [f.name, f.value]))
      const signatureFieldNames = new Set(
        formFields.filter(isSignatureField).map((field) => field.name),
      )
      window.requestAnimationFrame(() => {
        for (const pageEl of pageRefs.current.values()) {
          const inputs = pageEl.querySelectorAll('input, textarea, select')
          inputs.forEach((input) => {
            const el = input as HTMLInputElement | HTMLTextAreaElement
            if (el.dataset.proximalSignatureField === 'true') return
            const name =
              el.getAttribute('name') ||
              el.getAttribute('title') ||
              el.getAttribute('aria-label') ||
              ''
            if (signatureFieldNames.has(name)) {
              el.style.visibility = 'hidden'
              el.style.pointerEvents = 'none'
            } else {
              el.style.visibility = ''
              el.style.pointerEvents = ''
            }
            if (!valueByName.has(name)) return
            const nextValue = valueByName.get(name) ?? ''
            if (el.value !== nextValue) {
              el.value = nextValue
            }
          })
        }
      })
    }, [hasAcroForm, formFields, formFieldValueKey])

    useEffect(() => {
      if (!hasAcroForm) return
      const signatureFields = formFields.filter(isSignatureField)
      if (signatureFields.length === 0) {
        setSignatureNativeRectByName({})
        return
      }

      let cancelled = false
      let attempts = 0
      let timeoutId: number | null = null

      const measureNativeSignatureFields = () => {
        if (cancelled) return
        attempts += 1
        const next: Record<
          string,
          { x: number; y: number; width: number; height: number }
        > = {}
        for (const field of signatureFields) {
          const pageEl = pageRefs.current.get(field.page)
          if (!pageEl) continue
          const canvasRect =
            pageEl.querySelector('canvas')?.getBoundingClientRect() ??
            pageEl.getBoundingClientRect()
          const scale = PDF_RENDER_WIDTH / canvasRect.width || 1
          const controls = pageEl.querySelectorAll('input, textarea, select')
          for (const control of controls) {
            const el = control as HTMLInputElement | HTMLTextAreaElement
            if (el.dataset.proximalSignatureField === 'true') continue
            const name =
              el.getAttribute('name') ||
              el.getAttribute('title') ||
              el.getAttribute('aria-label') ||
              ''
            if (name !== field.name) continue
            const controlRect = el.getBoundingClientRect()
            next[field.name] = {
              x: (controlRect.left - canvasRect.left) * scale,
              y: (controlRect.top - canvasRect.top) * scale,
              width: controlRect.width * scale,
              height: controlRect.height * scale,
            }
          }
        }
        setSignatureNativeRectByName(next)

        if (
          Object.keys(next).length < signatureFields.length &&
          attempts < 20
        ) {
          timeoutId = window.setTimeout(measureNativeSignatureFields, 100)
        }
      }

      window.requestAnimationFrame(measureNativeSignatureFields)

      return () => {
        cancelled = true
        if (timeoutId != null) window.clearTimeout(timeoutId)
      }
    }, [hasAcroForm, formFields, formFieldValueKey, numPages])

    const clearOverlayAnnotations = useCallback(() => {
      setAnnotations([])
      setActiveAnnotation(null)
      setDragging(null)
    }, [])

    const mergeAcroValues = useCallback((values: Record<string, string>) => {
      setFormFields((prev) =>
        prev.map((f) =>
          values[f.name] !== undefined ? { ...f, value: values[f.name]! } : f,
        ),
      )
    }, [])

    const updateAcroFieldValue = useCallback((name: string, value: string) => {
      setFormFields((prev) =>
        prev.map((field) =>
          field.name === name ? { ...field, value } : field,
        ),
      )
    }, [])

    const updateSignatureFont = useCallback(
      (name: string, value: SignatureFontValue) => {
        setSignatureFontByName((prev) => ({ ...prev, [name]: value }))
      },
      [],
    )

    const addAnnotations = useCallback((items: PdfAnnotationDraft[]) => {
      setAnnotations((prev) => {
        const next = [...prev]
        for (const item of items) {
          const id = `${Date.now()}-${Math.random()}`
          next.push({
            id,
            page: item.page,
            x: item.x,
            y: item.y,
            text: item.text,
            fontSize: item.fontSize ?? 12,
          })
        }
        return next
      })
      setTool('pointer')
      setActiveAnnotation(null)
    }, [])

    const getPreviewAcroValues = useCallback(() => {
      const values = new Map<string, string>()
      const fieldNames = new Set(
        formFieldsRef.current.map((field) => field.name),
      )
      const controlsByPage = new Map<number, string[]>()

      for (const [pageNum, pageEl] of pageRefs.current.entries()) {
        const inputs = pageEl.querySelectorAll('input, textarea, select')
        inputs.forEach((input) => {
          const el = input as
            | HTMLInputElement
            | HTMLTextAreaElement
            | HTMLSelectElement
          const name =
            el.getAttribute('name') ||
            el.getAttribute('title') ||
            el.getAttribute('aria-label') ||
            ''
          if (fieldNames.has(name)) {
            values.set(name, el.value)
            return
          }
          const pageValues = controlsByPage.get(pageNum) ?? []
          pageValues.push(el.value)
          controlsByPage.set(pageNum, pageValues)
        })
      }

      for (const [pageNum, pageValues] of controlsByPage.entries()) {
        const pageFields = formFieldsRef.current.filter(
          (field) => field.page === pageNum && !values.has(field.name),
        )
        pageFields.forEach((field, index) => {
          const value = pageValues[index]
          if (value !== undefined) values.set(field.name, value)
        })
      }

      return values
    }, [])

    const renderPageImagesForAssist = useCallback(
      async (maxPages: number): Promise<PdfPageImagePayload[]> => {
        const bytes = pdfBytesRef.current
        if (!bytes?.length) {
          throw new Error('PDF not loaded')
        }
        const copy = bytes.slice()
        const loadingTask = pdfjs.getDocument(assistPdfDocumentParams(copy))
        const pdf = await loadingTask.promise
        const n = Math.min(maxPages, pdf.numPages)
        if (n < 1) {
          throw new Error('PDF has no pages')
        }
        const out: PdfPageImagePayload[] = []
        let lastRasterError: unknown = null
        for (let i = 1; i <= n; i += 1) {
          try {
            const page = await pdf.getPage(i)
            const rotate = page.rotate
            const vp1 = page.getViewport({ scale: 1, rotation: rotate })
            if (!(vp1.width > 0 && vp1.height > 0)) continue
            let s = PDF_RENDER_WIDTH / vp1.width
            let renderViewport = page.getViewport({
              scale: s,
              rotation: rotate,
            })
            while (
              Math.floor(renderViewport.width) < 1 ||
              Math.floor(renderViewport.height) < 1
            ) {
              s *= 2
              renderViewport = page.getViewport({
                scale: s,
                rotation: rotate,
              })
            }
            page.cleanup()
            const canvas = document.createElement('canvas')
            const ctx = canvas.getContext('2d', { alpha: false })
            if (!ctx) continue
            canvas.width = renderViewport.width
            canvas.height = renderViewport.height
            const task = page.render({
              canvasContext: ctx,
              viewport: renderViewport,
              canvas,
            })
            await task.promise
            const dataUrl = canvas.toDataURL('image/png')
            const image_base64 = dataUrl.includes(',')
              ? (dataUrl.split(',', 2)[1] ?? '')
              : dataUrl
            if (!image_base64 || image_base64.length < 32) {
              lastRasterError = new Error(
                `Encoded page ${i} image payload was empty`,
              )
              continue
            }
            out.push({
              page_number: i,
              image_base64,
              media_type: 'image/png',
            })
          } catch (e) {
            lastRasterError = e
          }
        }
        if (out.length === 0) {
          const hint =
            lastRasterError instanceof Error
              ? lastRasterError.message
              : lastRasterError
                ? String(lastRasterError)
                : 'unknown error'
          throw new Error(`Raster failed (${hint})`)
        }
        return out
      },
      [],
    )

    const exportFilledPdf = useCallback(async () => {
      const bytes = pdfBytesRef.current
      if (!bytes) throw new Error('PDF not loaded')

      const doc = await PDFDocument.load(bytes.slice(), {
        ignoreEncryption: true,
      })
      const font = await doc.embedFont(StandardFonts.Helvetica)

      if (hasAcroFormRef.current) {
        const form = doc.getForm()
        const previewValues = getPreviewAcroValues()
        for (const field of formFieldsRef.current) {
          if (isSignatureField(field)) continue
          try {
            const tf = form.getTextField(field.name)
            tf.setText(previewValues.get(field.name) ?? field.value)
          } catch {
            /* skip non-text fields */
          }
        }
        form.updateFieldAppearances(font)
        const pages = doc.getPages()
        const signatureFonts = new Map<SignatureFontValue, PDFFont>()
        for (const field of formFieldsRef.current.filter(isSignatureField)) {
          const value = previewValues.get(field.name) ?? field.value
          if (!value.trim()) continue
          const page = pages[field.page - 1]
          if (!page || field.rect.length !== 4) continue

          const fontOption = signatureFontOption(
            signatureFontByNameRef.current[field.name],
          )
          let signatureFont = signatureFonts.get(fontOption.value)
          if (!signatureFont) {
            signatureFont = await doc.embedFont(fontOption.pdf)
            signatureFonts.set(fontOption.value, signatureFont)
          }

          const x1 = field.rect[0]!
          const y1 = field.rect[1]!
          const x2 = field.rect[2]!
          const y2 = field.rect[3]!
          const previewRect = signaturePreviewRect(field)
          const nativeRect =
            signatureNativeRectByNameRef.current[field.name] ?? previewRect
          const placement = signaturePlacementByNameRef.current[field.name]
          const pageSize = page.getSize()
          const scale = pageSize.width / PDF_RENDER_WIDTH
          const xDelta = placement ? (placement.x - nativeRect.x) * scale : 0
          const yDelta = placement ? (placement.y - nativeRect.y) * scale : 0
          const x = Math.min(x1, x2) + xDelta + 3
          const y = Math.min(y1, y2) - yDelta + 2
          const width = Math.abs(x2 - x1) - 6
          const height = Math.abs(y2 - y1)
          const size = Math.max(9, Math.min(22, height * 0.7))
          page.drawText(value.trim(), {
            x,
            y: y + Math.max(0, (height - size) / 2),
            size,
            font: signatureFont,
            color: rgb(0, 0, 0),
            maxWidth: Math.max(20, width),
          })
          try {
            form.removeField(form.getField(field.name))
          } catch {
            /* keep the drawn signature even if the widget cannot be removed */
          }
        }
      } else {
        const pages = doc.getPages()
        for (const ann of annotationsRef.current) {
          if (!ann.text.trim()) continue
          const page = pages[ann.page - 1]
          if (!page) continue
          const { height } = page.getSize()
          const pdfY = height - ann.y - ann.fontSize * 0.8
          page.drawText(ann.text, {
            x: ann.x,
            y: pdfY,
            size: ann.fontSize,
            font,
            color: rgb(0, 0, 0),
          })
        }
      }

      return doc.save()
    }, [getPreviewAcroValues])

    useImperativeHandle(
      ref,
      () => ({
        isReady: () => readyRef.current,
        hasAcroForm: () => hasAcroFormRef.current,
        getAcroFieldSpecs: () => formFieldsRef.current,
        mergeAcroValues,
        exportFilledPdf,
        addAnnotations,
        hasOverlayAnnotations: () => annotationsRef.current.length > 0,
        clearOverlayAnnotations,
        renderPageImagesForAssist,
      }),
      [
        mergeAcroValues,
        exportFilledPdf,
        addAnnotations,
        clearOverlayAnnotations,
        renderPageImagesForAssist,
      ],
    )

    const options = useMemo(
      () => ({
        cMapUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/cmaps/`,
        cMapPacked: true,
        standardFontDataUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/standard_fonts/`,
      }),
      [],
    )

    useEffect(() => {
      let cancelled = false
      const load = async () => {
        try {
          setAnnotations([])
          setSignatureFontByName({})
          setSignaturePlacementByName({})
          setSignatureNativeRectByName({})
          setReady(false)
          setError(null)
          const resp = await fetch(fileUrl)
          if (!resp.ok) throw new Error('Failed to fetch PDF')
          const buf = await resp.arrayBuffer()
          if (cancelled) return
          const bytes = new Uint8Array(buf)
          setPdfBytes(bytes)

          const doc = await PDFDocument.load(bytes.slice(), {
            ignoreEncryption: true,
          })
          const form = doc.getForm()
          const fields = form.getFields()
          if (fields.length > 0) {
            setHasAcroForm(true)
            const valueByName = new Map<string, string>()
            for (const f of fields) {
              let val = ''
              try {
                const tf = form.getTextField(f.getName())
                val = tf.getText() ?? ''
              } catch {
                /* not a text field */
              }
              valueByName.set(f.getName(), val)
            }
            const acroFields = await extractAcroFieldSpecs(bytes, valueByName)
            if (cancelled) return
            setFormFields(
              acroFields.length > 0
                ? acroFields
                : fields.map((f, index) => ({
                    name: f.getName(),
                    type: '',
                    page: 1,
                    x: 0,
                    y: index * 20,
                    width: 0,
                    height: 0,
                    rect: [],
                    pdfPageX: 0,
                    pdfPageY: 0,
                    pdfPageWidth: PDF_RENDER_WIDTH,
                    pdfPageHeight: PDF_RENDER_WIDTH,
                    value: valueByName.get(f.getName()) ?? '',
                  })),
            )
          } else {
            setHasAcroForm(false)
            setFormFields([])
          }
          setReady(true)
        } catch (e) {
          if (!cancelled) setError(String(e))
        }
      }
      load()
      return () => {
        cancelled = true
      }
    }, [fileUrl])

    useEffect(() => {
      activeAnnotationRef.current = activeAnnotation
    }, [activeAnnotation])

    const handlePageClick = useCallback(
      (pageNum: number, e: React.MouseEvent<HTMLDivElement>) => {
        if (hasAcroForm) return
        if (tool === 'pointer') {
          setActiveAnnotation(null)
          return
        }
        const container = pageRefs.current.get(pageNum)
        if (!container) return
        const rect = container.getBoundingClientRect()
        const scale = PDF_RENDER_WIDTH / rect.width
        const x = (e.clientX - rect.left) * scale
        const y = (e.clientY - rect.top) * scale
        const id = `${Date.now()}-${Math.random()}`
        setAnnotations((prev) => [
          ...prev,
          { id, page: pageNum, x, y, text: '', fontSize: Number(fontSize) },
        ])
        setActiveAnnotation(id)
      },
      [hasAcroForm, tool, fontSize],
    )

    const updateAnnotationText = useCallback((id: string, text: string) => {
      setAnnotations((prev) =>
        prev.map((a) => (a.id === id ? { ...a, text } : a)),
      )
    }, [])

    const removeAnnotation = useCallback((id: string) => {
      setAnnotations((prev) => prev.filter((a) => a.id !== id))
      setActiveAnnotation(null)
    }, [])

    const handleDragStart = useCallback(
      (id: string, e: React.MouseEvent) => {
        if (tool !== 'pointer') return
        if ((e.target as HTMLElement).tagName === 'TEXTAREA') return
        e.preventDefault()
        e.stopPropagation()
        setActiveAnnotation(id)
        const ann = annotations.find((a) => a.id === id)
        if (!ann) return
        setDragging({
          id,
          startX: e.clientX,
          startY: e.clientY,
          origX: ann.x,
          origY: ann.y,
        })
      },
      [tool, annotations],
    )

    const handleSignatureDragStart = useCallback(
      (field: AcroFieldSpec, e: React.MouseEvent) => {
        e.preventDefault()
        e.stopPropagation()
        const previewRect = signaturePreviewRect(field)
        const nativeRect = signatureNativeRectByName[field.name] ?? previewRect
        const placement = signaturePlacementByName[field.name] ?? {
          x: nativeRect.x,
          y: nativeRect.y,
        }
        setDraggingSignature({
          name: field.name,
          page: field.page,
          startX: e.clientX,
          startY: e.clientY,
          origX: placement.x,
          origY: placement.y,
        })
      },
      [signatureNativeRectByName, signaturePlacementByName],
    )

    useEffect(() => {
      if (!dragging) return
      const onAnnotationMove = (e: MouseEvent) => {
        const ann = annotations.find((a) => a.id === dragging.id)
        if (!ann) return
        const container = pageRefs.current.get(ann.page)
        if (!container) return
        const rect = container.getBoundingClientRect()
        const scale = PDF_RENDER_WIDTH / rect.width
        const dx = (e.clientX - dragging.startX) * scale
        const dy = (e.clientY - dragging.startY) * scale
        setAnnotations((prev) =>
          prev.map((a) =>
            a.id === dragging.id
              ? { ...a, x: dragging.origX + dx, y: dragging.origY + dy }
              : a,
          ),
        )
      }
      const onUp = () => setDragging(null)
      window.addEventListener('mousemove', onAnnotationMove)
      window.addEventListener('mouseup', onUp)
      return () => {
        window.removeEventListener('mousemove', onAnnotationMove)
        window.removeEventListener('mouseup', onUp)
      }
    }, [dragging, annotations])

    useEffect(() => {
      if (!draggingSignature) return
      const onSignatureMove = (e: MouseEvent) => {
        const container = pageRefs.current.get(draggingSignature.page)
        if (!container) return
        const { dragScale } = pageRenderMetrics(container)
        const dx = (e.clientX - draggingSignature.startX) * dragScale
        const dy = (e.clientY - draggingSignature.startY) * dragScale
        setSignaturePlacementByName((prev) => ({
          ...prev,
          [draggingSignature.name]: {
            x: draggingSignature.origX + dx,
            y: draggingSignature.origY + dy,
          },
        }))
      }
      const onUp = () => setDraggingSignature(null)
      window.addEventListener('mousemove', onSignatureMove)
      window.addEventListener('mouseup', onUp)
      return () => {
        window.removeEventListener('mousemove', onSignatureMove)
        window.removeEventListener('mouseup', onUp)
      }
    }, [draggingSignature])

    const fileData = useMemo(() => ({ url: fileUrl }), [fileUrl])

    if (error) {
      return (
        <Text size="sm" c="red">
          {error}
        </Text>
      )
    }

    if (!ready) {
      return <Text size="sm">Loading PDF...</Text>
    }

    return (
      <Stack gap="sm">
        {hasAcroForm ? (
          <Text size="sm" fw={500}>
            Fillable form fields detected. Edit values directly in the PDF
            preview below.
          </Text>
        ) : (
          <Group justify="space-between" align="center">
            <Group gap="xs">
              <SegmentedControl
                size="xs"
                value={tool}
                onChange={(v) => setTool(v as 'pointer' | 'text')}
                data={[
                  {
                    value: 'pointer',
                    label: (
                      <Group gap={4} wrap="nowrap">
                        <IconPointer size={14} /> Select
                      </Group>
                    ),
                  },
                  {
                    value: 'text',
                    label: (
                      <Group gap={4} wrap="nowrap">
                        <IconCursorText size={14} /> Text
                      </Group>
                    ),
                  },
                ]}
              />
              <Select
                size="xs"
                w={80}
                value={fontSize}
                onChange={(v) => setFontSize(v ?? '12')}
                data={FONT_SIZES.map((s) => ({
                  value: s,
                  label: `${s}pt`,
                }))}
              />
            </Group>
            <Text size="xs" c="dimmed">
              {tool === 'text'
                ? 'Click on the PDF to place text'
                : 'Click an annotation to edit, drag to move'}
            </Text>
          </Group>
        )}

        <Box
          style={{
            width: '100%',
            maxHeight: 500,
            overflowY: 'auto',
            border: '1px solid var(--mantine-color-gray-3)',
            borderRadius: 8,
          }}
        >
          <Document
            file={fileData}
            onLoadSuccess={({ numPages: n }) => setNumPages(n)}
            options={options}
          >
            {Array.from({ length: numPages }, (_, i) => {
              const pageNum = i + 1
              const pageAnns = annotations.filter((a) => a.page === pageNum)
              const pageSignatureFields = formFields.filter(
                (field) => field.page === pageNum && isSignatureField(field),
              )
              return (
                <div
                  key={pageNum}
                  ref={(el) => {
                    if (el) pageRefs.current.set(pageNum, el)
                  }}
                  style={{
                    position: 'relative',
                    cursor: tool === 'text' ? 'crosshair' : 'default',
                  }}
                  onClick={(e) => handlePageClick(pageNum, e)}
                >
                  <Page
                    pageNumber={pageNum}
                    width={PDF_RENDER_WIDTH}
                    renderTextLayer={false}
                    renderAnnotationLayer={hasAcroForm}
                    renderForms={hasAcroForm}
                  />
                  {pageSignatureFields.map((field) => {
                    const container = pageRefs.current.get(pageNum)
                    const metrics = container
                      ? pageRenderMetrics(container)
                      : { offsetX: 0, offsetY: 0, scale: 1 }
                    const { offsetX, offsetY, scale } = metrics
                    const fontOption = signatureFontOption(
                      signatureFontByName[field.name],
                    )
                    const previewRect = signaturePreviewRect(field)
                    const nativeRect =
                      signatureNativeRectByName[field.name] ?? previewRect
                    const placement = signaturePlacementByName[field.name] ?? {
                      x: nativeRect.x,
                      y: nativeRect.y,
                    }
                    const fieldHeight = Math.max(22, nativeRect.height * scale)
                    const fieldWidth = Math.max(80, nativeRect.width * scale)
                    const fontSizePx = Math.max(
                      14,
                      Math.min(26, fieldHeight * 0.68),
                    )
                    const signatureLeft = offsetX + placement.x * scale
                    const signatureTop = offsetY + placement.y * scale
                    const signatureFontSelectorTop = fieldHeight + 3

                    return (
                      <div
                        key={`signature-${field.name}-${field.page}`}
                        style={{
                          position: 'absolute',
                          left: signatureLeft,
                          top: signatureTop,
                          width: fieldWidth,
                          minHeight: fieldHeight,
                          zIndex: 15,
                        }}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <input
                          data-proximal-signature-field="true"
                          name={field.name}
                          value={field.value}
                          placeholder="Type signature"
                          onChange={(e) =>
                            updateAcroFieldValue(field.name, e.target.value)
                          }
                          style={{
                            width: '100%',
                            height: fieldHeight,
                            boxSizing: 'border-box',
                            border: '1.5px solid #228be6',
                            borderRadius: 3,
                            background: 'rgba(255,255,255,0.9)',
                            color: '#000',
                            fontFamily: fontOption.css,
                            fontSize: fontSizePx,
                            lineHeight: 1,
                            padding: '1px 6px',
                            outline: 'none',
                          }}
                        />
                        <button
                          type="button"
                          onMouseDown={(e) =>
                            handleSignatureDragStart(field, e)
                          }
                          style={{
                            position: 'absolute',
                            left: 0,
                            top: -18,
                            height: 16,
                            fontSize: 10,
                            lineHeight: '14px',
                            padding: '0 5px',
                            color: '#fff',
                            background: '#228be6',
                            border: '1px solid #1971c2',
                            borderRadius: 3,
                            cursor: 'grab',
                          }}
                        >
                          Drag
                        </button>
                        <select
                          value={fontOption.value}
                          aria-label={`${field.name} signature font`}
                          onChange={(e) =>
                            updateSignatureFont(
                              field.name,
                              e.target.value as SignatureFontValue,
                            )
                          }
                          style={{
                            position: 'absolute',
                            right: 0,
                            top: signatureFontSelectorTop,
                            maxWidth: 118,
                            fontSize: 10,
                            color: '#000',
                            background: 'rgba(255,255,255,0.95)',
                            border: '1px solid #adb5bd',
                            borderRadius: 3,
                          }}
                        >
                          {SIGNATURE_FONT_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    )
                  })}
                  {pageAnns.map((ann) => {
                    const container = pageRefs.current.get(pageNum)
                    if (!container) return null
                    const rect = container.getBoundingClientRect()
                    const scale = rect.width / PDF_RENDER_WIDTH
                    const isActive = activeAnnotation === ann.id
                    const scaledFontSize = ann.fontSize * scale
                    const annotationLeft = ann.x * scale
                    const annotationTop = ann.y * scale
                    const editingMinHeight = scaledFontSize * 1.6
                    const editingWidth = Math.max(
                      80,
                      (ann.text.length + 4) * scaledFontSize * 0.6,
                    )
                    const displayMinHeight = scaledFontSize * 1.3

                    const isEditing = isActive && tool === 'text'

                    return (
                      <div
                        key={ann.id}
                        style={{
                          position: 'absolute',
                          left: annotationLeft,
                          top: annotationTop,
                          zIndex: isActive ? 20 : 10,
                          cursor: tool === 'pointer' ? 'grab' : 'default',
                          userSelect: 'none',
                        }}
                        onClick={(e) => {
                          e.stopPropagation()
                          setActiveAnnotation(ann.id)
                        }}
                        onMouseDown={(e) => handleDragStart(ann.id, e)}
                      >
                        <div
                          style={{
                            position: 'relative',
                            display: 'inline-block',
                          }}
                        >
                          {isEditing ? (
                            <textarea
                              value={ann.text}
                              placeholder="Type..."
                              autoFocus
                              onChange={(e) =>
                                updateAnnotationText(ann.id, e.target.value)
                              }
                              onMouseDown={(e) => e.stopPropagation()}
                              onBlur={() => {
                                window.setTimeout(() => {
                                  if (activeAnnotationRef.current !== ann.id)
                                    return
                                  setActiveAnnotation(null)
                                  setTool('pointer')
                                }, 0)
                              }}
                              rows={1}
                              style={{
                                fontSize: scaledFontSize,
                                lineHeight: 1.3,
                                fontFamily: 'Helvetica, Arial, sans-serif',
                                background: 'rgba(255,255,180,0.95)',
                                border: '1.5px solid #f59f00',
                                borderRadius: 2,
                                padding: '2px 4px',
                                margin: 0,
                                resize: 'both',
                                overflow: 'hidden',
                                minWidth: 80,
                                minHeight: editingMinHeight,
                                width: editingWidth,
                                outline: 'none',
                                color: '#000',
                              }}
                            />
                          ) : (
                            <div
                              style={{
                                fontSize: scaledFontSize,
                                lineHeight: 1.3,
                                fontFamily: 'Helvetica, Arial, sans-serif',
                                background: isActive
                                  ? 'rgba(255,255,180,0.9)'
                                  : 'rgba(255,255,200,0.6)',
                                border: isActive
                                  ? '1.5px dashed #f59f00'
                                  : '1px solid transparent',
                                borderRadius: 2,
                                padding: '2px 4px',
                                minWidth: 30,
                                minHeight: displayMinHeight,
                                color: '#000',
                                whiteSpace: 'pre-wrap',
                                cursor: tool === 'pointer' ? 'grab' : 'text',
                              }}
                              onDoubleClick={(e) => {
                                e.stopPropagation()
                                setActiveAnnotation(ann.id)
                                setTool('text')
                              }}
                            >
                              {ann.text || (
                                <span
                                  style={{
                                    color: '#999',
                                    fontStyle: 'italic',
                                  }}
                                >
                                  (empty)
                                </span>
                              )}
                            </div>
                          )}
                          {isActive && !isEditing && (
                            <ActionIcon
                              size={16}
                              color="red"
                              variant="filled"
                              style={{
                                position: 'absolute',
                                top: -8,
                                right: -8,
                              }}
                              onClick={(e) => {
                                e.stopPropagation()
                                removeAnnotation(ann.id)
                              }}
                            >
                              <IconTrash size={10} />
                            </ActionIcon>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )
            })}
          </Document>
        </Box>

        <Group justify="flex-end">
          <Text size="xs" c="dimmed">
            {hasAcroForm
              ? `${formFields.length} field(s)`
              : `${annotations.filter((a) => a.text.trim()).length} annotation(s)`}
          </Text>
        </Group>
      </Stack>
    )
  },
)

export default PdfAnnotator
