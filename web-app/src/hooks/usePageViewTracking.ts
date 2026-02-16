import { useGetUserSelf } from '@/api/v1/admin/users'
import { useUser } from '@clerk/clerk-react'
import { usePostHog } from '@posthog/react'
import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router'

// Normalize dynamic URL segments so analytics can be grouped by route shape
// rather than split by every concrete resource ID.
function normalizePath(pathname: string): string {
  // /projects/<uuid>/settings -> /projects/:projectId/settings
  if (/^\/projects\/[^/]+(?:\/.*)?$/.test(pathname)) {
    return pathname.replace(/^\/projects\/[^/]+/, '/projects/:projectId')
  }

  return pathname
}

// Module-level guard to reduce duplicate captures triggered by StrictMode
// remount behavior in development.
let lastTrackedRouteKey: string | null = null
let lastTrackedUserId: string | null = null

export const usePageViewTracking = () => {
  const posthog = usePostHog()
  const location = useLocation()
  const { isLoaded, isSignedIn } = useUser()
  const {
    data: userSelf,
    isLoading,
    isError,
  } = useGetUserSelf({
    queryOptions: {
      enabled: isLoaded && isSignedIn,
    },
  })
  const previousRouteKey = useRef<string | null>(null)
  const identifiedUserId = useRef<string | null>(null)

  // Identify the current user once so pageview events are tied to a stable
  // person profile and company group in PostHog.
  useEffect(() => {
    if (!posthog || isLoading || isError || !userSelf) {
      return
    }

    const userId = String(userSelf.user_id)

    if (identifiedUserId.current === userId) {
      return
    }

    posthog.identify(userId, {
      user_id: userSelf.user_id,
      company_id: userSelf.company_id,
      user_type_id: userSelf.user_type_id,
    })

    posthog.group('company', String(userSelf.company_id), {
      company_id: userSelf.company_id,
    })

    if (lastTrackedUserId !== userId) {
      lastTrackedUserId = userId
      lastTrackedRouteKey = null
      previousRouteKey.current = null
    }

    identifiedUserId.current = userId
  }, [isError, isLoading, posthog, userSelf])

  // Capture a pageview on route changes. We keep both a component-scoped and
  // module-scoped dedupe key to avoid duplicate events from rerenders/remounts.
  useEffect(() => {
    if (!posthog || isLoading || isError || !userSelf) {
      return
    }

    const fullPath = `${location.pathname}${location.search}`

    if (
      previousRouteKey.current === fullPath ||
      lastTrackedRouteKey === fullPath
    ) {
      return
    }

    const routeTemplate = normalizePath(location.pathname)

    posthog.capture('$pageview', {
      path: location.pathname,
      route_template: routeTemplate,
      search: location.search,
      full_path: fullPath,
    })

    previousRouteKey.current = fullPath
    lastTrackedRouteKey = fullPath
  }, [
    isError,
    isLoading,
    location.pathname,
    location.search,
    posthog,
    userSelf,
  ])
}
