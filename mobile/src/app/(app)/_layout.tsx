import { useAuth } from '@clerk/expo';
import { Redirect } from 'expo-router';

import AppTabs from '@/components/app-tabs';
import { AuthLoading } from '@/components/auth-loading';

export default function AppLayout() {
  const { isLoaded, isSignedIn } = useAuth({ treatPendingAsSignedOut: false });

  if (!isLoaded) {
    return <AuthLoading />;
  }

  if (!isSignedIn) {
    return <Redirect href="/sign-in" />;
  }

  return <AppTabs />;
}
