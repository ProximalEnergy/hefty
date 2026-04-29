import { formatCurrency } from '@/utils/currency'
import {
  Alert,
  Card,
  Grid,
  Group,
  Stack,
  Table,
  Text,
  Title,
  useMantineColorScheme,
} from '@mantine/core'
import {
  IconAlertCircle,
  IconClock,
  IconExclamationMark,
  IconPackage,
  IconTrendingUp,
} from '@tabler/icons-react'

interface SparePartData {
  name: string
  oem: string
  model: string
  onSite: number
  vmi: number
  purchasePrice: number
  carryingCosts: number
  stockoutCosts: number
  leadTime: string
}

const sparePartsData: SparePartData[] = [
  {
    name: 'String Inverter',
    oem: 'SunGrow',
    model: 'PX50',
    onSite: 5,
    vmi: 0,
    purchasePrice: 50000,
    carryingCosts: 2500,
    stockoutCosts: 100000,
    leadTime: '30 days',
  },
  {
    name: 'Tracker Motor',
    oem: 'Tracker',
    model: 'QX01',
    onSite: 15,
    vmi: 0,
    purchasePrice: 15000,
    carryingCosts: 750,
    stockoutCosts: 30000,
    leadTime: '30 days',
  },
  {
    name: 'String Inverter',
    oem: 'SunGrow',
    model: 'PX50',
    onSite: 42,
    vmi: 10,
    purchasePrice: 8000,
    carryingCosts: 400,
    stockoutCosts: 16000,
    leadTime: '45 days',
  },
  {
    name: 'String Inverter',
    oem: 'SunGrow',
    model: 'QX01',
    onSite: 45,
    vmi: 0,
    purchasePrice: 12000,
    carryingCosts: 600,
    stockoutCosts: 24000,
    leadTime: '20 days',
  },
  {
    name: 'Central Inverter',
    oem: 'SMA',
    model: 'SC900CP',
    onSite: 30,
    vmi: 20,
    purchasePrice: 25000,
    carryingCosts: 1250,
    stockoutCosts: 50000,
    leadTime: '20 days',
  },
  {
    name: 'Combined Power',
    oem: 'Combined Power',
    model: 'WaveInque',
    onSite: 25,
    vmi: 5,
    purchasePrice: 18000,
    carryingCosts: 900,
    stockoutCosts: 36000,
    leadTime: '50 days',
  },
  {
    name: 'Battery Module',
    oem: 'Tesla',
    model: 'Megapack',
    onSite: 24,
    vmi: 0,
    purchasePrice: 180000,
    carryingCosts: 9000,
    stockoutCosts: 360000,
    leadTime: '30 days',
  },
  {
    name: 'Transformer',
    oem: 'Transformer',
    model: '15kV',
    onSite: 6,
    vmi: 3,
    purchasePrice: 35000,
    carryingCosts: 1750,
    stockoutCosts: 70000,
    leadTime: '60 days',
  },
  {
    name: 'Charge Controller',
    oem: 'Schneider',
    model: 'C35',
    onSite: 50,
    vmi: 15,
    purchasePrice: 5000,
    carryingCosts: 250,
    stockoutCosts: 10000,
    leadTime: '30 days',
  },
  {
    name: 'Panel',
    oem: 'Panel',
    model: 'Super 6',
    onSite: 2200,
    vmi: 100,
    purchasePrice: 350,
    carryingCosts: 17.5,
    stockoutCosts: 700,
    leadTime: '15 days',
  },
  {
    name: 'Battery Inverter',
    oem: 'Delta',
    model: 'Flex E3',
    onSite: 25,
    vmi: 2,
    purchasePrice: 15000,
    carryingCosts: 750,
    stockoutCosts: 30000,
    leadTime: '20 days',
  },
  {
    name: 'PV Module',
    oem: 'PV Module',
    model: 'NexOn 2',
    onSite: 700,
    vmi: 25,
    purchasePrice: 250,
    carryingCosts: 12.5,
    stockoutCosts: 500,
    leadTime: '15 days',
  },
]

const formatNumber = (value: number): string => value.toLocaleString()

const SparePartsPage = () => {
  const { colorScheme } = useMantineColorScheme()

  // Calculate summary metrics
  const criticalParts = sparePartsData.filter((part) => part.onSite < 10).length
  const totalInventoryValue = sparePartsData.reduce(
    (sum, part) => sum + part.purchasePrice * part.onSite,
    0,
  )
  const avgLeadTime = Math.round(
    sparePartsData.reduce((sum, part) => {
      const days = parseInt(part.leadTime.split(' ')[0]) || 0
      return sum + days
    }, 0) / sparePartsData.length,
  )
  const inventoryBuffer =
    Math.round(
      (sparePartsData.reduce((sum, part) => sum + part.vmi, 0) /
        sparePartsData.reduce((sum, part) => sum + part.onSite, 0)) *
        100,
    ) || 0

  const columns = [
    { key: 'name', header: 'Spare part name' },
    { key: 'oem', header: 'OEM' },
    { key: 'model', header: 'Model' },
    { key: 'onSite', header: 'Number of Spares on Site' },
    {
      key: 'vmi',
      header: 'Number of Spares managed by Vendor Managed Inventory',
    },
    { key: 'purchasePrice', header: 'Purchase Price' },
    { key: 'carryingCosts', header: 'Carrying Costs' },
    { key: 'stockoutCosts', header: 'Cost of Stockouts' },
    { key: 'leadTime', header: 'Key Spare Lead Time Summary' },
  ]

  const renderCell = (part: SparePartData, key: string): string => {
    switch (key) {
      case 'onSite':
      case 'vmi':
        return formatNumber(part[key as keyof SparePartData] as number)
      case 'purchasePrice':
      case 'carryingCosts':
      case 'stockoutCosts':
        return formatCurrency(part[key as keyof SparePartData] as number)
      default:
        return String(part[key as keyof SparePartData])
    }
  }

  return (
    <Stack p="md" h="100%">
      <Title order={2}>Spare Parts Monitoring</Title>

      <Alert
        icon={<IconAlertCircle size={16} />}
        title="Placeholder Data"
        color="yellow"
      >
        This is placeholder data. If you would like to work with Proximal on
        integrating spare parts management, please use the feedback button at
        the bottom of the sidebar.
      </Alert>

      {/* Summary Cards */}
      <Grid>
        <Grid.Col span={3}>
          <Card withBorder p="md" bg="rgba(255, 0, 0, 0.1)">
            <Group justify="space-between">
              <div>
                <Text size="xl" fw={700} c="red">
                  {criticalParts}
                </Text>
                <Text size="sm" c="dimmed">
                  Parts Critical
                </Text>
              </div>
              <IconExclamationMark size={24} color="red" />
            </Group>
          </Card>
        </Grid.Col>

        <Grid.Col span={3}>
          <Card withBorder p="md">
            <Group justify="space-between">
              <div>
                <Text size="xl" fw={700}>
                  ${(totalInventoryValue / 1000000).toFixed(1)}M
                </Text>
                <Text size="sm" c="dimmed">
                  Total Inventory
                </Text>
              </div>
              <IconPackage size={24} />
            </Group>
          </Card>
        </Grid.Col>

        <Grid.Col span={3}>
          <Card withBorder p="md">
            <Group justify="space-between">
              <div>
                <Text size="xl" fw={700}>
                  {avgLeadTime}days
                </Text>
                <Text size="sm" c="dimmed">
                  Lead Time Avg
                </Text>
              </div>
              <IconClock size={24} />
            </Group>
          </Card>
        </Grid.Col>

        <Grid.Col span={3}>
          <Card withBorder p="md">
            <Group justify="space-between">
              <div>
                <Text size="xl" fw={700}>
                  {inventoryBuffer}mos
                </Text>
                <Text size="sm" c="dimmed">
                  Inventory Buffer Avg
                </Text>
              </div>
              <IconTrendingUp size={24} />
            </Group>
          </Card>
        </Grid.Col>
      </Grid>

      <Card withBorder>
        <Table
          withTableBorder
          withColumnBorders
          striped={colorScheme === 'light'}
          highlightOnHover
          style={{
            borderRadius: 'var(--mantine-radius-md)',
            overflow: 'hidden',
          }}
        >
          <Table.Thead>
            <Table.Tr>
              {columns.map((col) => (
                <Table.Th
                  key={col.key}
                  style={{
                    fontWeight: 600,
                    padding: '8px 12px',
                  }}
                >
                  {col.header}
                </Table.Th>
              ))}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {sparePartsData.map((part, index) => (
              <Table.Tr key={index}>
                {columns.map((col) => (
                  <Table.Td
                    key={col.key}
                    style={{
                      padding: '8px 12px',
                    }}
                  >
                    {renderCell(part, col.key)}
                  </Table.Td>
                ))}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>
    </Stack>
  )
}

export default SparePartsPage
