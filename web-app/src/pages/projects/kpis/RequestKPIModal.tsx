import { useGetProjectContracts } from '@/api/v1/operational/project/contracts'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useCreateFeedbackMutation } from '@/hooks/api'
import { useAuth } from '@clerk/clerk-react'
import {
  Button,
  Modal,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
} from '@mantine/core'
import { useState } from 'react'
import { useParams } from 'react-router'

import CreateContractModal from '../contracts/CreateContractModal'

interface RequestKPIModalProps {
  opened: boolean
  onClose: () => void
}

const RequestKPIModal = ({ opened, onClose }: RequestKPIModalProps) => {
  const { projectId } = useParams<{ projectId: string }>()
  const [kpiName, setKpiName] = useState('')
  const [selectedContract, setSelectedContract] = useState<string | null>(null)
  const [description, setDescription] = useState('')
  const [contractModalOpen, setContractModalOpen] = useState(false)
  const mutation = useCreateFeedbackMutation()
  const { userId } = useAuth()

  const {
    data: contracts,
    isLoading,
    refetch,
  } = useGetProjectContracts({
    pathParams: { projectId: projectId || '-1' },
  })

  const { data: project } = useSelectProject(projectId!)

  if (!projectId) return null

  const contractOptions = [
    { value: 'new', label: 'Add New...' },
    ...(contracts?.map((contract) => ({
      value: contract.contract_id.toString(),
      label: contract.name_long,
    })) || []),
  ]

  const handleContractChange = (value: string | null) => {
    if (value === 'new') {
      setContractModalOpen(true)
    } else {
      setSelectedContract(value)
    }
  }

  const handleContractModalClose = () => {
    setContractModalOpen(false)
    // Refresh the contracts list after a new contract is created
    refetch()
  }

  const handleSubmit = async () => {
    if (!kpiName || !selectedContract || !description) {
      // Show error message
      return
    }

    const contract = contracts?.find(
      (c) => c.contract_id.toString() === selectedContract,
    )

    const formData = new FormData()
    formData.append('user_id', userId || '')
    formData.append('subject', `KPI Request: ${kpiName}`)
    formData.append('url', window.location.href)
    formData.append(
      'comment',
      `New KPI Request:
Project: ${project?.name_long}
Contract: ${contract?.name_long}
KPI Name: ${kpiName}
Description: ${description}
Project ID: ${projectId}
Contract ID: ${selectedContract}`,
    )

    mutation.mutate(formData, {
      onSuccess: () => {
        setKpiName('')
        setSelectedContract(null)
        setDescription('')
        onClose()
      },
    })
  }

  return (
    <>
      <Modal
        opened={opened}
        onClose={onClose}
        title="Request New KPI"
        size="md"
      >
        <Stack>
          <Text size="sm" c="dimmed" style={{ lineHeight: 1.4 }}>
            Fill in this form to request the tracking of a new Contractual KPI
            that is tied to a specific contract and this project (
            {project?.name_long || ''}). The Proximal team will get back to you
            ASAP with an example implementation or follow up questions.
          </Text>

          <Select
            label="Contract"
            placeholder="Select contract..."
            data={contractOptions}
            value={selectedContract}
            onChange={handleContractChange}
            disabled={isLoading}
            required
          />

          <TextInput
            label="KPI Name"
            value={kpiName}
            onChange={(event) => setKpiName(event.currentTarget.value)}
            placeholder="Enter KPI name..."
            required
          />

          <Textarea
            label="Description"
            value={description}
            onChange={(event) => setDescription(event.currentTarget.value)}
            placeholder="Describe the KPI you'd like to request..."
            minRows={3}
            required
          />
          <Button onClick={handleSubmit}>Submit Request</Button>
        </Stack>
      </Modal>

      <CreateContractModal
        opened={contractModalOpen}
        onClose={handleContractModalClose}
      />
    </>
  )
}

export default RequestKPIModal
