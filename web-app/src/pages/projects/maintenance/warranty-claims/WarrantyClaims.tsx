import { ProjectTypeEnum } from '@/api/enumerations'
import { useGetCompanies } from '@/api/v1/admin/companies'
import { useGetAllCompanyProjectsForProject } from '@/api/v1/admin/company_projects'
import { useGetUserSelf } from '@/api/v1/admin/users'
import {
  ClaimConfig,
  ClaimListItem,
  useDeleteClaim,
  useDeleteClaimConfig,
  useGetClaimConfigs,
  useGetProjectClaims,
} from '@/api/v1/operational/claims'
import { useSelectProject } from '@/api/v1/operational/projects'
import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import HistoricalClaimModal from '@/components/warranty-claims/HistoricalClaimModal'
import NewClaimModal from '@/components/warranty-claims/NewClaimModal'
import NewOemConfigModal from '@/components/warranty-claims/NewOemConfigModal'
import OemConfigModal from '@/components/warranty-claims/OemConfigModal'
import {
  STATUS_COLORS,
  claimStatusSortRank,
} from '@/components/warranty-claims/constants'
import { formatDate } from '@/components/warranty-claims/formatDate'
import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Modal,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Timeline,
  Title,
  Tooltip,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { notifications } from '@mantine/notifications'
import {
  IconArrowDown,
  IconArrowUp,
  IconArrowsSort,
  IconBuildingFactory2,
  IconClock,
  IconEdit,
  IconFileText,
  IconHistory,
  IconInfoCircle,
  IconMessage,
  IconPlus,
  IconSearch,
  IconSettings,
  IconTrash,
} from '@tabler/icons-react'
import {
  type SortingState,
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import {
  BESS_PLACEHOLDERS,
  PV_PLACEHOLDERS,
  getFakeUpdates,
} from './placeholders'

function isProximalCompanyName(value: string | null | undefined) {
  return value?.trim().toLowerCase().startsWith('proximal') ?? false
}

export default function WarrantyClaims() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [modalOpened, { open, close }] = useDisclosure(false)
  const [
    historicalModalOpened,
    { open: openHistorical, close: closeHistorical },
  ] = useDisclosure(false)
  const [editingDraftId, setEditingDraftId] = useState<number | null>(null)
  const [deletingClaimId, setDeletingClaimId] = useState<number | null>(null)
  const [previewClaim, setPreviewClaim] = useState<ClaimListItem | null>(null)
  const [
    newOemModalOpened,
    { open: openNewOemModal, close: closeNewOemModal },
  ] = useDisclosure(false)
  const [editingConfig, setEditingConfig] = useState<ClaimConfig | null>(null)
  const [deletingConfig, setDeletingConfig] = useState<ClaimConfig | null>(null)
  const deleteClaim = useDeleteClaim()
  const deleteClaimConfig = useDeleteClaimConfig()
  const project = useSelectProject(projectId)
  const projectTypeId = project.data?.project_type_id
  const { data: claimConfigs } = useGetClaimConfigs({
    pathParams: { projectId: projectId! },
    queryOptions: { enabled: !!projectId },
  })

  const [sorting, setSorting] = useState<SortingState>([])
  const [globalFilter, setGlobalFilter] = useState('')

  const { data, isLoading, isError } = useGetProjectClaims({
    pathParams: { projectId: projectId! },
    queryOptions: { enabled: !!projectId },
  })
  const userSelf = useGetUserSelf({
    queryOptions: { enabled: !!projectId },
  })
  const { data: projectCompanyProjects, isLoading: companyProjectsLoading } =
    useGetAllCompanyProjectsForProject({
      pathParams: { project_id: projectId! },
      queryOptions: { enabled: !!projectId },
    })

  const projectCompanyIds = useMemo(() => {
    const ids = (projectCompanyProjects ?? []).map((item) => item.company_id)
    return Array.from(new Set(ids))
  }, [projectCompanyProjects])

  const otherProjectCompanyIds = useMemo(() => {
    if (!userSelf.data?.company_id) return []
    return projectCompanyIds.filter(
      (companyId) => companyId !== userSelf.data.company_id,
    )
  }, [projectCompanyIds, userSelf.data?.company_id])

  const { data: projectCompanies, isLoading: companiesLoading } =
    useGetCompanies({
      queryParams: {
        company_ids:
          otherProjectCompanyIds.length > 0
            ? otherProjectCompanyIds
            : undefined,
      },
      queryOptions: { enabled: otherProjectCompanyIds.length > 0 },
    })

  const projectCompanyNames = useMemo(() => {
    const companiesById = new Map(
      (projectCompanies ?? []).map((company) => [company.company_id, company]),
    )
    return otherProjectCompanyIds
      .flatMap((companyId) => {
        const company = companiesById.get(companyId)
        const isProximal =
          isProximalCompanyName(company?.name_short) ||
          isProximalCompanyName(company?.name_long)
        if (isProximal) return []
        return [company?.name_long || company?.name_short || companyId]
      })
      .sort((a, b) => a.localeCompare(b))
  }, [projectCompanies, otherProjectCompanyIds])

  const claims = data && data.length > 0 ? data : null
  const placeholders =
    projectTypeId === ProjectTypeEnum.BESS
      ? BESS_PLACEHOLDERS
      : projectTypeId === ProjectTypeEnum.PV
        ? PV_PLACEHOLDERS
        : [...PV_PLACEHOLDERS.slice(0, 5), ...BESS_PLACEHOLDERS.slice(0, 5)]
  const displayClaims = claims ?? placeholders
  const isPlaceholder = !claims

  const oemStats = useMemo(() => {
    const counts = new Map<number, { total: number; open: number }>()
    for (const c of claims ?? []) {
      const cur = counts.get(c.claim_config_id) ?? { total: 0, open: 0 }
      cur.total += 1
      if (c.status !== 'closed' && c.status !== 'resolved') cur.open += 1
      counts.set(c.claim_config_id, cur)
    }
    return (claimConfigs ?? []).map((cfg) => ({
      config: cfg,
      claim_config_id: cfg.claim_config_id,
      name: cfg.counterparty_name || `Config #${cfg.claim_config_id}`,
      total: counts.get(cfg.claim_config_id)?.total ?? 0,
      open: counts.get(cfg.claim_config_id)?.open ?? 0,
    }))
  }, [claimConfigs, claims])

  const ownClaimConfigIds = useMemo(
    () => new Set((claimConfigs ?? []).map((cfg) => cfg.claim_config_id)),
    [claimConfigs],
  )

  const handleConfirmDeleteConfig = async () => {
    if (!deletingConfig) return
    try {
      await deleteClaimConfig.mutateAsync({
        projectId: projectId!,
        claimConfigId: deletingConfig.claim_config_id,
      })
      notifications.show({
        title: 'OEM removed',
        message: 'Claim config deleted',
        color: 'green',
      })
      setDeletingConfig(null)
    } catch (e: unknown) {
      const detail =
        (e as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? 'Failed to delete OEM config'
      notifications.show({
        title: 'Error',
        message: detail,
        color: 'red',
      })
    }
  }

  const columnHelper = createColumnHelper<ClaimListItem>()
  const columns = useMemo(
    () => [
      columnHelper.accessor('external_reference', {
        header: 'Ref',
        cell: ({ row }) => (
          <Text size="sm">
            {row.original.external_reference ?? `#${row.original.claim_id}`}
          </Text>
        ),
        size: 120,
      }),
      columnHelper.accessor('counterparty_name', {
        header: 'OEM',
        cell: ({ getValue }) => <Text size="sm">{getValue() ?? '—'}</Text>,
        size: 140,
      }),
      columnHelper.accessor('status', {
        header: 'Status',
        sortingFn: (rowA, rowB, columnId) => {
          const a = String(rowA.getValue(columnId))
          const b = String(rowB.getValue(columnId))
          return claimStatusSortRank(a) - claimStatusSortRank(b)
        },
        cell: ({ getValue }) => {
          const s = getValue()
          return (
            <Badge color={STATUS_COLORS[s] ?? 'gray'} variant="light" size="sm">
              {s.replace('_', ' ')}
            </Badge>
          )
        },
        size: 110,
      }),
      columnHelper.accessor('summary', {
        header: 'Summary',
        cell: ({ getValue }) => (
          <Text size="sm" lineClamp={1}>
            {getValue() ?? '—'}
          </Text>
        ),
        size: 300,
      }),
      columnHelper.accessor('device_count', {
        header: 'Devices',
        cell: ({ getValue }) => <Text size="sm">{getValue()}</Text>,
        size: 80,
        meta: { align: 'right' as const },
      }),
      columnHelper.accessor('created_at', {
        header: 'Created',
        cell: ({ getValue }) => <Text size="sm">{formatDate(getValue())}</Text>,
        size: 110,
        sortingFn: 'datetime',
      }),
      columnHelper.accessor('updated_at', {
        header: 'Updated',
        cell: ({ getValue }) => <Text size="sm">{formatDate(getValue())}</Text>,
        size: 110,
        sortingFn: 'datetime',
      }),
      columnHelper.display({
        id: 'actions',
        size: 40,
        cell: ({ row }) =>
          !isPlaceholder &&
          row.original.status === 'draft' &&
          ownClaimConfigIds.has(row.original.claim_config_id) ? (
            <ActionIcon
              color="red"
              variant="subtle"
              size="sm"
              onClick={(e) => {
                e.stopPropagation()
                setDeletingClaimId(row.original.claim_id)
              }}
            >
              <IconTrash size={14} />
            </ActionIcon>
          ) : null,
      }),
    ],
    [isPlaceholder, columnHelper, ownClaimConfigIds],
  )

  const table = useReactTable<ClaimListItem>({
    data: displayClaims,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    enableSorting: true,
    globalFilterFn: 'includesString',
  })

  if (isLoading) return <PageLoader />
  if (isError) return <PageError />

  const previewUpdates = previewClaim
    ? getFakeUpdates(previewClaim.claim_id)
    : []
  const previewTimelineActiveIndex = previewUpdates.length - 1

  return (
    <Stack p="md" gap="md">
      <Group justify="space-between">
        <Title order={3}>Warranty Claims</Title>
        <Group gap="xs">
          <Button
            variant="default"
            leftSection={<IconHistory size={16} />}
            onClick={openHistorical}
          >
            Add Historical Claim
          </Button>
          <Button
            leftSection={<IconPlus size={16} />}
            onClick={() => {
              setEditingDraftId(null)
              open()
            }}
          >
            Submit New Claim
          </Button>
        </Group>
      </Group>

      {isPlaceholder && (
        <Text size="sm" c="dimmed">
          No warranty claims yet. The rows below are examples. Click "Submit New
          Claim" to get started.
        </Text>
      )}

      <Alert
        icon={<IconInfoCircle size={16} />}
        color="blue"
        variant="light"
        w="50%"
      >
        <Text size="sm">
          Warranty claims are visible to any company with access to this
          project.
          {companyProjectsLoading || userSelf.isLoading || companiesLoading
            ? ' Loading companies...'
            : projectCompanyNames.length > 0
              ? ` Other companies with access: ${projectCompanyNames.join(
                  ', ',
                )}.`
              : ' No other companies are currently listed.'}
        </Text>
      </Alert>

      <Stack gap="xs">
        <Text size="sm" fw={500} c="dimmed">
          Configured OEMs
        </Text>
        <SimpleGrid cols={{ base: 2, xs: 3, sm: 4, md: 5, lg: 6 }}>
          {oemStats.map((o) => (
            <Card
              key={o.claim_config_id}
              withBorder
              p="sm"
              radius="md"
              style={{ cursor: 'pointer' }}
              onClick={() => setGlobalFilter(o.name)}
            >
              <Group justify="space-between" wrap="nowrap" gap="xs">
                <Group gap={6} wrap="nowrap" style={{ minWidth: 0 }}>
                  <IconBuildingFactory2
                    size={16}
                    stroke={1.5}
                    style={{ flexShrink: 0 }}
                  />
                  <Text size="sm" fw={500} lineClamp={1} title={o.name}>
                    {o.name}
                  </Text>
                </Group>
                <Group gap={2} wrap="nowrap">
                  <Tooltip label="Edit OEM" withArrow>
                    <ActionIcon
                      variant="subtle"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        setEditingConfig(o.config)
                      }}
                    >
                      <IconEdit size={14} />
                    </ActionIcon>
                  </Tooltip>
                  <Tooltip
                    label={
                      o.total > 0
                        ? 'Cannot delete: claims exist for this OEM'
                        : 'Delete OEM'
                    }
                    withArrow
                  >
                    <ActionIcon
                      variant="subtle"
                      color="red"
                      size="sm"
                      disabled={o.total > 0}
                      onClick={(e) => {
                        e.stopPropagation()
                        if (o.total > 0) return
                        setDeletingConfig(o.config)
                      }}
                    >
                      <IconTrash size={14} />
                    </ActionIcon>
                  </Tooltip>
                </Group>
              </Group>
              <Group gap={4} mt={6} align="baseline">
                <Text fz={22} fw={700} lh={1}>
                  {o.total}
                </Text>
                <Text size="xs" c="dimmed">
                  claim{o.total === 1 ? '' : 's'}
                </Text>
              </Group>
              <Text size="xs" c={o.open > 0 ? 'orange' : 'dimmed'} mt={2}>
                {o.open} open
              </Text>
            </Card>
          ))}
          <Card
            withBorder
            p="sm"
            radius="md"
            style={{
              cursor: 'pointer',
              borderStyle: 'dashed',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: 88,
            }}
            onClick={openNewOemModal}
          >
            <Stack gap={2} align="center">
              <IconPlus size={20} stroke={1.5} />
              <Text size="sm" fw={500}>
                Add OEM
              </Text>
              <Text size="xs" c="dimmed">
                Configure a counterparty
              </Text>
            </Stack>
          </Card>
        </SimpleGrid>
      </Stack>

      <TextInput
        placeholder="Search claims..."
        leftSection={<IconSearch size={16} />}
        value={globalFilter}
        onChange={(e) => setGlobalFilter(e.currentTarget.value)}
        style={{ maxWidth: 320 }}
      />

      <Table.ScrollContainer minWidth="100%">
        <Table
          style={{ width: '100%', tableLayout: 'fixed' }}
          highlightOnHover
          striped
          stickyHeader
        >
          <Table.Thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <Table.Tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const align = ((
                    header.column.columnDef.meta as
                      | { align?: 'left' | 'right' | 'center' }
                      | undefined
                  )?.align ?? 'left') as 'left' | 'right' | 'center'
                  return (
                    <Table.Th
                      key={header.id}
                      style={{
                        width: header.getSize(),
                        cursor: header.column.getCanSort()
                          ? 'pointer'
                          : 'default',
                        textAlign: align,
                        userSelect: 'none',
                      }}
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      <Group gap={4} wrap="nowrap" justify={align}>
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                        {header.column.getCanSort() &&
                          (header.column.getIsSorted() === 'asc' ? (
                            <IconArrowUp size={14} />
                          ) : header.column.getIsSorted() === 'desc' ? (
                            <IconArrowDown size={14} />
                          ) : (
                            <IconArrowsSort size={14} opacity={0.3} />
                          ))}
                      </Group>
                    </Table.Th>
                  )
                })}
              </Table.Tr>
            ))}
          </Table.Thead>
          <Table.Tbody>
            {table.getRowModel().rows.map((row) => (
              <Table.Tr
                key={row.id}
                style={{
                  cursor: 'pointer',
                  opacity: isPlaceholder ? 0.6 : 1,
                }}
                onClick={() => {
                  if (isPlaceholder) {
                    setPreviewClaim(row.original)
                    return
                  }
                  if (row.original.status === 'draft') {
                    setEditingDraftId(row.original.claim_id)
                    open()
                  } else {
                    navigate(
                      `/projects/${projectId}/maintenance/warranty-claims/${row.original.claim_id}`,
                    )
                  }
                }}
              >
                {row.getVisibleCells().map((cell) => {
                  const align = ((
                    cell.column.columnDef.meta as
                      | { align?: 'left' | 'right' | 'center' }
                      | undefined
                  )?.align ?? 'left') as 'left' | 'right' | 'center'
                  return (
                    <Table.Td
                      key={cell.id}
                      style={{ textAlign: align, overflow: 'hidden' }}
                    >
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </Table.Td>
                  )
                })}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>

      <NewClaimModal
        projectId={projectId!}
        opened={modalOpened}
        onClose={() => {
          setEditingDraftId(null)
          close()
        }}
        draftClaimId={editingDraftId}
      />

      <NewOemConfigModal
        projectId={projectId!}
        opened={newOemModalOpened}
        onClose={closeNewOemModal}
      />

      <HistoricalClaimModal
        projectId={projectId!}
        opened={historicalModalOpened}
        onClose={closeHistorical}
      />

      {editingConfig && (
        <OemConfigModal
          mode="edit"
          projectId={projectId!}
          opened={!!editingConfig}
          onClose={() => setEditingConfig(null)}
          existing={editingConfig}
        />
      )}

      <Modal
        opened={!!deletingConfig}
        onClose={() => setDeletingConfig(null)}
        title="Delete OEM Configuration"
        size="sm"
      >
        {deletingConfig && (
          <Stack gap="md">
            <Text size="sm">
              Delete{' '}
              <Text component="span" fw={500}>
                {deletingConfig.counterparty_name ||
                  `Config #${deletingConfig.claim_config_id}`}
              </Text>
              ? This cannot be undone.
            </Text>
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setDeletingConfig(null)}>
                Cancel
              </Button>
              <Button
                color="red"
                onClick={handleConfirmDeleteConfig}
                loading={deleteClaimConfig.isPending}
              >
                Delete
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>

      <Modal
        opened={!!deletingClaimId}
        onClose={() => setDeletingClaimId(null)}
        title="Delete Draft Claim"
        size="sm"
      >
        <Stack gap="md">
          <Text size="sm">
            Are you sure you want to delete this draft claim? This action cannot
            be undone.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDeletingClaimId(null)}>
              Cancel
            </Button>
            <Button
              color="red"
              loading={deleteClaim.isPending}
              onClick={async () => {
                if (!deletingClaimId) return
                try {
                  await deleteClaim.mutateAsync({
                    projectId: projectId!,
                    claimId: deletingClaimId,
                  })
                  notifications.show({
                    title: 'Deleted',
                    message: 'Draft claim deleted',
                    color: 'green',
                  })
                } catch {
                  notifications.show({
                    title: 'Error',
                    message: 'Failed to delete claim',
                    color: 'red',
                  })
                }
                setDeletingClaimId(null)
              }}
            >
              Delete
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={!!previewClaim}
        onClose={() => setPreviewClaim(null)}
        title={
          previewClaim ? `Example: ${previewClaim.summary}` : 'Claim Preview'
        }
        size="lg"
      >
        {previewClaim && (
          <Stack gap="md">
            <Text size="xs" c="dimmed">
              This is example data to illustrate how warranty claims look on the
              platform.
            </Text>

            <Table withTableBorder>
              <Table.Tbody>
                <Table.Tr>
                  <Table.Td fw={500} w={130}>
                    OEM
                  </Table.Td>
                  <Table.Td>{previewClaim.counterparty_name}</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td fw={500}>Status</Table.Td>
                  <Table.Td>
                    <Badge
                      color={STATUS_COLORS[previewClaim.status] ?? 'gray'}
                      variant="light"
                      size="sm"
                    >
                      {previewClaim.status.replace('_', ' ')}
                    </Badge>
                  </Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td fw={500}>Reference</Table.Td>
                  <Table.Td>{previewClaim.external_reference ?? '—'}</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td fw={500}>Devices</Table.Td>
                  <Table.Td>{previewClaim.device_count}</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td fw={500}>Created</Table.Td>
                  <Table.Td>{formatDate(previewClaim.created_at)}</Table.Td>
                </Table.Tr>
              </Table.Tbody>
            </Table>

            <Title order={6}>Timeline</Title>
            <Timeline
              active={previewTimelineActiveIndex}
              bulletSize={22}
              lineWidth={2}
            >
              {previewUpdates.map((u, i) => {
                const icon =
                  u.type === 'status_change' ? (
                    <IconSettings size={12} />
                  ) : u.type === 'submission' ? (
                    <IconFileText size={12} />
                  ) : u.type === 'field_visit' ? (
                    <IconClock size={12} />
                  ) : (
                    <IconMessage size={12} />
                  )
                return (
                  <Timeline.Item
                    key={i}
                    bullet={icon}
                    title={
                      <Group gap="xs">
                        <Text size="sm" fw={500}>
                          {u.type.replace('_', ' ')}
                        </Text>
                        {u.status && (
                          <Badge
                            size="xs"
                            color={STATUS_COLORS[u.status] ?? 'gray'}
                            variant="light"
                          >
                            {u.status.replace('_', ' ')}
                          </Badge>
                        )}
                      </Group>
                    }
                  >
                    <Text size="sm">{u.message}</Text>
                    <Text size="xs" c="dimmed">
                      {u.user} · {formatDate(u.date)}
                    </Text>
                  </Timeline.Item>
                )
              })}
            </Timeline>
          </Stack>
        )}
      </Modal>
    </Stack>
  )
}
