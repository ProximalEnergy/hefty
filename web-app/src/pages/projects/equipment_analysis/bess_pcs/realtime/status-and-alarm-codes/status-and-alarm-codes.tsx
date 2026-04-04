import { StatusAndAlarmCodes as SharedStatusAndAlarmCodes } from '@/components/bess-pcs/StatusAndAlarmCodes'

type StatusAndAlarmCodesProps = {
  projectId: string
}

export function StatusAndAlarmCodes({ projectId }: StatusAndAlarmCodesProps) {
  return <SharedStatusAndAlarmCodes projectId={projectId} />
}
