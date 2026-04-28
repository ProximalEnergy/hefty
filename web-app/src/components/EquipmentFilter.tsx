import { LoadingOverlay, Select, Stack } from '@mantine/core'
import { UseQueryOptions, UseQueryResult } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { useEffect, useState } from 'react'

// Props interface
interface EquipmentFilterProps {
  // Hook to fetch manufacturers
  useGetManufacturers: ({
    queryParams,
    queryOptions,
  }: {
    queryParams?: object
    queryOptions?: Partial<UseQueryOptions>
  }) => UseQueryResult<string[], AxiosError>

  // Hook to fetch models based on manufacturer
  useGetModels: ({
    queryParams,
    queryOptions,
  }: {
    queryParams?: { manufacturer?: string | null } // Manufacturer is optional for query params
    queryOptions?: Partial<UseQueryOptions>
  }) => UseQueryResult<string[], AxiosError>

  // Callback when manufacturer selection changes
  onManufacturerChange?: (value: string | null) => void
  // Callback when model selection changes
  onModelChange?: (value: string | null) => void
  // Initial value for manufacturer (controlled by parent)
  initialManufacturer?: string | null
  // Initial value for model (controlled by parent)
  initialModel?: string | null
  // Company ID to filter equipment by
  company_id?: string | number | null
  // Additional query parameters to pass to both hooks
  additionalQueryParams?: object
}

const EquipmentFilter = ({
  useGetManufacturers,
  useGetModels,
  onManufacturerChange,
  onModelChange,
  initialManufacturer = null,
  initialModel = null,
  company_id = null,
  additionalQueryParams = {},
}: EquipmentFilterProps) => {
  // Internal state to manage selections within this component
  // Initialize with props to reflect parent state
  const [selectedManufacturer, setSelectedManufacturer] = useState<
    string | null
  >(initialManufacturer)
  const [selectedModel, setSelectedModel] = useState<string | null>(
    initialModel,
  )

  // --- Fetch Manufacturers ---
  const { data: manufacturers = [], isLoading: isLoadingManufacturers } =
    useGetManufacturers({
      queryParams: {
        ...(company_id ? { company_id } : {}),
        ...additionalQueryParams,
      },
      queryOptions: {
        enabled: !!company_id,
      },
    })

  // --- Fetch Models ---
  const { data: models = [], isLoading: isLoadingModels } = useGetModels({
    queryParams: {
      manufacturer: selectedManufacturer,
      ...(company_id ? { company_id } : {}),
      ...additionalQueryParams,
    },
    queryOptions: { enabled: !!selectedManufacturer && !!company_id },
  })

  // --- Effect to sync internal state with props ---
  useEffect(() => {
    setSelectedManufacturer(initialManufacturer)
  }, [initialManufacturer])

  useEffect(() => {
    setSelectedModel(initialModel)
  }, [initialModel])

  // --- Effect to reset model when manufacturer changes ---
  useEffect(() => {
    if (selectedManufacturer !== initialManufacturer && !initialModel) {
      setSelectedModel(null)
      if (onModelChange) {
        onModelChange(null)
      }
    }
  }, [selectedManufacturer, initialManufacturer, initialModel, onModelChange])

  // --- Handler for Manufacturer Select ---
  const handleEquipmentManufacturerChange = (value: string | null) => {
    setSelectedModel(null)
    setSelectedManufacturer(value)

    if (onManufacturerChange) {
      onManufacturerChange(value)
    }
  }

  // --- Handler for Model Select ---
  const handleEquipmentModelChange = (value: string | null) => {
    setSelectedModel(value)
    if (onModelChange) {
      onModelChange(value)
    }
  }

  // Format data for Mantine Select component
  const manufacturerOptions = manufacturers.map((m) => ({ value: m, label: m }))
  const modelOptions = models.map((m) => ({ value: m, label: m }))

  return (
    <Stack>
      <div style={{ position: 'relative' }}>
        <LoadingOverlay visible={isLoadingManufacturers} />
        <Select
          label="Manufacturer"
          placeholder="Select manufacturer"
          data={manufacturerOptions}
          value={selectedManufacturer}
          onChange={handleEquipmentManufacturerChange}
          clearable
          searchable={true}
          required={true}
          disabled={isLoadingManufacturers}
          nothingFoundMessage={
            isLoadingManufacturers ? 'Loading...' : 'No manufacturers found'
          }
        />
      </div>
      <div style={{ position: 'relative' }}>
        <LoadingOverlay visible={isLoadingModels} />
        <Select
          label="Model"
          placeholder={
            selectedManufacturer ? 'Select model' : 'Select manufacturer first'
          }
          data={modelOptions}
          value={selectedModel}
          onChange={handleEquipmentModelChange}
          clearable
          searchable={true}
          required={true}
          disabled={isLoadingModels || !selectedManufacturer}
          nothingFoundMessage={
            isLoadingModels ? 'Loading...' : 'No models found'
          }
        />
      </div>
    </Stack>
  )
}

export default EquipmentFilter
