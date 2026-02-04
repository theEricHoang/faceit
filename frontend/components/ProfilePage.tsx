import React, { useState } from 'react';
import { Alert, View, Text, Switch, Pressable, StyleSheet, ScrollView } from 'react-native';
import { ThemedView } from '@/components/themed-view';
import { ThemedText } from '@/components/themed-text';

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
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [pushNotifications, setPushNotifications] = useState(true);
  const [darkMode, setDarkMode] = useState(false);

  const handleLogout = () => {
    Alert.alert('Log Out', 'Are you sure you want to log out of FaceIT?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Log Out',
        style: 'destructive',
        onPress: () => Alert.alert('Success', 'Logged out successfully'),
      },
    ]);
  };

  const handleUploadPhoto = () => {
    Alert.alert('Coming Soon', 'Face image upload coming soon');
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
          <View style={styles.headerRow}>
            <Pressable onPress={onBack} style={styles.backButton}>
              <ThemedText type="defaultSemiBold">Back</ThemedText>
            </Pressable>
            <ThemedText type="title">Settings</ThemedText>
          </View>

          <View style={styles.section}>
            <ThemedText type="subtitle">Security</ThemedText>
            <View style={styles.card}>
              <ThemedText>Change Password</ThemedText>
              <ThemedText lightColor="#687076">Update your account password</ThemedText>
            </View>
            <View style={styles.card}>
              <ThemedText>iCollege Connection</ThemedText>
              <ThemedText lightColor="#687076">Manage SSO connection</ThemedText>
            </View>
          </View>

          <View style={styles.section}>
            <ThemedText type="subtitle">Notifications</ThemedText>
            <View style={styles.cardRow}>
              <View>
                <ThemedText>Push Notifications</ThemedText>
                <ThemedText lightColor="#687076">Receive notifications on this device</ThemedText>
              </View>
              <Switch value={pushNotifications} onValueChange={setPushNotifications} />
            </View>
            <View style={styles.cardRow}>
              <View>
                <ThemedText>Email Notifications</ThemedText>
                <ThemedText lightColor="#687076">Receive updates via email</ThemedText>
              </View>
              <Switch value={emailNotifications} onValueChange={setEmailNotifications} />
            </View>
            <View style={styles.cardRow}>
              <View>
                <ThemedText>Low Attendance Alerts</ThemedText>
                <ThemedText lightColor="#687076">Get notified about attendance issues</ThemedText>
              </View>
              <Switch value={notificationsEnabled} onValueChange={setNotificationsEnabled} />
            </View>
          </View>

          <View style={styles.section}>
            <ThemedText type="subtitle">Preferences</ThemedText>
            <View style={styles.cardRow}>
              <View>
                <ThemedText>Dark Mode</ThemedText>
                <ThemedText lightColor="#687076">Toggle dark theme</ThemedText>
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
        <View style={styles.headerRow}>
          <ThemedText type="title">Profile</ThemedText>
        </View>

        <View style={{ alignItems: 'center', marginVertical: 16 }}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{userRole === 'instructor' ? 'DS' : 'ME'}</Text>
          </View>
          <Pressable style={styles.primaryButton} onPress={handleUploadPhoto}>
            <Text style={styles.primaryButtonText}>
              {userRole === 'student' ? 'Upload Face Images' : 'Update Profile Photo'}
            </Text>
          </Pressable>
        </View>

        <View style={styles.section}>
          <ThemedText type="subtitle">Personal Information</ThemedText>
          <View style={styles.card}>
            <ThemedText lightColor="#687076">Full Name</ThemedText>
            <ThemedText>
              {userRole === 'instructor' ? 'Dr. Sarah Smith' : 'Alex Johnson'}
            </ThemedText>
          </View>

          {userRole === 'student' && (
            <View style={styles.card}>
              <ThemedText lightColor="#687076">Student ID</ThemedText>
              <ThemedText>S123456</ThemedText>
            </View>
          )}

          {userRole === 'instructor' && (
            <View style={styles.card}>
              <ThemedText lightColor="#687076">Role</ThemedText>
              <ThemedText>Associate Professor</ThemedText>
            </View>
          )}

          <View style={styles.card}>
            <ThemedText lightColor="#687076">Email</ThemedText>
            <ThemedText>
              {userRole === 'instructor'
                ? 'sarah.smith@university.edu'
                : 'alex.johnson@university.edu'}
            </ThemedText>
          </View>
        </View>

        <View style={styles.section}>
          <Pressable style={styles.cardRow} onPress={onNavigateToSettings}>
            <View>
              <ThemedText>Settings</ThemedText>
              <ThemedText lightColor="#687076">Password, notifications, preferences</ThemedText>
            </View>
          </Pressable>

          <Pressable style={styles.cardRow}>
            <View>
              <ThemedText>Help & FAQ</ThemedText>
              <ThemedText lightColor="#687076">Get support and answers</ThemedText>
            </View>
          </Pressable>

          <Pressable style={styles.cardRow}>
            <View>
              <ThemedText>Privacy Policy</ThemedText>
              <ThemedText lightColor="#687076">How we protect your data</ThemedText>
            </View>
          </Pressable>
        </View>

        <Pressable style={[styles.primaryButton, { backgroundColor: '#d9534f' }]} onPress={handleLogout}>
          <Text style={[styles.primaryButtonText, { color: '#fff' }]}>Log Out</Text>
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
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
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
    borderColor: '#e0e0e0',
    borderRadius: 12,
    padding: 12,
    gap: 4,
    backgroundColor: 'transparent',
  },
  cardRow: {
    borderWidth: 1,
    borderColor: '#e0e0e0',
    borderRadius: 12,
    padding: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: 'transparent',
    marginBottom: 8,
  },
  avatar: {
    width: 128,
    height: 128,
    borderRadius: 64,
    backgroundColor: 'rgba(10, 126, 164, 0.1)',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#0a7ea4',
  },
  avatarText: {
    color: '#0a7ea4',
    fontWeight: '600',
    fontSize: 24,
  },
  primaryButton: {
    marginTop: 12,
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: '#0a7ea4',
    borderRadius: 12,
    alignItems: 'center',
  },
  primaryButtonText: {
    color: '#fff',
    fontWeight: '600',
  },
  roleButton: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    borderRadius: 12,
    paddingVertical: 10,
    alignItems: 'center',
  },
  roleButtonActive: {
    backgroundColor: 'rgba(10, 126, 164, 0.15)',
    borderColor: '#0a7ea4',
  },
});
