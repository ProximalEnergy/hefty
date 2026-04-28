import { Combobox, Group, InputBase, Tooltip, useCombobox } from '@mantine/core'
import { IconHelp } from '@tabler/icons-react'
import React, { ChangeEvent, useEffect, useRef, useState } from 'react'

export type DurationUnit = 'day' | 'week' | 'month' | 'quarter' | 'year'

export type Limits = {
  [key in DurationUnit]: number
}

interface DateComboboxProps {
  limits: Limits
  onOptionSubmit: (value: string) => void
  activate: boolean
}

const DateCombobox: React.FC<DateComboboxProps> = ({
  limits,
  onOptionSubmit,
  activate,
}) => {
  const [inputValue, setInputValue] = useState<string>('')
  const [options, setOptions] = useState<string[]>([])
  const inputRef = useRef<HTMLInputElement>(null)

  const combobox = useCombobox({
    onDropdownClose: () => combobox.resetSelectedOption(),
    opened: inputValue !== '',
  })

  // Handle input change
  const handleComboboxInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    let value = event.target.value

    // Strip all "0"s from the beginning of the string
    while (value.startsWith('0')) {
      value = value.slice(1)
    }

    setInputValue(value)
    setOptions(generateOptions(value))
    if (value === '') {
      combobox.closeDropdown()
    } else {
      combobox.openDropdown()
    }
  }

  const generateOptions = (value: string): string[] => {
    // Match a number followed by an optional unit
    // Returned array will have 3 elements:
    // - The full matched string
    // - The number
    // - The unit
    const match = value.match(/^(\d+)\s*([a-zA-Z]*)$/)

    // If there's no match, return an empty array
    if (!match) return []

    const number = parseInt(match[1], 10)
    const unit = match[2].toLowerCase()

    // Create an array of options based on the number and unit
    const options = Object.keys(limits)
      // Filter out units that exceed the limit
      .filter((key) => number <= limits[key as DurationUnit])
      // Map the units to strings, pluralizing if necessary
      .map((key) => `${number} ${key}${number > 1 ? 's' : ''}`)

    // If there's no unit, return all remaining options
    if (!unit) return options

    // Otherwise, return only the options that start with the unit
    return options.filter((option) =>
      option.replace(number.toString(), '').trim().startsWith(unit),
    )
  }

  // Focus the input when the Popover is opened
  useEffect(() => {
    if (activate && inputRef.current) {
      inputRef.current.focus()
    }
  }, [activate])

  // Select the first option when the input value changes
  useEffect(() => {
    combobox.selectFirstOption()
  }, [inputValue, combobox])

  return (
    <Group w="100%" gap="xs">
      <Combobox
        store={combobox}
        onOptionSubmit={(val: string) => {
          onOptionSubmit(val)
          setInputValue('')
        }}
      >
        <Combobox.Target>
          <InputBase
            ref={inputRef}
            value={inputValue}
            onChange={handleComboboxInputChange}
            placeholder="Search range..."
            flex={1}
          />
        </Combobox.Target>

        <Combobox.Dropdown>
          <Combobox.Options>
            {options.length === 0 ? (
              <Combobox.Empty>Nothing found</Combobox.Empty>
            ) : (
              options.map((option) => (
                <Combobox.Option value={option} key={option}>
                  {option}
                </Combobox.Option>
              ))
            )}
          </Combobox.Options>
        </Combobox.Dropdown>
      </Combobox>
      <Tooltip label="Type a number followed by a unit (e.g., 1 day, 2w, 3 months)">
        <IconHelp size={20} stroke={1.5} />
      </Tooltip>
    </Group>
  )
}

export default DateCombobox
