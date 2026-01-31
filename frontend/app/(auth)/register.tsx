import { Link, useRouter } from 'expo-router';
import { Pressable, StyleSheet } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { useThemeColor } from '@/hooks/use-theme-color';

export default function RegisterScreen() {
  const router = useRouter();
  const borderColor = useThemeColor({ light: '#ccc', dark: '#444' }, 'icon');
  const iconColor = useThemeColor({}, 'text');

  return (
    <ThemedView style={styles.container}>
      <ThemedView style={styles.content}>
        <ThemedText type="title" style={styles.title}>
          Create Account
        </ThemedText>
        <ThemedText style={styles.subtitle}>
          Choose your account type to get started
        </ThemedText>

        <Pressable
          style={[styles.optionCard, { borderColor }]}
          onPress={() => router.push('/(auth)/register-student')}
        >
          <ThemedView style={styles.optionIcon}>
            <IconSymbol name="person.fill" size={32} color={iconColor} />
          </ThemedView>
          <ThemedView style={styles.optionText}>
            <ThemedText type="subtitle">Student</ThemedText>
            <ThemedText style={styles.optionDescription}>
              Join classes and connect with instructors
            </ThemedText>
          </ThemedView>
        </Pressable>

        <Pressable
          style={[styles.optionCard, { borderColor }]}
          onPress={() => router.push('/(auth)/register-instructor')}
        >
          <ThemedView style={styles.optionIcon}>
            <IconSymbol name="person.badge.key.fill" size={32} color={iconColor} />
          </ThemedView>
          <ThemedView style={styles.optionText}>
            <ThemedText type="subtitle">Instructor</ThemedText>
            <ThemedText style={styles.optionDescription}>
              Create classes and manage your students
            </ThemedText>
          </ThemedView>
        </Pressable>

        <ThemedView style={styles.footer}>
          <ThemedText>Already have an account? </ThemedText>
          <Link href="/(auth)/login" asChild>
            <Pressable>
              <ThemedText type="link">Sign In</ThemedText>
            </Pressable>
          </Link>
        </ThemedView>
      </ThemedView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
  },
  title: {
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    textAlign: 'center',
    marginBottom: 32,
    opacity: 0.7,
  },
  optionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 20,
    borderWidth: 1,
    borderRadius: 12,
    marginBottom: 16,
  },
  optionIcon: {
    width: 56,
    height: 56,
    borderRadius: 28,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  optionText: {
    flex: 1,
  },
  optionDescription: {
    opacity: 0.7,
    marginTop: 4,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 24,
  },
});
