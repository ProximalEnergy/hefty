import { useClerk, useUser } from '@clerk/expo';
import { Platform, Pressable, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AnimatedIcon } from '@/components/animated-icon';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { WebBadge } from '@/components/web-badge';
import { BottomTabInset, MaxContentWidth, Spacing } from '@/constants/theme';
import { useGetProjects } from '@/hooks/use-get-projects';

export default function HomeScreen() {
  const { signOut } = useClerk();
  const { user } = useUser();
  const { data: projects, error, isLoading, isRefetching } = useGetProjects();

  return (
    <ThemedView style={styles.container}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}>
        <SafeAreaView style={styles.safeArea}>
          <ThemedView type="backgroundElement" style={styles.heroCard}>
            <AnimatedIcon />
            <ThemedText type="title" style={styles.title}>
              Welcome to&nbsp;Proximal
            </ThemedText>
            <ThemedText type="small" themeColor="textSecondary" style={styles.subtitle}>
              Signed in as{' '}
              {user?.primaryEmailAddress?.emailAddress ?? user?.fullName ?? 'your account'}
            </ThemedText>
            <Pressable
              onPress={() => signOut()}
              style={({ pressed }) => [styles.signOut, pressed && styles.pressed]}>
              <ThemedText type="smallBold" style={styles.signOutText}>
                Sign out
              </ThemedText>
            </Pressable>
          </ThemedView>

          <ThemedView type="backgroundElement" style={styles.projectsCard}>
            <ThemedView type="backgroundElement" style={styles.sectionHeader}>
              <ThemedText type="subtitle" style={styles.sectionTitle}>
                Your projects
              </ThemedText>
              <ThemedText type="small" themeColor="textSecondary" style={styles.sectionSubtitle}>
                {projects?.length ? `${projects.length} project${projects.length === 1 ? '' : 's'}` : 'Portfolio'}
              </ThemedText>
            </ThemedView>

            {isLoading ? (
              <ThemedText type="small" themeColor="textSecondary">
                Loading projects...
              </ThemedText>
            ) : error ? (
              <ThemedText type="small" style={styles.errorText}>
                {error.message}
              </ThemedText>
            ) : projects?.length ? (
              projects.map((project) => (
                <ThemedView key={project.project_id} type="background" style={styles.projectRow}>
                  <ThemedText type="smallBold">{project.name_long}</ThemedText>
                </ThemedView>
              ))
            ) : (
              <ThemedText type="small" themeColor="textSecondary">
                No projects found for this account.
              </ThemedText>
            )}

            {isRefetching && (
              <ThemedText type="code" themeColor="textSecondary">
                refreshing
              </ThemedText>
            )}
          </ThemedView>

          {Platform.OS === 'web' && <WebBadge />}
        </SafeAreaView>
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    alignItems: 'center',
  },
  safeArea: {
    width: '100%',
    paddingHorizontal: Spacing.four,
    paddingTop: Spacing.four,
    paddingBottom: BottomTabInset + Spacing.four,
    gap: Spacing.three,
    maxWidth: MaxContentWidth,
  },
  heroCard: {
    alignItems: 'center',
    gap: Spacing.three,
    paddingHorizontal: Spacing.four,
    paddingVertical: Spacing.five,
    borderRadius: Spacing.four,
  },
  title: {
    textAlign: 'center',
  },
  subtitle: {
    textAlign: 'center',
  },
  signOut: {
    paddingVertical: Spacing.two,
    paddingHorizontal: Spacing.four,
    borderRadius: Spacing.three,
    backgroundColor: '#208AEF',
  },
  signOutText: {
    color: '#ffffff',
  },
  pressed: {
    opacity: 0.7,
  },
  projectsCard: {
    gap: Spacing.three,
    paddingHorizontal: Spacing.four,
    paddingVertical: Spacing.four,
    borderRadius: Spacing.four,
  },
  sectionHeader: {
    gap: Spacing.one,
  },
  sectionTitle: {
    fontSize: 28,
    lineHeight: 34,
  },
  sectionSubtitle: {
    textTransform: 'uppercase',
  },
  projectRow: {
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.three,
    borderRadius: Spacing.three,
  },
  errorText: {
    color: '#D92D20',
  },
});
