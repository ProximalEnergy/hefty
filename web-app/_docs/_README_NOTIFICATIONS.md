# Adding a New Notification Type

This guide covers the critical changes needed to add a new notification type to the frontend.

## Prerequisites

Before adding frontend support, ensure:

1. The notification type exists in the database (`admin.notification_types` table)
2. The backend is creating notifications with the appropriate `notification_type_id` and `data` structure
3. `NotificationType` / `NotificationTypeEnum` includes the new id (see `core` and `web-app/src/api/enumerations.ts`)

## Critical Changes

### 1. Add Notification Formatter

**File:** `src/utils/notificationFormatters.ts`

Formatters are keyed by **`notification_type_id`** (same integers as `NotificationTypeEnum`).

1. Add your formatter function (same signature as existing `formatHailAlert`, etc.).

2. Register it on the `formatters` map:

```typescript
const formatters: Partial<Record<number, NotificationFormatterFn>> = {
  // ...existing entries...
  [NotificationTypeEnum.NEW_TYPE]: formatNewNotificationType,
}
```

Unknown ids fall back to a generic title + JSON body.

### 2. Add Icon to Notification Panel

**File:** `src/pages/layout/header/NotificationsPanel.tsx`

1. Import an icon from `@tabler/icons-react`.
2. Compare `notification.notification_type_id` to `NotificationTypeEnum.*` (see existing hail / calendar / event chat branches).
3. If the type is weather-like and uses `data.day`, add its id to `WEATHER_NOTIFICATION_TYPE_IDS` when `isPastWeatherNotification` should apply.

## Example: Weather risk pattern

Weather notifications use ids `HAIL`, `FIRE`, `TORNADO`, `WIND`. Payload still includes `weather_type`, `day`, `value`, `severity` for display; routing uses **`notification_type_id`**, not `name_long` in the payload.

## Testing

After implementing:

1. Verify notifications display with the correct icon
2. Verify the title and body text format correctly
3. Verify any optional link navigation works
4. Test with different severity levels to ensure color coding works

## Notes

- Use **`NotificationTypeEnum`** for panel icons and the `formatters` map
- Icons: `@tabler/icons-react`
- `formatAlertDate()` is available for date formatting in weather-style formatters
