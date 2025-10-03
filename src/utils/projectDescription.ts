import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { Project } from '@/api/v1/operational/projects'

const formatNumber = (number: number | null) => {
  if (number === null) {
    return number
  }

  if (number <= 20) {
    return Number(number.toFixed(2))
  } else if (number <= 100) {
    return Number(number.toFixed(1))
  } else {
    return Math.floor(number)
  }
}

export const projectDescription = (project: Project) => {
  let title = ''
  switch (project.project_type_id) {
    case ProjectTypeId.PV:
      title = `${formatNumber(project.poi)} MW PV`
      break
    case ProjectTypeId.BESS:
      title = `${formatNumber(project.capacity_bess_power_ac)} MW / ${formatNumber(project.capacity_bess_energy_bol_dc)} MWh BESS`
      break
    case ProjectTypeId.PV_BESS:
      title = `${formatNumber(project.poi)} MW PV | ${formatNumber(project.capacity_bess_power_ac)} MW - ${formatNumber(project.capacity_bess_energy_bol_dc)} MWh BESS`
      break
  }

  return title
}
