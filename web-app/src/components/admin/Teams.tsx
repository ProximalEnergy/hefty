import {
  useAddTeamMember,
  useCreateTeam,
  useDeleteTeam,
  useGetTeamsWithMembers,
  useRemoveTeamMember,
  useRenameTeam,
} from '@/api/admin'
import { useGetSelfCompanyUsers, useGetUserSelf } from '@/api/v1/admin/users'
import {
  Badge,
  Button,
  Card,
  Divider,
  Grid,
  Group,
  Loader,
  Modal,
  MultiSelect,
  NavLink,
  ScrollArea,
  Stack,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core'
import { useDisclosure, useLocalStorage } from '@mantine/hooks'
import { useQueryClient } from '@tanstack/react-query'
import type { AxiosResponse } from 'axios'
import { useCallback, useEffect, useMemo, useState } from 'react'

export function Teams() {
  const self = useGetUserSelf({})
  const companyId = self.data?.company_id

  const teams = useGetTeamsWithMembers({
    queryParams: { company_id: companyId || '' },
    queryOptions: { enabled: !!companyId },
  })
  const createTeam = useCreateTeam()
  const allUsers = useGetSelfCompanyUsers({})
  const addMember = useAddTeamMember()
  const removeMember = useRemoveTeamMember()
  const deleteTeam = useDeleteTeam()
  const renameTeam = useRenameTeam()
  const queryClient = useQueryClient()

  const [createOpen, { open: openCreate, close: closeCreate }] =
    useDisclosure(false)
  const [renameOpen, { open: openRename, close: closeRename }] =
    useDisclosure(false)
  const [deleteOpen, { open: openDelete, close: closeDelete }] =
    useDisclosure(false)

  const [selectedTeamId, setSelectedTeamId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState('')
  const [pendingSave, setPendingSave] = useState(false)
  const [renaming, setRenaming] = useState(false)
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [draftMembers, setDraftMembers] = useState<string[]>([])

  // Keep selection valid on first load and after list changes (e.g., delete)
  useEffect(() => {
    const list = teams.data ?? []
    if (!list.length) {
      if (selectedTeamId !== null) setSelectedTeamId(null)
      if (draftMembers.length) setDraftMembers([])
      return
    }
    // If current selection missing, pick first team
    const stillExists = list.some((t) => t.team_id === selectedTeamId)
    const nextId = stillExists ? selectedTeamId : list[0].team_id
    if (nextId !== selectedTeamId) {
      setSelectedTeamId(nextId)
      const nextTeam = list.find((t) => t.team_id === nextId)!
      setDraftMembers(nextTeam.members.map((m) => m.user_id))
    }
    // oxlint-disable-next-line react/exhaustive-deps
  }, [teams.data]) // intentionally not depending on draftMembers/selectedTeamId to avoid loops

  const selectedTeam = useMemo(() => {
    const list = teams.data ?? []
    if (!list.length) return undefined
    return list.find((t) => t.team_id === selectedTeamId) ?? list[0]
  }, [teams.data, selectedTeamId])

  const resetDraft = useCallback(() => {
    if (!selectedTeam) return
    setDraftMembers(selectedTeam.members.map((m) => m.user_id))
  }, [selectedTeam])

  const handleSaveMembers = useCallback(async () => {
    if (!selectedTeam) return
    setPendingSave(true)
    const current = selectedTeam.members.map((m) => m.user_id)
    const added = draftMembers.filter((id) => !current.includes(id))
    const removed = current.filter((id) => !draftMembers.includes(id))
    try {
      await Promise.all([
        ...added.map((user_id) =>
          addMember.mutateAsync({ team_id: selectedTeam.team_id, user_id }),
        ),
        ...removed.map((user_id) =>
          removeMember.mutateAsync({ team_id: selectedTeam.team_id, user_id }),
        ),
      ])
      // Optionally refetch the selected team's data if the server returns derived members
      await queryClient.refetchQueries({ queryKey: ['getTeamsWithMembers'] })
    } finally {
      setPendingSave(false)
    }
  }, [addMember, removeMember, draftMembers, queryClient, selectedTeam])

  const handleRename = useCallback(async () => {
    if (!selectedTeam) return
    const newName = renameValue.trim()
    if (!newName || newName === selectedTeam.name_long) return
    setRenaming(true)
    try {
      await renameTeam.mutateAsync({
        team_id: selectedTeam.team_id,
        name_long: newName,
      })
      await queryClient.refetchQueries({ queryKey: ['getTeamsWithMembers'] })
    } finally {
      setRenaming(false)
      closeRename()
    }
  }, [renameValue, renameTeam, queryClient, selectedTeam, closeRename]) // renameName is a typo; see final note below

  const handleDelete = useCallback(async () => {
    if (!selectedTeam) return
    if ((deleteConfirm || '').trim() !== selectedTeam.name_long) return
    try {
      setDeleting(true)
      await deleteTeam.mutateAsync({ team_id: selectedTeam.team_id })
      await queryClient.refetchQueries({ queryKey: ['getTeamsWithMembers'] })
      // After refetch, our effect will notice the missing selection
      // and auto-select the first available team + reset draftMembers.
    } finally {
      setDeleteConfirm('')
      closeDelete()
      // Defer resetting deleting so spinner persists until after modal close
      setTimeout(() => setDeleting(false), 0)
    }
  }, [deleteConfirm, deleteTeam, queryClient, selectedTeam, closeDelete])

  const hasMemberChanges = useMemo(() => {
    if (!selectedTeam) return false
    const current = selectedTeam.members.map((m) => m.user_id).sort()
    const draft = [...draftMembers].sort()
    if (current.length !== draft.length) return true
    for (let i = 0; i < current.length; i++) {
      if (current[i] !== draft[i]) return true
    }
    return false
  }, [selectedTeam, draftMembers])

  return (
    <Stack id="teams">
      <Title order={2}>Teams</Title>
      <Text>Manage teams and members. Changes require explicit save.</Text>
      <Grid gutter="md">
        <Grid.Col span={{ base: 12, md: 4 }}>
          <Card withBorder>
            <Group justify="space-between" mb="xs">
              <Text fw={600}>Teams</Text>
              <Button size="xs" onClick={openCreate}>
                New Team
              </Button>
            </Group>
            <Divider mb="xs" />
            <ScrollArea h={300}>
              <Stack gap={4}>
                {teams.data?.map((t) => (
                  <NavLink
                    key={t.team_id}
                    active={t.team_id === selectedTeam?.team_id}
                    label={
                      <Group gap={6} wrap="nowrap">
                        <Text truncate>{t.name_long}</Text>
                        <Badge size="xs" variant="light">
                          {t.members.length}
                        </Badge>
                      </Group>
                    }
                    rightSection={
                      (renameTeam.isPending || deleteTeam.isPending) &&
                      t.team_id === selectedTeam?.team_id ? (
                        <Loader size="xs" type="hex" />
                      ) : undefined
                    }
                    onClick={() => {
                      setSelectedTeamId(t.team_id)
                      setDraftMembers(t.members.map((m) => m.user_id))
                    }}
                  />
                ))}
              </Stack>
            </ScrollArea>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 8 }}>
          <Card withBorder>
            {selectedTeam ? (
              <Stack>
                <Group justify="space-between" align="flex-end">
                  <Group>
                    <Title order={3}>{selectedTeam.name_long}</Title>
                    <Badge>{selectedTeam.members.length} members</Badge>
                  </Group>
                  <Group>
                    <Button
                      size="xs"
                      variant="light"
                      onClick={() => {
                        setRenameValue(selectedTeam.name_long)
                        openRename()
                      }}
                    >
                      Rename
                    </Button>
                    <Tooltip withArrow label="Delete team">
                      <Button
                        size="xs"
                        color="red"
                        variant="outline"
                        onClick={() => {
                          setDeleteConfirm('')
                          openDelete()
                        }}
                      >
                        Delete
                      </Button>
                    </Tooltip>
                  </Group>
                </Group>
                <Divider />
                <Stack gap="xs">
                  <Text fw={600}>Members</Text>
                  <MultiSelect
                    searchable
                    clearable
                    placeholder="Select users"
                    data={(allUsers.data || []).map((u) => ({
                      value: u.user_id,
                      label: u.name_long,
                    }))}
                    value={draftMembers}
                    onChange={setDraftMembers}
                  />
                  <Group>
                    <Tooltip
                      withArrow
                      label={
                        hasMemberChanges
                          ? 'Save member changes'
                          : 'No changes to save'
                      }
                    >
                      <span>
                        <Button
                          size="sm"
                          onClick={handleSaveMembers}
                          loading={pendingSave}
                          disabled={!hasMemberChanges}
                        >
                          Save
                        </Button>
                      </span>
                    </Tooltip>
                    <Tooltip
                      withArrow
                      label={
                        hasMemberChanges
                          ? 'Discard unsaved changes'
                          : 'Nothing to reset'
                      }
                    >
                      <span>
                        <Button
                          size="sm"
                          variant="default"
                          onClick={resetDraft}
                          disabled={!selectedTeam || !hasMemberChanges}
                        >
                          Reset
                        </Button>
                      </span>
                    </Tooltip>
                  </Group>
                </Stack>
              </Stack>
            ) : (
              <Text c="dimmed">Start by creating a New Team.</Text>
            )}
          </Card>

          {/* Modals */}
          <Modal
            title="Create team"
            opened={createOpen}
            onClose={closeCreate}
            centered
          >
            <CreateTeamForm
              onCreate={async (name_long) => {
                setCreating(true)
                try {
                  const res = await createTeam.mutateAsync({ name_long })
                  const newId = (res as AxiosResponse<{ team_id: string }>)
                    ?.data?.team_id
                  await queryClient.refetchQueries({
                    queryKey: ['getTeamsWithMembers'],
                  })
                  if (newId) {
                    // Select new team explicitly; effect would also pick it if first in list
                    setSelectedTeamId(newId)
                    setDraftMembers([])
                  }
                } finally {
                  closeCreate()
                  // Defer resetting creating so spinner persists until after modal close
                  setTimeout(() => setCreating(false), 0)
                }
              }}
              isLoading={creating || createTeam.isPending}
            />
          </Modal>

          <Modal
            title="Rename team"
            opened={renameOpen}
            onClose={closeRename}
            centered
          >
            <Stack>
              <TextInput
                label="Team name"
                value={renameValue}
                onChange={(e) => setRenameValue(e.currentTarget.value)}
              />
              <Group justify="flex-end">
                <Button variant="default" onClick={closeRename}>
                  Cancel
                </Button>
                <Button
                  onClick={handleRename}
                  loading={renameTeam.isPending || renaming}
                >
                  Save
                </Button>
              </Group>
            </Stack>
          </Modal>

          <Modal
            title="Delete team"
            opened={deleteOpen}
            onClose={closeDelete}
            centered
          >
            <Stack>
              <Text c="red">
                This will remove all memberships and delete the team. This
                action cannot be undone. Type the team name to confirm.
              </Text>
              <TextInput
                placeholder={selectedTeam?.name_long}
                value={deleteConfirm}
                onChange={(e) => setDeleteConfirm(e.currentTarget.value)}
              />
              <Group justify="flex-end">
                <Button variant="default" onClick={closeDelete}>
                  Cancel
                </Button>
                <Button
                  color="red"
                  onClick={handleDelete}
                  disabled={deleteConfirm !== (selectedTeam?.name_long || '')}
                  loading={deleting || deleteTeam.isPending}
                >
                  Delete
                </Button>
              </Group>
            </Stack>
          </Modal>
        </Grid.Col>
      </Grid>
    </Stack>
  )
}

function CreateTeamForm({
  onCreate,
  isLoading,
}: {
  onCreate: (name_long: string) => Promise<unknown>
  isLoading: boolean
}) {
  const [value, setValue] = useLocalStorage<string>({
    key: 'proximal-create-team-name',
    defaultValue: '',
  })
  return (
    <TextInput
      label="Team Name"
      placeholder="e.g. O&M West"
      value={value}
      onChange={(e) => setValue(e.currentTarget.value)}
      rightSectionWidth={120}
      rightSection={
        <Button
          size="compact-sm"
          onClick={() => value && onCreate(value).then(() => setValue(''))}
          disabled={!value}
          loading={isLoading}
        >
          Create Team
        </Button>
      }
      style={{ maxWidth: 520 }}
    />
  )
}
