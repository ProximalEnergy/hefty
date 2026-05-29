# Welcome to your Expo app 👋

This is an [Expo](https://expo.dev) project created with [`create-expo-app`](https://www.npmjs.com/package/create-expo-app).

## Get started

1. Install dependencies

   ```bash
   npm install
   ```

2. Start the app

   ```bash
   npx expo start
   ```

In the output, you'll find options to open the app in a

- [development build](https://docs.expo.dev/develop/development-builds/introduction/)
- [Android emulator](https://docs.expo.dev/workflow/android-studio-emulator/)
- [iOS simulator](https://docs.expo.dev/workflow/ios-simulator/)
- [Expo Go](https://expo.dev/go), a limited sandbox for trying out app development with Expo

You can start developing by editing the files inside the **app** directory. This project uses [file-based routing](https://docs.expo.dev/router/introduction).

## Get a fresh project

When you're ready, run:

```bash
npm run reset-project
```

This command will move the starter code to the **app-example** directory and create a blank **app** directory where you can start developing.

### Other setup steps

- To set up ESLint for linting, run `npx expo lint`, or follow our guide on ["Using ESLint and Prettier"](https://docs.expo.dev/guides/using-eslint/)
- If you'd like to set up unit testing, follow our guide on ["Unit Testing with Jest"](https://docs.expo.dev/develop/unit-testing/)
- Learn more about the TypeScript setup in this template in our guide on ["Using TypeScript"](https://docs.expo.dev/guides/typescript/)

## Learn more

To learn more about developing your project with Expo, look at the following resources:

- [Expo documentation](https://docs.expo.dev/): Learn fundamentals, or go into advanced topics with our [guides](https://docs.expo.dev/guides).
- [Learn Expo tutorial](https://docs.expo.dev/tutorial/introduction/): Follow a step-by-step tutorial where you'll create a project that runs on Android, iOS, and the web.

## Join the community

Join our community of developers creating universal apps.

- [Expo on GitHub](https://github.com/expo/expo): View our open source platform and contribute.
- [Discord community](https://chat.expo.dev): Chat with Expo users and ask questions.


## Dev onboarding
1. Download Xcode from the App Store
1. Install platform support for iOS on Xcode
   1. Open Xcode
   1. In the toolbar, open Xcode -> Settings
   1. Select Components from the sidebar
   1. Install iOS
1. Complete your Xcode install:
   - Run `sudo xcode-select -s /Applications/Xcode.app/Contents/Developer`
1. Open the Simulator app
   - `open -a Simulator`
1. Create a `mobile/.env` file with the following variables:
   - `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_Y29uY3JldGUtc25hcHBlci04LmNsZXJrLmFjY291bnRzLmRldiQ`
   - `EXPO_PUBLIC_API_BASE_URL=https://api.staging.proximal.energy`
   - Note here: I'm currently using the Staging publishable key & API URL, because I don't have the prod publishable key and because my dev API is local to my computer, which is not the same device as the simulated iPhone. We can figure this out later.
1. Install expo locally to your development environment. From `/mono`:
   - `cd mobile`
   - `npm install expo`
1. Run the app:
   `npx expo start --ios --go`
1. On initial launch, Expo Go will be installed on your simulated iPhone. This will not happen on subsequent launches.