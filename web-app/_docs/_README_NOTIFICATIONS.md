# Adding a New Notification Type

This guide covers the critical changes needed to add a new notification type to the frontend.

## Prerequisites

Before adding frontend support, ensure:

1. The notification type exists in the database (`admin.notification_types` table)
2. The backend is creating notifications with the appropriate `notification_type_id` and `data` structure

## Critical Changes

### 1. Add Notification Formatter

**File:** `src/utils/notificationFormatters.ts`

Notification types are identified by their `name_long` value (matching the
`name_long` column in `admin.notification_types` table). The formatter looks up
by `name_long` from the notification data structure.

1. Add your formatter function:

```typescript
function formatNewNotificationType(
  data: NotificationData,
  createdAt: string | Date,
): FormattedNotification {
  // Extract data fields specific to your notification type
  const day = String(data.day || '')
  const formattedDate = formatAlertDate(day, createdAt)

  return {
    title: `New Type Risk - ${formattedDate}`,
    body: `${formattedDate} formatted message here.`,
    link: '/portfolio/map', // Optional: remove if no link needed
  }
}
```

2. Register it in the `formattersByName` map using the `name_long` value:

```typescript
const formattersByName: Record<
  string,
  (data: NotificationData, createdAt: string | Date) => FormattedNotification
> = {
  hail: formatHailAlert,
  fire: formatFireAlert,
  tornado: formatTornadoAlert,
  wind: formatWindAlert,
  new_type: formatNewNotificationType, // Add this line - use name_long from database
}
```

**Note:** The key in `formattersByName` must match the `name_long` value from
`admin.notification_types` table. The formatter uses `data.weather_type` (or
similar field) to extract the `name_long` value, so ensure your notification
data includes a field that contains the `name_long` value.

### 2. Add Icon to Notification Panel

**File:** `src/pages/layout/header/NotificationsPanel.tsx`

Import the icon:

```typescript
import {
  // ... existing imports
  IconNewType, // Add your icon from @tabler/icons-react
} from '@tabler/icons-react'
```

Add icon detection (using name_long from data structure):

```typescript
const getNotificationTypeName = () => {
  if (
    typeof notification.data === 'object' &&
    notification.data !== null &&
    'weather_type' in notification.data &&
    typeof notification.data.weather_type === 'string'
  ) {
    return notification.data.weather_type.toLowerCase()
  }
  return undefined
}

const typeName = getNotificationTypeName()
const isNewNotificationType = typeName === 'new_type' // Use name_long from database
```

Add to icon selection logic:

```typescript
const NotificationIcon = isFireAlert
  ? IconFlame
  : isHailAlert
    ? IconCloudRain
    : isTornadoAlert
      ? IconTornado
      : isWindAlert
        ? IconWind
        : isNewNotificationType
          ? IconNewType
          : IconBell
```

## Example: Weather risk pattern

The existing weather risk notifications (hail, fire, tornado, wind) use the `name_long`
pattern. Their data structure includes:

- `data.weather_type` contains the `name_long` value (e.g., "hail", "tornado",
  "wind", "fire") - this must match the `name_long` column in
  `admin.notification_types` table
- `data.day` contains the day offset (e.g., "day1", "day2")
- `data.value` contains the percentage risk (0-100) or other value
- `data.severity` contains the severity level

Your New notification may include any type of keys and values in the data structure.

See existing formatters (`formatHailAlert`, `formatTornadoAlert`,
`formatWindAlert`, `formatFireAlert`) for reference.

## Testing

After implementing:

1. Verify notifications display with the correct icon
2. Verify the title and body text format correctly
3. Verify any optional link navigation works
4. Test with different severity levels to ensure color coding works

## Notes

- **Use `name_long` values** to identify notification types - these must match
  the `name_long` column in the `admin.notification_types` database table
- The notification data must include a field (e.g., `weather_type`) that
  contains the `name_long` value
- The notification system uses a fallback pattern: if no formatter matches, it
  displays raw JSON
- Icons should be imported from `@tabler/icons-react`
- The `formatAlertDate()` helper function is available for date formatting
- Simply add your formatter function and register it in `formattersByName` with
  the `name_long` value as the key
