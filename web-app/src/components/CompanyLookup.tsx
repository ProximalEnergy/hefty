import { HexLoader } from '@/HexLoader'
import { useCreateCompany, useGetCompanies } from '@/api/v1/admin/companies'
import {
  Button,
  Radio,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { useMemo, useState } from 'react'

interface CompanyLookupProps {
  label?: string
  placeholder?: string
  minQueryLength?: number
  selectedCompanyId?: string | null
  onSelect: (companyId: string) => void
  autoFocus?: boolean
}

export default function CompanyLookup({
  label = 'Company',
  placeholder = 'Type at least 3 letters to search companies',
  minQueryLength = 3,
  selectedCompanyId,
  onSelect,
  autoFocus = false,
}: CompanyLookupProps) {
  const [companyQuery, setCompanyQuery] = useState('')
  const companies = useGetCompanies({
    queryOptions: { enabled: companyQuery.length >= minQueryLength },
  })
  const createCompany = useCreateCompany()

  const [localOptions, setLocalOptions] = useState<
    { value: string; label: string }[]
  >([])

  const companyOptions = useMemo(() => {
    const q = companyQuery.trim().toLowerCase()
    if (q.length < minQueryLength) return []
    const all = (companies.data || []).map((c) => ({
      id: c.company_id,
      nameLong: c.name_long || '',
      nameShort: c.name_short || '',
    }))

    // Basic Levenshtein distance
    const levenshtein = (a: string, b: string) => {
      const lowerA = a.toLowerCase()
      const lowerB = b.toLowerCase()
      const m = lowerA.length
      const n = lowerB.length
      if (m === 0) return n
      if (n === 0) return m
      const dp = Array.from({ length: m + 1 }, () =>
        Array.from({ length: n + 1 }, () => 0),
      )
      for (let i = 0; i <= m; i++) dp[i][0] = i
      for (let j = 0; j <= n; j++) dp[0][j] = j
      for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
          const cost = lowerA[i - 1] === lowerB[j - 1] ? 0 : 1
          dp[i][j] = Math.min(
            dp[i - 1][j] + 1,
            dp[i][j - 1] + 1,
            dp[i - 1][j - 1] + cost,
          )
        }
      }
      return dp[m][n]
    }

    const computeAcronym = (name: string) =>
      name
        .replace(/&/g, ' and ')
        .split(/[^a-zA-Z0-9]+/)
        .filter(Boolean)
        .map((w) => w[0]?.toUpperCase() || '')
        .join('')

    const normalize = (s: string) =>
      s
        .toLowerCase()
        .replace(/&/g, ' and ')
        .replace(/[^a-z0-9]+/g, ' ')
        .trim()
        .replace(/\s+/g, ' ')

    const toTokens = (s: string) => normalize(s).split(' ').filter(Boolean)
    const collapse = (s: string) => normalize(s).replace(/\s+/g, '')

    const qTokens = toTokens(companyQuery)
    const qCollapsed = collapse(companyQuery)

    const ranked = all
      .map((c) => {
        const nameLongNorm = normalize(c.nameLong)
        const nameShortNorm = normalize(c.nameShort)
        const nameTokens = toTokens(c.nameLong)
        const nameCollapsed = collapse(c.nameLong)

        const qUpper = q.toUpperCase()
        const acronym = computeAcronym(c.nameLong)

        // Base distance components (whole string)
        const distLong = q ? levenshtein(q, nameLongNorm) : 0
        const distShort = q ? levenshtein(q, nameShortNorm) : 0
        let score = Math.min(distLong, distShort)

        // Token-wise scoring: find best match per query token among name tokens
        for (const qt of qTokens) {
          let best = Number.POSITIVE_INFINITY
          let bestLen = 0
          for (const nt of nameTokens) {
            let d = levenshtein(qt, nt)
            if (nt.startsWith(qt)) d -= 4
            else if (nt.includes(qt)) d -= 2
            const candidate = d
            if (candidate < best) {
              best = candidate
              bestLen = Math.max(qt.length, nt.length)
            }
          }
          // Collapsed containment bonus (e.g., deshaw -> de shaw)
          if (nameCollapsed.includes(collapse(qt))) best -= 4
          if (isFinite(best)) {
            score += best
            // Penalize heavily if more than 33% letters differ for best token match
            const diffRatio = bestLen > 0 ? Math.max(0, best) / bestLen : 0
            if (diffRatio > 0.33) score += 12
          }
        }

        // Strong signals
        if (nameShortNorm === q) score -= 100 // exact short-name
        if (acronym === qUpper) score -= 90 // acronym equals query
        if (nameLongNorm.startsWith(q)) score -= 20 // starts-with long name
        if (nameLongNorm.includes(q)) score -= 5 // substring in long name
        if (nameCollapsed.includes(qCollapsed)) score -= 8 // collapsed substring

        // Short query guardrails
        const hasStrong = nameShortNorm === q || acronym === qUpper
        if (q.length <= 3 && !hasStrong && !nameLongNorm.includes(q)) {
          score += 5
        }

        return { id: c.id, label: c.nameLong, score }
      })
      .sort((a, b) => a.score - b.score)

    // Merge with locally created options and de-dupe
    const rankedOptions = ranked
      .slice(0, 1)
      .map((r) => ({ value: r.id, label: r.label }))
    const mergedMap = new Map<string, { value: string; label: string }>()
    for (const opt of [...localOptions, ...rankedOptions]) {
      if (!mergedMap.has(opt.value)) mergedMap.set(opt.value, opt)
    }
    return Array.from(mergedMap.values())
  }, [companies.data, localOptions, companyQuery, minQueryLength])

  const hasExactMatch = useMemo(() => {
    const q = companyQuery.trim().toLowerCase()
    if (!q) return false
    return companyOptions.some((opt) => opt.label.trim().toLowerCase() === q)
  }, [companyOptions, companyQuery])

  const handleCompanyLookupCreate = async () => {
    const nameLong = companyQuery.trim()
    if (!nameLong) return
    const nameShort = nameLong
      .toLowerCase()
      .replace(/\s+/g, '_')
      .replace(/[^a-z0-9_]/g, '')
    const res = await createCompany.mutateAsync({
      name_short: nameShort,
      name_long: nameLong,
    })
    const newId = res.data.company_id
    if (newId) {
      const newOpt = { value: newId, label: nameLong }
      setLocalOptions((prev) => [newOpt, ...prev])
      onSelect(newId)
      // Keep the query so the newly created option remains visible and selected
      setCompanyQuery(nameLong)
    }
  }

  return (
    <Stack gap="xs">
      <Title order={6}>{label}</Title>
      <TextInput
        placeholder={placeholder}
        value={companyQuery}
        onChange={(e) => setCompanyQuery(e.currentTarget.value)}
        autoFocus={autoFocus}
      />
      <Table withRowBorders={false} highlightOnHover>
        <Table.Tbody>
          {companyOptions.map((opt) => (
            <Table.Tr
              key={opt.value}
              style={{ cursor: 'pointer' }}
              onClick={() => onSelect(opt.value)}
              data-selected={selectedCompanyId === opt.value}
            >
              <Table.Td width={36}>
                <Radio
                  checked={selectedCompanyId === opt.value}
                  onChange={() => onSelect(opt.value)}
                  aria-label={`Select ${opt.label}`}
                />
              </Table.Td>
              <Table.Td>
                <Text size="sm">{opt.label}</Text>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
      {companyQuery.length >= minQueryLength && companies.isLoading && (
        <HexLoader />
      )}
      {companyQuery.length >= minQueryLength &&
        !companies.isLoading &&
        !hasExactMatch && (
          <Button
            variant="light"
            onClick={handleCompanyLookupCreate}
            loading={createCompany.isPending}
          >
            Create company “{companyQuery.trim()}”
          </Button>
        )}
    </Stack>
  )
}
