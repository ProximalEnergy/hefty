# Proximal Energy Web Application

## Getting Started

1. Install Node.js version 20. Installation instructions can be found [here](https://nodejs.org/en/download). Make sure to select v20 for macOS using nvm with npm.
2. Install dependencies using `npm install`.
3. Fix non-breaking dependencies with `npm audit fix`
4. `npx node build-plotly-custom.js` (see \_README_PLOTLY.md)
5. Create a `.env` file and add the following variables. Reach out to someone on the team to get the correct values.
   - `VITE_CLERK_SECRET_KEY`
   - `VITE_CLERK_PUBLISHABLE_KEY`
   - `VITE_OPENWEATHERMAP_APP_ID`
   - `VITE_MAPBOX_TOKEN`
   - `VITE_ENVIRONMENT`=`DEV`

6. Run the development server using `npm run dev`.
7. Navigate to `http://localhost:5173` to view the application!

In order to see data, you will need to also run the API on your local machine. See the [API README](https://github.com/ProximalEnergy/api/blob/main/README.md) for how to get started.

## Node.js Version

Node.js version 20 is required to run the project. Run the following commands to ensure you are using version 20.

```shell
nvm install 20
nvm use 20
node --version
```

## Check for package updates

To check for available package updates run the following commands. Note that this will not upgrade the packages or change the `packages.json` file.

```shell
npx npm-check-updates
npx npm-check-updates --target patch -u // Only available patch updates
npx npm-check-updates --target minor -u // Only available minor updates
```

### Upgrading Mantine packages

To update all installed mantine packages, run the following commands.

```shell
npx npm-check-updates "@mantine/*" "@mantinex/*" postcss-preset-mantine -u
npm install
```

Note that sometimes you might encounter a dependency resolution error. This is because there are multiple mantine packages wanting to be updated at the same time. Try the following command instead.

```shell
npm install --legacy-peer-deps
```

### canvas release not found

If you encounter an error related to not being able to install a specific canvas release from GitHub, it could be due to other missing dependencies on your machine. Run the following command to install the required dependencies.

```shell
brew install pkg-config cairo pango libpng jpeg giflib librsvg pixman
```

### Further Documentation and Resources

- [Bundle information](https://github.com/plotly/plotly.js/blob/master/dist/README.md#bundle-information) (plotly.js)
- [Custom bundle](https://github.com/plotly/plotly.js/blob/master/CUSTOM_BUNDLE.md#custom-bundle) (plotly.js)
- [node-canvas](https://github.com/Automattic/node-canvas)

## Theme Customization

To add a new client theme, follow the steps below.

1. Download a logo from company website.
2. Save the logo as `logo_<company_name>.<ext>` in the `public` folder.
3. Navigate to `src/pages/layout/header/Logo.tsx` and add a conditional statement for the new company. Note, you might have to adjust the `h` prop to ensure the logo is displayed correctly.
4. Navigate to `src/App.tsx`, locate the `ProtectedRoute` component, and add a conditional statement for the new company.

## Important Routes

Clerk protects the pages behind auth
App.tsx (Clerk Protected Routes)
