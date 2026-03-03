export type KPIInstanceKey = `${number}::${string}`
export type KPIInstanceState = Record<KPIInstanceKey, boolean>

export const keyOf = (kpiTypeId: number, projectId: string): KPIInstanceKey =>
  `${kpiTypeId}::${projectId}` as const

export const setValue = (
  prev: KPIInstanceState,
  kpiTypeId: number,
  projectId: string,
  visible: boolean | null,
): KPIInstanceState => {
  const key = keyOf(kpiTypeId, projectId)

  if (visible === null) {
    if (!(key in prev)) return prev
    const { [key]: _removed, ...rest } = prev
    return rest
  }

  const existing = prev[key]
  if (existing === visible) return prev

  return {
    ...prev,
    [key]: visible,
  }
}
