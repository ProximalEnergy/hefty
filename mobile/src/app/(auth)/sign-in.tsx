import { useAuth, useClerk } from '@clerk/expo';
import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AnimatedIcon } from '@/components/animated-icon';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

function getErrorMessage(error: unknown) {
  if (
    typeof error === 'object' &&
    error !== null &&
    'errors' in error &&
    Array.isArray(error.errors) &&
    error.errors[0]?.message
  ) {
    return String(error.errors[0].message);
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'Unable to sign in. Please check your credentials and try again.';
}

type ClerkSignInResult = {
  status?: string;
  createdSessionId?: string | null;
  error?: { message?: string } | null;
  supportedSecondFactors?: ClerkSecondFactor[];
  prepareSecondFactor?: (params: ClerkSecondFactorAttempt) => Promise<ClerkSignInResult>;
  attemptSecondFactor?: (params: ClerkSecondFactorAttempt & { code: string }) => Promise<ClerkSignInResult>;
};

type ClerkSecondFactor = {
  strategy?: string;
  emailAddressId?: string;
  phoneNumberId?: string;
  safeIdentifier?: string;
};

type ClerkSecondFactorAttempt = {
  strategy: string;
  emailAddressId?: string;
  phoneNumberId?: string;
};

type ClerkWithEmailSignIn = {
  client?: {
    signIn?: {
      create: (params: { identifier: string; password: string }) => Promise<ClerkSignInResult>;
    };
  };
  setActive: (params: { session: string }) => Promise<void>;
};

function getSecondFactorAttempt(factors: ClerkSecondFactor[] = []): ClerkSecondFactorAttempt | null {
  const supportedFactor =
    factors.find((factor) => factor.strategy === 'totp') ??
    factors.find((factor) => factor.strategy === 'phone_code') ??
    factors.find((factor) => factor.strategy === 'email_code') ??
    factors.find((factor) => factor.strategy === 'backup_code');

  if (!supportedFactor?.strategy) {
    return null;
  }

  return {
    strategy: supportedFactor.strategy,
    emailAddressId: supportedFactor.emailAddressId,
    phoneNumberId: supportedFactor.phoneNumberId,
  };
}

function getSecondFactorMessage(factors: ClerkSecondFactor[] = []) {
  const factor = factors.find((item) => item.strategy === getSecondFactorAttempt(factors)?.strategy);

  if (factor?.strategy === 'totp') {
    return 'Enter the 6-digit code from your authenticator app.';
  }

  if (factor?.strategy === 'phone_code') {
    return `Enter the code Clerk sent to ${factor.safeIdentifier ?? 'your phone'}.`;
  }

  if (factor?.strategy === 'email_code') {
    return `Enter the code Clerk sent to ${factor.safeIdentifier ?? 'your email'}.`;
  }

  if (factor?.strategy === 'backup_code') {
    return 'Enter one of your Clerk backup codes.';
  }

  return 'This account requires a second verification step.';
}

function getIncompleteSignInMessage(signInAttempt: ClerkSignInResult) {
  switch (signInAttempt.status) {
    case 'needs_second_factor':
      return getSecondFactorMessage(signInAttempt.supportedSecondFactors);
    case 'needs_first_factor':
      return 'Clerk needs another first-factor method for this account. Try signing in with the web app for now.';
    case 'needs_identifier':
      return 'Enter the email address for your Proximal account.';
    case 'needs_new_password':
      return 'This account needs a password reset before mobile sign-in can continue.';
    case 'needs_reset_password':
      return 'This account requires a password reset before mobile sign-in can continue.';
    default:
      return `Sign-in could not finish. Clerk returned status "${signInAttempt.status ?? 'unknown'}".`;
  }
}

export default function SignInScreen() {
  const { isLoaded, isSignedIn } = useAuth({ treatPendingAsSignedOut: false });
  const clerk = useClerk() as unknown as ClerkWithEmailSignIn;
  const router = useRouter();
  const theme = useTheme();
  const [emailAddress, setEmailAddress] = useState('');
  const [password, setPassword] = useState('');
  const [secondFactorCode, setSecondFactorCode] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [verificationMessage, setVerificationMessage] = useState<string | null>(null);
  const [pendingSignIn, setPendingSignIn] = useState<ClerkSignInResult | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (isSignedIn) {
      router.replace('/');
    }
  }, [isSignedIn, router]);

  const handleSignIn = async () => {
    if (!isLoaded || isSubmitting) return;

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const signIn = clerk.client?.signIn;

      if (!signIn) {
        throw new Error('Clerk sign-in is not ready yet.');
      }

      const signInAttempt = await signIn.create({
        identifier: emailAddress.trim(),
        password,
      });

      if (signInAttempt.error) {
        throw new Error(signInAttempt.error.message);
      }

      if (signInAttempt.status === 'complete' && signInAttempt.createdSessionId) {
        await clerk.setActive({ session: signInAttempt.createdSessionId });
        router.replace('/');
        return;
      }

      if (signInAttempt.status === 'needs_second_factor') {
        const secondFactorAttempt = getSecondFactorAttempt(signInAttempt.supportedSecondFactors);

        if (!secondFactorAttempt || !signInAttempt.attemptSecondFactor) {
          setErrorMessage(
            'This account requires a second factor that this mobile sign-in screen does not support yet. Try signing in through the web app.',
          );
          return;
        }

        if (secondFactorAttempt.strategy !== 'totp' && signInAttempt.prepareSecondFactor) {
          await signInAttempt.prepareSecondFactor(secondFactorAttempt);
        }

        setPendingSignIn(signInAttempt);
        setVerificationMessage(getSecondFactorMessage(signInAttempt.supportedSecondFactors));
        return;
      }

      setErrorMessage(getIncompleteSignInMessage(signInAttempt));
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSecondFactor = async () => {
    if (!pendingSignIn?.attemptSecondFactor || isSubmitting) return;

    const secondFactorAttempt = getSecondFactorAttempt(pendingSignIn.supportedSecondFactors);

    if (!secondFactorAttempt) {
      setErrorMessage('This account requires a second factor that this mobile sign-in screen does not support yet.');
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const signInAttempt = await pendingSignIn.attemptSecondFactor({
        ...secondFactorAttempt,
        code: secondFactorCode.trim(),
      });

      if (signInAttempt.error) {
        throw new Error(signInAttempt.error.message);
      }

      if (signInAttempt.status === 'complete' && signInAttempt.createdSessionId) {
        await clerk.setActive({ session: signInAttempt.createdSessionId });
        router.replace('/');
        return;
      }

      setPendingSignIn(signInAttempt);
      setErrorMessage(getIncompleteSignInMessage(signInAttempt));
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ThemedView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.select({ ios: 'padding', default: undefined })}
        style={styles.keyboardView}>
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.brandSection}>
            <AnimatedIcon />
            <ThemedText type="subtitle" style={styles.title}>
              Sign in to Proximal
            </ThemedText>
            <ThemedText type="small" themeColor="textSecondary" style={styles.subtitle}>
              Use your Proximal account to continue.
            </ThemedText>
          </View>

          <ThemedView type="backgroundElement" style={styles.form}>
            {pendingSignIn ? (
              <>
                {verificationMessage && (
                  <ThemedText type="small" themeColor="textSecondary">
                    {verificationMessage}
                  </ThemedText>
                )}
                <View style={styles.field}>
                  <ThemedText type="smallBold">Verification code</ThemedText>
                  <TextInput
                    autoCapitalize="none"
                    autoComplete="one-time-code"
                    autoCorrect={false}
                    keyboardType="number-pad"
                    onChangeText={setSecondFactorCode}
                    onSubmitEditing={handleSecondFactor}
                    placeholder="123456"
                    placeholderTextColor={theme.textSecondary}
                    style={[
                      styles.input,
                      {
                        backgroundColor: theme.background,
                        borderColor: theme.backgroundSelected,
                        color: theme.text,
                      },
                    ]}
                    textContentType="oneTimeCode"
                    value={secondFactorCode}
                  />
                </View>
              </>
            ) : (
              <>
                <View style={styles.field}>
                  <ThemedText type="smallBold">Email</ThemedText>
                  <TextInput
                    autoCapitalize="none"
                    autoComplete="email"
                    autoCorrect={false}
                    keyboardType="email-address"
                    onChangeText={setEmailAddress}
                    placeholder="you@proximal.energy"
                    placeholderTextColor={theme.textSecondary}
                    style={[
                      styles.input,
                      {
                        backgroundColor: theme.background,
                        borderColor: theme.backgroundSelected,
                        color: theme.text,
                      },
                    ]}
                    textContentType="username"
                    value={emailAddress}
                  />
                </View>

                <View style={styles.field}>
                  <ThemedText type="smallBold">Password</ThemedText>
                  <TextInput
                    autoCapitalize="none"
                    autoComplete="current-password"
                    onChangeText={setPassword}
                    onSubmitEditing={handleSignIn}
                    placeholder="Password"
                    placeholderTextColor={theme.textSecondary}
                    secureTextEntry
                    style={[
                      styles.input,
                      {
                        backgroundColor: theme.background,
                        borderColor: theme.backgroundSelected,
                        color: theme.text,
                      },
                    ]}
                    textContentType="password"
                    value={password}
                  />
                </View>
              </>
            )}

            {errorMessage && (
              <ThemedText type="small" style={styles.error}>
                {errorMessage}
              </ThemedText>
            )}

            <Pressable
              disabled={!isLoaded || isSubmitting}
              onPress={pendingSignIn ? handleSecondFactor : handleSignIn}
              style={({ pressed }) => [
                styles.submitButton,
                (!isLoaded || isSubmitting) && styles.disabled,
                pressed && styles.pressed,
              ]}>
              {isSubmitting ? (
                <ActivityIndicator color="#ffffff" />
              ) : (
                <ThemedText type="smallBold" style={styles.submitText}>
                  {pendingSignIn ? 'Verify code' : 'Sign in'}
                </ThemedText>
              )}
            </Pressable>

            {pendingSignIn && (
              <Pressable
                disabled={isSubmitting}
                onPress={() => {
                  setPendingSignIn(null);
                  setSecondFactorCode('');
                  setVerificationMessage(null);
                  setErrorMessage(null);
                }}>
                <ThemedText type="linkPrimary" style={styles.secondaryAction}>
                  Use a different account
                </ThemedText>
              </Pressable>
            )}
          </ThemedView>
        </SafeAreaView>
      </KeyboardAvoidingView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  keyboardView: {
    flex: 1,
  },
  safeArea: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.four,
    padding: Spacing.four,
  },
  brandSection: {
    alignItems: 'center',
    gap: Spacing.three,
  },
  title: {
    textAlign: 'center',
  },
  subtitle: {
    textAlign: 'center',
  },
  form: {
    gap: Spacing.three,
    width: '100%',
    maxWidth: MaxContentWidth,
    padding: Spacing.four,
    borderRadius: Spacing.four,
  },
  field: {
    gap: Spacing.two,
  },
  input: {
    borderWidth: 1,
    borderRadius: Spacing.three,
    fontSize: 16,
    minHeight: 52,
    paddingHorizontal: Spacing.three,
  },
  error: {
    color: '#D92D20',
  },
  submitButton: {
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 52,
    borderRadius: Spacing.three,
    backgroundColor: '#208AEF',
  },
  submitText: {
    color: '#ffffff',
  },
  disabled: {
    opacity: 0.6,
  },
  pressed: {
    opacity: 0.7,
  },
  secondaryAction: {
    textAlign: 'center',
  },
});
