import { ProjectTypeEnum } from '@/api/enumerations'
import { Project } from '@/api/v1/operational/projects'

const formatProjectDescriptionValue = (number: number | null) => {
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
    case ProjectTypeEnum.PV:
      title = `${formatProjectDescriptionValue(project.poi)} MW PV`
      break
    case ProjectTypeEnum.BESS:
      title = `${formatProjectDescriptionValue(project.capacity_bess_power_ac)} MW / ${formatProjectDescriptionValue(project.capacity_bess_energy_bol_dc)} MWh BESS`
      break
    case ProjectTypeEnum.PVS:
      title = `${formatProjectDescriptionValue(project.poi)} MW PV | ${formatProjectDescriptionValue(project.capacity_bess_power_ac)} MW - ${formatProjectDescriptionValue(project.capacity_bess_energy_bol_dc)} MWh BESS`
      break
  }

  return title
}
