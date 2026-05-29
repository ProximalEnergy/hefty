import { useAuth } from '@clerk/expo';
import { Redirect, Stack } from 'expo-router';

import { AuthLoading } from '@/components/auth-loading';

export default function AuthLayout() {
  const { isLoaded, isSignedIn } = useAuth({ treatPendingAsSignedOut: false });

  if (!isLoaded) {
    return <AuthLoading />;
  }

  if (isSignedIn) {
    return <Redirect href="/" />;
  }

  return <Stack screenOptions={{ headerShown: false }} />;
}
