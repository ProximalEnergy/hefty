export const makePreviousDayCellClassNames =
  (previousDayClassName: string) => (arg: { date: Date }) => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)

    if (arg.date < today) {
      return [previousDayClassName]
    }
    return []
  }
