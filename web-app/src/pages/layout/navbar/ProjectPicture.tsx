import { ProjectTypeEnum } from '@/api/enumerations'
import { useSelectProject } from '@/api/v1/operational/projects'
import ProjectInfoModal from '@/components/modals/ProjectInfoModal'
import { projectDescription } from '@/utils/projectDescription'
import {
  ActionIcon,
  BackgroundImage,
  Group,
  Overlay,
  Stack,
  Text,
  Tooltip,
  useComputedColorScheme,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { IconInfoCircle } from '@tabler/icons-react'
import { Fragment } from 'react/jsx-runtime'

const ProjectPicture = ({
  project,
  showText,
  collapsed,
}: {
  project: ReturnType<typeof useSelectProject>['data']
  showText: boolean
  collapsed: boolean
}) => {
  const computedColorScheme = useComputedColorScheme()
  const [opened, { open, close }] = useDisclosure(false)

  const description = project ? projectDescription(project) : ''
  const descriptionLines = description.split(' - ')

  return (
    <BackgroundImage
      src={
        project?.image_url ??
        (project?.project_type_id === ProjectTypeEnum.BESS
          ? 'https://iea.imgix.net/d771a759-2355-4f8e-89f4-d53e762d1047/shutterstock_1514163416.jpg?auto=compress%2Cformat&fit=min&h=630&q=80&rect=987%2C0%2C7013%2C3943&w=1200'
          : 'https://images.unsplash.com/photo-1586366461834-d2d65d725a2e?q=80&w=1974&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D')
      }
      radius={0}
      h={collapsed ? 60 : 150}
      pos="relative"
    >
      <Overlay
        color={computedColorScheme === 'dark' ? '#242424' : '#fff'}
        backgroundOpacity={computedColorScheme === 'dark' ? 0.5 : 0.7}
        zIndex={1}
      />
      <Stack p="md" gap={2} h="100%" justify="end">
        {showText && !collapsed && (
          <>
            <Group gap="xs" align="center" style={{ zIndex: 2 }}>
              <Text size="xl" fw={800} lh={1}>
                {project?.name_long}
              </Text>
              <Tooltip label="Project Information">
                <ActionIcon
                  variant="subtle"
                  color="gray"
                  size="sm"
                  onClick={open}
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.2)',
                    backdropFilter: 'blur(4px)',
                  }}
                >
                  <IconInfoCircle size={16} />
                </ActionIcon>
              </Tooltip>
            </Group>
            <Text fw={500} fs="italic" lh={1} style={{ zIndex: 2 }}>
              {descriptionLines.map((line, index) => (
                <Fragment key={index}>
                  {line}
                  {index < descriptionLines.length - 1 && <br />}
                </Fragment>
              ))}
            </Text>
          </>
        )}
      </Stack>
      <ProjectInfoModal opened={opened} onClose={close} projectData={project} />
    </BackgroundImage>
  )
}

export default ProjectPicture
