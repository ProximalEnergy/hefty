import DOMPurify from 'dompurify'
import type MarkdownIt from 'markdown-it'

interface RenderMarkdownOptions {
  content: string
  markdown: MarkdownIt
  sanitize?: boolean
  styleImages?: boolean
}

export const renderMarkdownToHtml = ({
  content,
  markdown,
  sanitize = false,
  styleImages = false,
}: RenderMarkdownOptions): { __html: string } => {
  const renderedContent = markdown.render(content)
  let styledContent = renderedContent
    .replace(/<p>/g, '<p style="margin: 0">')
    .replace(
      /<code>/g,
      '<code style="color: white; font-size: 0.875em; ' +
        'background-color: #333333; padding: 2px 4px; border-radius: 4px;">',
    )
    .replace(
      /<pre>/g,
      '<pre style="color: white; font-size: 0.875em; ' +
        'background-color: #333333; padding: 10px; border-radius: 4px; ' +
        'overflow-x: auto;">',
    )

  if (styleImages) {
    styledContent = styledContent.replace(
      /<img/g,
      '<img style="width: 100%; height: auto;"',
    )
  }

  if (sanitize) {
    const sanitizedContent = DOMPurify.sanitize(styledContent, {
      USE_PROFILES: { html: true },
    })
    return { __html: sanitizedContent }
  }

  return { __html: styledContent }
}
