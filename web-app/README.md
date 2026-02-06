# Proximal Energy Web Application

## Getting Started

1. Install Node.js via `nvm` with the latest version.
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

Use the latest Node.js and npm versions for this project. Run the following
commands to install and select the latest Node.js, then update npm.

```shell
nvm install node --latest-npm
nvm use node
node --version
npm --version
```

If you use `mise`, run `mise run upgrade-node-npm` from the repo root to install
the latest Node.js and npm versions.

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

## CDN for Device Model Images

Device model images (inverter images, etc.) are served from AWS CloudFront CDN instead of being bundled with the app. This improves performance and reduces bundle size.

### Configuration

Add the CDN base URL to your environment variables:

**For Development (.env file in `web-app/` folder):**

```bash
VITE_CDN_BASE_URL=https://d1c2bmp5ry9il0.cloudfront.net
```

**For Staging/Production:**

- Add `VITE_CDN_BASE_URL` to your deployment platform's environment variables
- For AWS Amplify: Add it in the Amplify Console under Environment Variables

If `VITE_CDN_BASE_URL` is not set, the app will fall back to loading images from the public folder (backward compatible).

### Uploading New Device Model Images

When you need to add new device model images:

1. Go to [AWS S3 Console](https://s3.console.aws.amazon.com/)
2. Navigate to bucket: `proximal-static-assets`
3. Click on the `device_models` folder (or create it if it doesn't exist)
4. Click **Upload** button
5. Drag and drop your png images or click **Add files**
6. **Important**: Before uploading, click **Upload** → **Properties** → **Metadata** and add:
   - **Key**: `Cache-Control`
   - **Value**: `public, max-age=31536000, immutable`
7. Click **Upload**

After uploading, invalidate the CloudFront cache to see changes immediately:

```bash
aws cloudfront create-invalidation \
  --distribution-id E29FJ8X83I1S0J \
  --paths "/device_models/42.png" "/device_models/51.png"
```

### How It Works

The app uses utility functions in `src/utils/cdn.ts`:

- `getDeviceModelImageUrl(deviceModelId)` - Generates CDN URLs for device model images
- `getPublicAssetUrl(path)` - For other public assets (if needed)

These functions automatically use the CDN when `VITE_CDN_BASE_URL` is configured, or fall back to relative paths if not set.

### CDN Details

- **S3 Bucket**: `proximal-static-assets`
- **CloudFront Distribution ID**: `E29FJ8X83I1S0J`
- **CDN URL**: `https://d1c2bmp5ry9il0.cloudfront.net`
- **Region**: `us-east-2`
