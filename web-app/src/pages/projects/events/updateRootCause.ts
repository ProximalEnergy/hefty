interface UpdateRootCausePayload {
  project_id: string
  event_id: number
  root_cause_id?: number
}

interface BuildUpdateRootCauseHandlerArgs {
  eventId: number
  projectId: string | undefined
  mutate: (payload: UpdateRootCausePayload) => void
}

export const buildUpdateRootCauseHandler = ({
  eventId,
  projectId,
  mutate,
}: BuildUpdateRootCauseHandlerArgs) => {
  return (rootCauseId: number | null) => {
    mutate({
      project_id: projectId || '-1',
      event_id: eventId,
      root_cause_id: rootCauseId !== null ? rootCauseId : undefined,
    })
  }
}
