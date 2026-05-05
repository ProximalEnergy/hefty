# Proximal Energy Web Application

## Getting Started

Commands below assume you ran `mise install` from the repo root. If your shell
does not auto-activate `mise`, prefix direct `pnpm` commands with
`mise exec -C web-app --`.

1. Install toolchain versions with `mise install` from the repo root.
2. Install dependencies using `mise run web:install`.
3. Fix non-breaking dependencies with `pnpm audit` and apply fixes manually
4. Create a `.env` file and add the following variables. Reach out to someone on the team to get the correct values.
   - `VITE_CLERK_SECRET_KEY`
   - `VITE_CLERK_PUBLISHABLE_KEY`
   - `VITE_OPENWEATHERMAP_APP_ID`
   - `VITE_MAPBOX_TOKEN`
   - `VITE_ENVIRONMENT`=`DEV`
   - Optional: `VITE_API_BASE_URL`
   - Optional: `VITE_CHAT_WS_URL`

5. Run the development server using `mise run web:dev`.
6. Navigate to `http://localhost:5173` to view the application!

In order to see data, you will need to also run the API on your local machine. See the [API README](https://github.com/ProximalEnergy/api/blob/main/README.md) for how to get started.

## Node.js Version

This repo pins Node.js and pnpm in the root `mise` config. Install them from
the repo root and verify the versions with:

```shell
mise install
mise exec -- node --version
mise exec -C web-app -- pnpm --version
```

## Check for package updates

To check for available package updates run the following commands. Note that this will not upgrade the packages or change the `packages.json` file.

```shell
pnpm dlx npm-check-updates
pnpm dlx npm-check-updates --target patch -u // Only available patch updates
pnpm dlx npm-check-updates --target minor -u // Only available minor updates
```

### Upgrading Mantine packages

To update all installed mantine packages, run the following commands.

```shell
pnpm dlx npm-check-updates "@mantine/*" "@mantinex/*" postcss-preset-mantine -u
pnpm install
```

Note that sometimes you might encounter a dependency resolution error. This is because there are multiple mantine packages wanting to be updated at the same time. Try the following command instead.

```shell
pnpm install
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

## Deployment Overrides

For non-standard deployments such as `sandbox`, you can override the default
API and chat routing with deployment environment variables:

```bash
VITE_ENVIRONMENT=SANDBOX
VITE_API_BASE_URL=https://api.sandbox.proximal.energy
VITE_CHAT_WS_URL=wss://chat.proximal.energy/ws
```

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
