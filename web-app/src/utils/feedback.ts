import type { FeedbackFormData } from '@/hooks/types'

export type FeedbackFormDefaults = Partial<FeedbackFormData>

export const OPEN_FEEDBACK_FORM_EVENT = 'proximal:open-feedback-form'

export const openFeedbackForm = (defaults: FeedbackFormDefaults = {}) => {
  window.dispatchEvent(
    new CustomEvent<FeedbackFormDefaults>(OPEN_FEEDBACK_FORM_EVENT, {
      detail: defaults,
    }),
  )
}
