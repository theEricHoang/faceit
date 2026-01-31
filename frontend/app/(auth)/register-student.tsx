import { Link, useRouter } from 'expo-router';
import { useState } from 'react';
import {
    ActivityIndicator,
    KeyboardAvoidingView,
    Platform,
    Pressable,
    ScrollView,
    StyleSheet,
    TextInput,
} from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useThemeColor } from '@/hooks/use-theme-color';
import { registerStudent } from '@/services/auth-service';

export default function RegisterStudentScreen() {
  const router = useRouter();

  // Required fields
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');

  // Optional fields
  const [bio, setBio] = useState('');
  const [studentNumber, setStudentNumber] = useState('');
  const [major, setMajor] = useState('');

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const textColor = useThemeColor({}, 'text');
  const borderColor = useThemeColor({ light: '#ccc', dark: '#444' }, 'icon');
  const placeholderColor = useThemeColor({ light: '#999', dark: '#666' }, 'icon');

  const validateForm = (): string | null => {
    if (!email || !password || !confirmPassword || !firstName || !lastName) {
      return 'Please fill in all required fields';
    }
    if (password.length < 8) {
      return 'Password must be at least 8 characters';
    }
    if (password !== confirmPassword) {
      return 'Passwords do not match';
    }
    if (studentNumber && !/^\d{9}$/.test(studentNumber)) {
      return 'Student number must be exactly 9 digits';
    }
    return null;
  };

  const handleRegister = async () => {
    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      await registerStudent({
        email,
        password,
        first_name: firstName,
        last_name: lastName,
        bio: bio || '',
        number: studentNumber || null,
        major: major || null,
      });
      router.replace('/');
    } catch (err: any) {
      setError(err.data?.detail || err.message || 'Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const inputStyle = [styles.input, { color: textColor, borderColor }];

  return (
    <ThemedView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.flex}
      >
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
        >
          <ThemedText type="title" style={styles.title}>
            Student Registration
          </ThemedText>
          <ThemedText style={styles.subtitle}>
            Create your student account
          </ThemedText>

          {error && (
            <ThemedView style={styles.errorContainer}>
              <ThemedText style={styles.errorText}>{error}</ThemedText>
            </ThemedView>
          )}

          <ThemedText type="defaultSemiBold" style={styles.sectionTitle}>
            Account Information
          </ThemedText>

          <TextInput
            style={inputStyle}
            placeholder="Email *"
            placeholderTextColor={placeholderColor}
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
            autoComplete="email"
            editable={!isLoading}
          />

          <TextInput
            style={inputStyle}
            placeholder="Password * (min 8 characters)"
            placeholderTextColor={placeholderColor}
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            autoComplete="new-password"
            editable={!isLoading}
          />

          <TextInput
            style={inputStyle}
            placeholder="Confirm Password *"
            placeholderTextColor={placeholderColor}
            value={confirmPassword}
            onChangeText={setConfirmPassword}
            secureTextEntry
            autoComplete="new-password"
            editable={!isLoading}
          />

          <ThemedText type="defaultSemiBold" style={styles.sectionTitle}>
            Personal Information
          </ThemedText>

          <TextInput
            style={inputStyle}
            placeholder="First Name *"
            placeholderTextColor={placeholderColor}
            value={firstName}
            onChangeText={setFirstName}
            autoComplete="given-name"
            editable={!isLoading}
          />

          <TextInput
            style={inputStyle}
            placeholder="Last Name *"
            placeholderTextColor={placeholderColor}
            value={lastName}
            onChangeText={setLastName}
            autoComplete="family-name"
            editable={!isLoading}
          />

          <TextInput
            style={[inputStyle, styles.textArea]}
            placeholder="Bio (optional)"
            placeholderTextColor={placeholderColor}
            value={bio}
            onChangeText={setBio}
            multiline
            numberOfLines={3}
            editable={!isLoading}
          />

          <ThemedText type="defaultSemiBold" style={styles.sectionTitle}>
            Student Details
          </ThemedText>

          <TextInput
            style={inputStyle}
            placeholder="Student Number (9 digits, optional)"
            placeholderTextColor={placeholderColor}
            value={studentNumber}
            onChangeText={setStudentNumber}
            keyboardType="number-pad"
            maxLength={9}
            editable={!isLoading}
          />

          <TextInput
            style={inputStyle}
            placeholder="Major (optional)"
            placeholderTextColor={placeholderColor}
            value={major}
            onChangeText={setMajor}
            editable={!isLoading}
          />

          <Pressable
            style={[styles.button, isLoading && styles.buttonDisabled]}
            onPress={handleRegister}
            disabled={isLoading}
          >
            {isLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <ThemedText style={styles.buttonText}>Create Account</ThemedText>
            )}
          </Pressable>

          <ThemedView style={styles.footer}>
            <ThemedText>Already have an account? </ThemedText>
            <Link href="/(auth)/login" asChild>
              <Pressable>
                <ThemedText type="link">Sign In</ThemedText>
              </Pressable>
            </Link>
          </ThemedView>
        </ScrollView>
      </KeyboardAvoidingView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  flex: {
    flex: 1,
  },
  content: {
    padding: 24,
    paddingTop: 60,
  },
  title: {
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    textAlign: 'center',
    marginBottom: 24,
    opacity: 0.7,
  },
  sectionTitle: {
    marginTop: 8,
    marginBottom: 12,
  },
  errorContainer: {
    backgroundColor: '#ffebee',
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
  },
  errorText: {
    color: '#c62828',
    textAlign: 'center',
  },
  input: {
    height: 50,
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 16,
    marginBottom: 16,
    fontSize: 16,
  },
  textArea: {
    height: 100,
    paddingTop: 12,
    textAlignVertical: 'top',
  },
  button: {
    backgroundColor: '#0a7ea4',
    height: 50,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 8,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 24,
    marginBottom: 40,
  },
});
