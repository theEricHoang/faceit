import React, { useEffect, useMemo, useState } from 'react';
import { Alert, View, Text, Switch, Pressable, StyleSheet, ScrollView, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { ThemedView } from '@/components/themed-view';
import { ThemedText } from '@/components/themed-text';
import { useAuthStore } from '@/stores/auth-store';
import { usersService, type UserProfileResponse } from '@/services/users-service';
import { enrollmentService, type JobStatusResponse } from '@/services/enrollment-service';

type Role = 'instructor' | 'student';

interface ProfilePageProps {
  userRole: Role;
  onNavigateToSettings: () => void;
  showSettings?: boolean;
  onBack?: () => void;
}

export function ProfilePage({
  userRole,
  onNavigateToSettings,
  showSettings = false,
  onBack,
}: ProfilePageProps) {
  const router = useRouter();
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [pushNotifications, setPushNotifications] = useState(true);
  const [darkMode, setDarkMode] = useState(false);
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const [profile, setProfile] = useState<UserProfileResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [enrollmentStatus, setEnrollmentStatus] = useState<string | null>(null);
  const [isEnrolling, setIsEnrolling] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    const fetchProfile = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await usersService.getMyProfile();
        if (isMounted) {
          setProfile(data);
        }
      } catch (e) {
        if (isMounted) {
          setError('Failed to load profile');
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchProfile();
    return () => {
      isMounted = false;
    };
  }, []);

  const resolvedRole = useMemo(() => profile?.type ?? userRole, [profile, userRole]);
  const initials = useMemo(() => {
    const first = profile?.first_name || (resolvedRole === 'instructor' ? 'D' : 'M');
    const last = profile?.last_name || (resolvedRole === 'instructor' ? 'S' : 'E');
    return `${first[0] ?? ''}${last[0] ?? ''}`.toUpperCase();
  }, [profile, resolvedRole]);

  const handleLogout = () => {
    Alert.alert('Log Out', 'Are you sure you want to log out of FaceIT?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Log Out',
        style: 'destructive',
        onPress: async () => {
          try {
            await clearAuth();
            Alert.alert('Success', 'Logged out successfully');
          } catch (e) {
            Alert.alert('Error', 'Failed to log out');
          }
        },
      },
    ]);
  };

  const handleUploadPhoto = async () => {
    // For instructors, just show coming soon (profile photo, not face enrollment)
    if (resolvedRole !== 'student') {
      Alert.alert('Coming Soon', 'Profile photo upload coming soon');
      return;
    }

    try {
      // Request camera permissions
      const { status } = await ImagePicker.requestCameraPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert(
          'Permission Required',
          'Camera access is needed to take your face signature photo.'
        );
        return;
      }

      // Launch camera to take a selfie
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: 'images',
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.8,
        cameraType: ImagePicker.CameraType.front,
      });

      if (result.canceled || !result.assets?.[0]?.uri) {
        return; // User cancelled
      }

      const imageUri = result.assets[0].uri;

      // Confirm with user before enrolling
      Alert.alert(
        'Enroll Face',
        'This photo will be used to recognize you during attendance. Continue?',
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Enroll',
            onPress: () => performEnrollment(imageUri),
          },
        ]
      );
    } catch (e) {
      console.error('Error launching camera:', e);
      Alert.alert('Error', 'Failed to open camera. Please try again.');
    }
  };

  const performEnrollment = async (imageUri: string) => {
    setIsEnrolling(true);
    setEnrollmentStatus('Starting enrollment...');

    try {
      const result = await enrollmentService.enrollFace(imageUri, (step, status) => {
        setEnrollmentStatus(step);
      });

      if (result.status === 'SUCCEEDED') {
        Alert.alert(
          'Success!',
          'Your face signature has been enrolled successfully. You can now be recognized for attendance.'
        );
      } else if (result.status === 'FAILED') {
        const errorMsg = result.error_message || 'Unknown error';
        let userMessage = 'Face enrollment failed. ';

        if (errorMsg.includes('NO_FACE_DETECTED')) {
          userMessage += 'No face was detected in the photo. Please ensure your face is clearly visible and well-lit.';
        } else if (errorMsg.includes('MULTIPLE_FACES')) {
          userMessage += 'Multiple faces were detected. Please take a photo with only your face visible.';
        } else {
          userMessage += 'Please try again with a clear photo of your face.';
        }

        Alert.alert('Enrollment Failed', userMessage);
      }
    } catch (e: any) {
      console.error('Enrollment error:', e);
      Alert.alert(
        'Error',
        e.message || 'Failed to enroll face signature. Please try again.'
      );
    } finally {
      setIsEnrolling(false);
      setEnrollmentStatus(null);
    }
  };

  if (showSettings) {
    return (
      <ThemedView style={{ flex: 1 }}>
        <ScrollView
          contentContainerStyle={styles.container}
          keyboardShouldPersistTaps="handled"
          contentInsetAdjustmentBehavior="automatic"
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.header}>
            <Pressable onPress={onBack} style={styles.backIconButton}>
              <Ionicons name="chevron-back-outline" size={22} color="#000" />
            </Pressable>
            <Text style={styles.title}>Settings</Text>
          </View>

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Security</Text>
            <Pressable style={styles.card} onPress={() => router.push('/change-password')}>
              <View style={styles.cardInnerRow}>
                <View>
                  <Text style={styles.valueText}>Change Password</Text>
                  <Text style={styles.labelText}>Update your account password</Text>
                </View>
                <Ionicons name="chevron-forward-outline" size={18} color="#888" />
              </View>
            </Pressable>
            <Pressable style={styles.card}>
              <View style={styles.cardInnerRow}>
                <View>
                  <Text style={styles.valueText}>iCollege Connection</Text>
                  <Text style={styles.labelText}>Manage SSO connection</Text>
                </View>
                <Ionicons name="chevron-forward-outline" size={18} color="#888" />
              </View>
            </Pressable>
          </View>

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Notifications</Text>
            <View style={styles.cardRow}>
              <View>
                <Text style={styles.valueText}>Push Notifications</Text>
                <Text style={styles.labelText}>Receive notifications on this device</Text>
              </View>
              <Switch value={pushNotifications} onValueChange={setPushNotifications} />
            </View>
            <View style={styles.cardRow}>
              <View>
                <Text style={styles.valueText}>Email Notifications</Text>
                <Text style={styles.labelText}>Receive updates via email</Text>
              </View>
              <Switch value={emailNotifications} onValueChange={setEmailNotifications} />
            </View>
            <View style={styles.cardRow}>
              <View>
                <Text style={styles.valueText}>Low Attendance Alerts</Text>
                <Text style={styles.labelText}>Get notified about attendance issues</Text>
              </View>
              <Switch value={notificationsEnabled} onValueChange={setNotificationsEnabled} />
            </View>
          </View>

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Preferences</Text>
            <View style={styles.cardRow}>
              <View>
                <Text style={styles.valueText}>Dark Mode</Text>
                <Text style={styles.labelText}>Toggle dark theme</Text>
              </View>
              <Switch value={darkMode} onValueChange={setDarkMode} />
            </View>
          </View>

          {/* Demo role toggle removed */}
        </ScrollView>
      </ThemedView>
    );
  }

  return (
    <ThemedView style={{ flex: 1 }}>
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
        contentInsetAdjustmentBehavior="automatic"
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <Text style={styles.title}>Profile</Text>
        </View>

        <View style={{ alignItems: 'center', marginVertical: 16 }}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{initials}</Text>
          </View>
          <Pressable
            style={[styles.primaryButton, isEnrolling && styles.primaryButtonDisabled]}
            onPress={handleUploadPhoto}
            disabled={isEnrolling}
          >
            {isEnrolling ? (
              <View style={styles.enrollingContainer}>
                <ActivityIndicator size="small" color="#fff" />
                <Text style={styles.primaryButtonText}>{enrollmentStatus || 'Enrolling...'}</Text>
              </View>
            ) : (
              <Text style={styles.primaryButtonText}>
                {resolvedRole === 'student' ? 'Update Face Signature' : 'Update Profile Photo'}
              </Text>
            )}
          </Pressable>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Personal Information</Text>
          <View style={styles.card}>
            <Text style={styles.labelText}>Full Name</Text>
            <Text style={styles.valueText}>{profile?.full_name ?? '—'}</Text>
          </View>

          {resolvedRole === 'student' && (
            <View style={styles.card}>
              <Text style={styles.labelText}>Student ID</Text>
              <Text style={styles.valueText}>{profile?.student_number ?? 'N/A'}</Text>
            </View>
          )}

          {resolvedRole === 'instructor' && (
            <View style={styles.card}>
              <Text style={styles.labelText}>Role</Text>
              <Text style={styles.valueText}>{profile?.bio ?? '—'}</Text>
            </View>
          )}

          <View style={styles.card}>
            <Text style={styles.labelText}>Email</Text>
            <Text style={styles.valueText}>{profile?.email ?? '—'}</Text>
          </View>

          {resolvedRole === 'student' && (
            <View style={styles.card}>
              <Text style={styles.labelText}>Bio</Text>
              <Text style={styles.valueText}>{profile?.bio ?? '—'}</Text>
            </View>
          )}

          {resolvedRole === 'student' && (
            <View style={styles.card}>
              <Text style={styles.labelText}>Major</Text>
              <Text style={styles.valueText}>{profile?.major ?? '—'}</Text>
            </View>
          )}
        </View>

        <View style={styles.section}>
          <Pressable style={styles.cardRow} onPress={onNavigateToSettings}>
            <View>
              <Text style={styles.valueText}>Settings</Text>
              <Text style={styles.labelText}>Password, notifications, preferences</Text>
            </View>
            <Ionicons name="chevron-forward-outline" size={18} color="#888" />
          </Pressable>

          <Pressable style={styles.cardRow}>
            <View>
              <Text style={styles.valueText}>Help & FAQ</Text>
              <Text style={styles.labelText}>Get support and answers</Text>
            </View>
            <Ionicons name="chevron-forward-outline" size={18} color="#888" />
          </Pressable>

          <Pressable style={styles.cardRow}>
            <View>
              <Text style={styles.valueText}>Privacy Policy</Text>
              <Text style={styles.labelText}>How we protect your data</Text>
            </View>
            <Ionicons name="chevron-forward-outline" size={18} color="#888" />
          </Pressable>
        </View>

        <Pressable style={[styles.primaryButton, styles.logoutButton]} onPress={handleLogout}>
          <Text style={[styles.primaryButtonText, styles.logoutText]}>Log Out</Text>
        </Pressable>
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingVertical: 16,
    paddingHorizontal: 16,
    paddingBottom: 24,
    backgroundColor: '#fff',
  },
  header: {
    paddingHorizontal: 16,
    paddingBottom: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderColor: '#eee',
  },
  backIconButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#f3f3f3',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#eee',
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
  },
  backButton: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ccc',
  },
  section: {
    marginTop: 16,
    gap: 8,
  },
  card: {
    borderWidth: 1,
    borderColor: '#eee',
    borderRadius: 12,
    padding: 12,
    gap: 4,
    backgroundColor: '#fff',
  },
  cardInnerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#030213',
  },
  labelText: {
    color: '#717182',
    fontSize: 16,
    fontWeight: '500',
  },
  valueText: {
    color: '#030213',
    fontSize: 16,
    fontWeight: '500',
  },
  cardRow: {
    borderWidth: 1,
    borderColor: '#eee',
    borderRadius: 12,
    padding: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#fff',
    marginBottom: 8,
  },
  avatar: {
    width: 128,
    height: 128,
    borderRadius: 64,
    backgroundColor: '#000',
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 24,
  },
  primaryButton: {
    marginTop: 12,
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: '#000',
    borderRadius: 12,
    alignItems: 'center',
  },
  primaryButtonDisabled: {
    backgroundColor: '#666',
  },
  primaryButtonText: {
    color: '#fff',
    fontWeight: '600',
  },
  enrollingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  roleButton: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#eee',
    borderRadius: 12,
    paddingVertical: 10,
    alignItems: 'center',
  },
  roleButtonActive: {
    backgroundColor: '#f3f3f3',
    borderColor: '#eee',
  },
  logoutButton: {
    backgroundColor: '#d4183d',
  },
  logoutText: {
    color: '#fff',
  },
});
