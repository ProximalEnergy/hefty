import { GISProvider } from '@/contexts/GISContext'
// Pages
import { ProjectDropdownProvider } from '@/providers/ProjectDropdownProvider'
import { themes } from '@/utils/themes'
import { ClerkProvider, useUser } from '@clerk/clerk-react'
import { dark } from '@clerk/themes'
import {
  Loader,
  MantineProvider,
  createTheme,
  useComputedColorScheme,
} from '@mantine/core'
import '@mantine/core/styles.css'
import '@mantine/dates/styles.css'
import '@mantine/dropzone/styles.css'
import { Notifications } from '@mantine/notifications'
import '@mantine/notifications/styles.css'
import '@mantine/spotlight/styles.css'
import '@mantine/tiptap/styles.css'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import 'mantine-react-table/styles.css'
import 'mapbox-gl/dist/mapbox-gl.css'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'
import {
  BrowserRouter,
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom'

import { ErrorBoundary } from './ErrorBoundary'
import { HexLoader } from './HexLoader'
import { CompanyThemeManager } from './components/CompanyThemeManager'
import { PageLoader } from './components/Loading'
// Development
import RequiresUserType from './components/admin/RequiresUserType'
import { useTheme } from './contexts/ThemeContext'
// Profile
import { AccountSettings } from './pages/AccountSettings'
import { Api } from './pages/Api'
import ApplicationSettings from './pages/ApplicationSettings'
import LoomTesting from './pages/LoomTesting'
import NotFound from './pages/NotFound'
import { SignIn } from './pages/SignIn'
import DroneIntegrations from './pages/admin/DroneIntegrations'
import DronePermissions from './pages/admin/DronePermissions'
import DroneProviders from './pages/admin/DroneProviders'
import ProjectTagExplorer from './pages/admin/ProjectTagExplorer'
import SensorTypes from './pages/admin/SensorTypes'
import UserManagement from './pages/admin/UserManagement'
import ERCOTMap from './pages/development/ercot-map'
import DevelopmentHome from './pages/development/home'
import Prices from './pages/development/prices'
import ResourcePage from './pages/development/resource-page'
import { Layout } from './pages/layout/Layout'
import CreateProject from './pages/onboarding/CreateProject'
import CreatePVsystemDefinition from './pages/onboarding/Devices'
import UploadGISData from './pages/onboarding/UploadGISData'
import Combiners from './pages/onboarding/device_types/Combiners'
import Inverters from './pages/onboarding/device_types/Inverters'
import MetStations from './pages/onboarding/device_types/MetStations'
import Trackers from './pages/onboarding/device_types/Trackers'
import Transformers from './pages/onboarding/device_types/Transformers'
import { PortfolioCalendar } from './pages/portfolio/PortfolioCalendar'
// Portfolio
import PortfolioHome from './pages/portfolio/PortfolioHome'
import PortfolioKPIHome from './pages/portfolio/PortfolioKPIHome'
import PortfolioList from './pages/portfolio/PortfolioList'
import PortfolioMap from './pages/portfolio/PortfolioMap'
import PortfolioSettings from './pages/portfolio/settings/PortfolioSettings'
// Battery Health
import BatteryHealth from './pages/projects/BatteryHealth'
// Data Browsing
import DataBrowsing from './pages/projects/DataBrowsing'
// Project Admin
import ProjectAdmin from './pages/projects/ProjectAdmin'
// In Development
import ProjectAvailabilityAnalysis from './pages/projects/ProjectAvailabilityAnalysis'
import ProjectEvents from './pages/projects/ProjectEvents'
// Project Home
import ProjectHome from './pages/projects/ProjectHome'
import ProjectLossWaterfall from './pages/projects/ProjectLossWaterfall'
// Reports
import ProjectReports from './pages/projects/ProjectReports'
// Project Settings
import ProjectSettings from './pages/projects/ProjectSettings'
// Calendar
import { ProjectCalendar } from './pages/projects/calendar/ProjectCalendar'
// CMMS
import TicketDisplay from './pages/projects/cmms/TicketDisplay'
// KPIs
import ProjectContract from './pages/projects/contracts/ProjectContract'
import ProjectContracts from './pages/projects/contracts/ProjectContracts'
import CustomDash from './pages/projects/custom_dash/CustomDash'
import CustomDashMenu from './pages/projects/custom_dash/CustomDashMenu'
import DataAvailability from './pages/projects/device_details/DataAvailability'
import RealTime from './pages/projects/device_details/RealTime'
import VerticalDeviceDetails from './pages/projects/device_details/VerticalDeviceDetails'
// Device Details
import DeviceDetailsBESS from './pages/projects/device_details/horizontal/bess'
import DeviceDetailsPV from './pages/projects/device_details/horizontal/pv'
import DeviceDetailsSingle from './pages/projects/device_details/single'
import TrackerRowDetail from './pages/projects/device_details/tracker-row/page'
// DroneInspections
import DroneInspections from './pages/projects/drone_inspections/DroneInspections'
// Current Day
import EquipmentAnalysis from './pages/projects/equipment_analysis'
import EquipmentAnalysisPVDCCombinerBlock from './pages/projects/equipment_analysis/pv_dc_combiner/block/page'
import EquipmentAnalysisTrackerBlock from './pages/projects/equipment_analysis/tracker/block/page'
// Events
import EventPage from './pages/projects/events/EventPage'
import EventsMetaAnalysis from './pages/projects/events/EventsMetaAnalysis'
import UptimeTable from './pages/projects/events/UptimeTable'
// GIS
import BessEnclosureGIS from './pages/projects/gis/bess-enclosure-gis'
import CombinerBlockGIS from './pages/projects/gis/combiner-block-gis'
import CombinerGIS from './pages/projects/gis/combiner-gis'
import PCSGIS from './pages/projects/gis/pcs-gis'
import TrackerBlockGIS from './pages/projects/gis/tracker-block-gis'
import TrackerGIS from './pages/projects/gis/tracker-gis'
import ProjectKPIAlerts from './pages/projects/kpis/ProjectKPIAlerts'
import ProjectKPIContractual from './pages/projects/kpis/ProjectKPIContractual'
import ProjectKPIHome from './pages/projects/kpis/ProjectKPIHome'
import ProjectKPITemplate from './pages/projects/kpis/ProjectKPITemplate'
import SparePartsPage from './pages/projects/maintenance/SpareParts'
// McCarthy Quality
import Inspections from './pages/projects/mccarthy_quality/Inspections'
import InspectionsGIS from './pages/projects/mccarthy_quality/InspectionsGIS'
import Observations from './pages/projects/mccarthy_quality/Observations'
import ObservationsGIS from './pages/projects/mccarthy_quality/ObservationsGIS'
import QualityHome from './pages/projects/mccarthy_quality/QualityHome'
import CustomReport from './pages/projects/reports/CustomReport'
import DCAmperageReport from './pages/projects/reports/DCAmperageReport'
import InverterAvailabilityReport from './pages/projects/reports/InverterAvailabilityReport'
import ModuleDegradation from './pages/projects/reports/ModuleDegradation'
import PCSApparentVsVoltage from './pages/projects/reports/PCSApparentVsVoltageReport'
import TrackerAvailabilityReport from './pages/projects/reports/TrackerAvailabilityReport'
// Utility
import Backfill from './pages/projects/utility/Backfill'
import ExpectedPlotting from './pages/projects/utility/ExpectedPlotting'

// import CustomDash from './pages/projects/custom_dash/CustomDash'

const URL_SIGN_IN = '/sign-in'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 0,
    },
  },
})

/**
 * AuthLayout component that manages user authentication and access control.
 *
 * This component checks if the user information has been fully loaded and verifies the user's sign-in status.
 * If the user data is still loading, it displays a loading overlay. If the user is not signed in, it redirects
 * them to the sign-in page. If the user is signed in, it renders the main application layout.
 */
const AuthLayout = () => {
  const { isLoaded, isSignedIn } = useUser()
  const location = useLocation()

  // If the user is not loaded, return loader
  if (!isLoaded) {
    return (
      <div style={{ height: '100vh', width: '100vw' }}>
        <PageLoader />
      </div>
    )
  }

  // If the user is not signed in, redirect to the sign in page
  if (!isSignedIn) {
    return <Navigate to={URL_SIGN_IN} replace />
  }

  // Routes that should not show the sidebar
  const routesWithoutSidebar = [
    '/portfolio/create-project',
    '/onboarding/create-pv-system',
    '/onboarding/upload-gis-data',
    '/onboarding',
  ]
  const shouldHideSidebar = routesWithoutSidebar.some((route) =>
    location.pathname.startsWith(route),
  )

  // If the user is signed in, return the layout with the CompanyThemeManager
  return (
    <>
      <CompanyThemeManager />
      {shouldHideSidebar ? <Outlet /> : <Layout />}
    </>
  )
}

/**
 * RequiresTwoFactor component that ensures the user has two-factor authentication enabled.
 *
 * This component checks if the user information is fully loaded and verifies whether the user has
 * two-factor authentication enabled. If the user data is still loading, it displays a loading
 * indicator. If the user does not have two-factor authentication enabled and is not a demo user,
 * it redirects them to the account settings page for two-factor configuration. If the user has
 * two-factor authentication enabled or is a demo user, it renders the child components.
 */
const RequiresTwoFactor = ({ children }: { children: React.ReactNode }) => {
  const { isLoaded, user } = useUser()

  const hasTwoFactorEnabled = user?.twoFactorEnabled
  const isDemoUser = user?.publicMetadata?.demo

  // If the user is not loaded, return loader
  if (!isLoaded) {
    return <PageLoader />
  }

  // If the user does not have two factor enabled and they are not a demo user, redirect to the account settings page for two factor configuration
  if (!hasTwoFactorEnabled && !isDemoUser) {
    return <Navigate to="/account-settings#/security" replace />
  }

  // If the user has two factor enabled or is a demo user, return the children
  return children
}

const ClerkProviderWithRoutes = () => {
  const computedColorScheme = useComputedColorScheme('light', {
    getInitialValueInEffect: true,
  })

  return (
    <ClerkProvider
      // If computedColorScheme is "dark", use the dark theme
      appearance={
        computedColorScheme === 'dark' ? { baseTheme: dark } : undefined
      }
      publishableKey={import.meta.env.VITE_CLERK_PUBLISHABLE_KEY}
    >
      <Routes>
        {/* Public routes */}
        <Route path={URL_SIGN_IN} element={<SignIn />} />
        <Route path="/sign-up" element={<Navigate to={URL_SIGN_IN} />} />

        <Route path="/" element={<AuthLayout />}>
          <Route index element={<Navigate to="/portfolio" replace />} />
          <Route path="/account-settings" element={<AccountSettings />} />

          {/* Start:  Outside of main layout to hide sidebar */}
          <Route path="/portfolio/create-project" element={<CreateProject />} />
          <Route
            path="/onboarding/create-pv-system/:projectId"
            element={<CreatePVsystemDefinition />}
          />
          <Route
            path="/onboarding/upload-gis-data/:projectId"
            element={<UploadGISData />}
          />
          <Route
            path="/onboarding/:projectId/devices"
            element={<CreatePVsystemDefinition />}
          />
          <Route
            path="/onboarding/:projectId/device-types/met-stations"
            element={<MetStations />}
          />
          <Route
            path="/onboarding/:projectId/device-types/transformers"
            element={<Transformers />}
          />
          <Route
            path="/onboarding/:projectId/device-types/inverters"
            element={<Inverters />}
          />
          <Route
            path="/onboarding/:projectId/device-types/combiners"
            element={<Combiners />}
          />
          <Route
            path="/onboarding/:projectId/device-types/trackers"
            element={<Trackers />}
          />
          {/* End:  Outside of main layout to hide sidebar */}

          <Route
            element={
              <RequiresTwoFactor>
                <Outlet />
              </RequiresTwoFactor>
            }
          >
            <Route
              path="/application-settings"
              element={<ApplicationSettings />}
            />
            <Route path="/api" element={<Api />} />
            <Route path="/loom-testing" element={<LoomTesting />} />

            {/* Portfolio */}
            <Route path="/portfolio">
              <Route index element={<PortfolioHome />} />
              <Route path="list" element={<PortfolioList />} />
              <Route path="map" element={<PortfolioMap />} />
              <Route path="kpis" element={<PortfolioKPIHome />} />
              <Route path="settings" element={<PortfolioSettings />} />
              <Route path="calendar" element={<PortfolioCalendar />} />
            </Route>

            {/* Project */}
            <Route path="/projects/:projectId">
              <Route index element={<ProjectHome />} />
              <Route path="custom-dash">
                <Route index element={<CustomDashMenu />} />
                <Route path="new" element={<CustomDash />} />
                <Route path=":dashboardId" element={<CustomDash />} />
              </Route>

              <Route path="real-time" element={<RealTime />} />

              {/* Battery Health */}
              <Route path="battery-health" element={<BatteryHealth />} />

              {/* GIS */}
              <Route path="gis">
                <Route path="bess-enclosure" element={<BessEnclosureGIS />} />
                <Route path="pv-dc-combiner">
                  <Route index element={<CombinerGIS />} />
                  <Route path=":blockId" element={<CombinerBlockGIS />} />
                </Route>
                <Route path="pv-pcs" element={<PCSGIS />} />
                <Route path="tracker">
                  <Route index element={<TrackerGIS />} />
                  <Route path=":blockId" element={<TrackerBlockGIS />} />
                </Route>
              </Route>

              {/* Current Day */}
              <Route path="equipment-analysis">
                <Route index element={<EquipmentAnalysis />} />
                <Route path="pv-dc-combiner/block">
                  <Route
                    index
                    element={<EquipmentAnalysisPVDCCombinerBlock />}
                  />
                </Route>
                <Route path="tracker/block">
                  <Route index element={<EquipmentAnalysisTrackerBlock />} />
                </Route>
              </Route>

              {/* Device Details */}
              <Route path="device-details">
                <Route
                  path="data-availability"
                  element={<DataAvailability />}
                />
                <Route path="horizontal">
                  <Route path="bess" element={<DeviceDetailsBESS />} />
                  <Route path="pv" element={<DeviceDetailsPV />} />
                </Route>
                <Route path="single">
                  <Route path=":deviceId" element={<DeviceDetailsSingle />} />
                </Route>
                <Route path="vertical" element={<VerticalDeviceDetails />} />
                <Route
                  path="tracker-row/:deviceId"
                  element={<TrackerRowDetail />}
                />
              </Route>

              {/* Events */}
              <Route path="events">
                <Route index element={<ProjectEvents />} />
                <Route path="event" element={<EventPage />} />
                <Route path="uptime" element={<UptimeTable />} />
                <Route path="meta-analysis" element={<EventsMetaAnalysis />} />
              </Route>

              {/* CMMS */}
              <Route path="cmms">
                <Route path="ticket-display" element={<TicketDisplay />} />
              </Route>

              {/* Maintenance */}
              <Route path="maintenance">
                <Route path="spare-parts" element={<SparePartsPage />} />
              </Route>

              {/* KPIs */}
              <Route path="kpis">
                <Route index element={<ProjectKPIHome />} />
                <Route path="alerts" element={<ProjectKPIAlerts />} />
                <Route
                  path="contractual/:nameShort"
                  element={<ProjectKPIContractual />}
                />
                <Route
                  path="type/:kpiTypeId"
                  element={<ProjectKPITemplate />}
                />
              </Route>

              {/* Reports */}
              <Route path="reports" element={<ProjectReports />} />
              <Route
                path="reports/dc-amperage"
                element={<DCAmperageReport />}
              />
              <Route
                path="reports/module-degradation"
                element={<ModuleDegradation />}
              />
              <Route
                path="reports/tracker-availability"
                element={<TrackerAvailabilityReport />}
              />
              <Route
                path="reports/inverter-availability"
                element={<InverterAvailabilityReport />}
              />
              <Route
                path="reports/pcs-apparent-vs-voltage"
                element={<PCSApparentVsVoltage />}
              />

              <Route path="reports/custom" element={<CustomReport />} />

              {/* Contracts */}
              <Route path="contracts">
                <Route index element={<ProjectContracts />} />
                <Route path=":contractId" element={<ProjectContract />} />
                {/* <Route path="create" element={<CreateContract />} /> */}
              </Route>

              {/* Drone Inspections */}
              <Route path="drone-inspections" element={<DroneInspections />} />

              {/* Data Browsing */}
              <Route path="data-browsing" element={<DataBrowsing />} />

              {/* McCarthy Quality */}
              <Route path="quality">
                <Route index element={<QualityHome />} />
                <Route path="inspections" element={<Inspections />} />
                <Route path="inspections/gis" element={<InspectionsGIS />} />
                <Route path="observations" element={<Observations />} />
                <Route path="observations/gis" element={<ObservationsGIS />} />
              </Route>

              {/* Project Settings */}
              <Route path="settings" element={<ProjectSettings />} />

              {/* Project Admin */}
              <Route
                path="admin"
                element={
                  <RequiresUserType requiredUserType="admin">
                    <ProjectAdmin />
                  </RequiresUserType>
                }
              />

              {/* Calendar */}
              <Route path="calendar" element={<ProjectCalendar />} />

              {/* Utility */}
              <Route path="utility">
                <Route
                  path="expected"
                  element={
                    <RequiresUserType requiredUserType="superadmin">
                      <ExpectedPlotting />
                    </RequiresUserType>
                  }
                />
                <Route
                  path="backfill"
                  element={
                    <RequiresUserType requiredUserType="superadmin">
                      <Backfill />
                    </RequiresUserType>
                  }
                />
                <Route
                  path="project-tag-explorer"
                  element={
                    <RequiresUserType requiredUserType="superadmin">
                      <ProjectTagExplorer />
                    </RequiresUserType>
                  }
                />
              </Route>

              {/* In Development */}
              <Route path="loss-waterfall" element={<ProjectLossWaterfall />} />
              <Route
                path="availability-analysis"
                element={<ProjectAvailabilityAnalysis />}
              />
            </Route>

            {/* Admin */}
            <Route path="/admin">
              <Route
                path="users"
                element={
                  <RequiresUserType requiredUserType="admin">
                    <UserManagement />
                  </RequiresUserType>
                }
              />
              <Route
                path="sensor-types"
                element={
                  <RequiresUserType requiredUserType="superadmin">
                    <SensorTypes />
                  </RequiresUserType>
                }
              />
              <Route
                path="drone-integrations"
                element={
                  <RequiresUserType requiredUserType="superadmin">
                    <DroneIntegrations />
                  </RequiresUserType>
                }
              />
              <Route
                path="drone-providers"
                element={
                  <RequiresUserType requiredUserType="superadmin">
                    <DroneProviders />
                  </RequiresUserType>
                }
              />
              <Route
                path="drone-permissions"
                element={
                  <RequiresUserType requiredUserType="superadmin">
                    <DronePermissions />
                  </RequiresUserType>
                }
              />
            </Route>

            {/* Development */}
            <Route path="/development">
              <Route index element={<ERCOTMap />} />
              <Route path="resources">
                <Route index element={<DevelopmentHome />} />
                <Route path=":resourceId" element={<ResourcePage />} />
              </Route>
              <Route path="prices" element={<Prices />} />
            </Route>
          </Route>
        </Route>

        {/* Catch-all 404 route */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </ClerkProvider>
  )
}

export default function App() {
  const { primaryColor } = useTheme()

  const theme = createTheme({
    colors: {
      ...themes,
    },
    primaryShade: { light: 7, dark: 7 },
    // See defaults at
    breakpoints: {
      xl: '92em',
      '2xl': '106em',
      '3xl': '122em',
      '4xl': '138em',
      '5xl': '154em',
    },
    primaryColor: primaryColor,
    // https://stackoverflow.com/questions/8118741/css-font-helvetica-neue
    fontFamily: 'Helvetica Neue, sans-serif',
    components: {
      Loader: Loader.extend({
        defaultProps: {
          loaders: { ...Loader.defaultLoaders, hex: HexLoader },
          type: 'hex',
        },
      }),
    },
  })

  return (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <MantineProvider theme={theme} defaultColorScheme="auto">
          <ErrorBoundary>
            <Notifications
              autoClose={5000}
              position="bottom-right"
              zIndex={800}
            />

            <ProjectDropdownProvider>
              <GISProvider>
                <ClerkProviderWithRoutes />
              </GISProvider>
            </ProjectDropdownProvider>
          </ErrorBoundary>
        </MantineProvider>
        <ReactQueryDevtools
          initialIsOpen={false}
          buttonPosition="bottom-left"
        />
      </QueryClientProvider>
    </BrowserRouter>
  )
}
