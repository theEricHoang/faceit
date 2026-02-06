import React, { useState } from 'react';
import { SafeAreaView } from 'react-native';
import { ProfilePage } from '@/components/ProfilePage';

export default function ProfileScreen() {
  const [role, setRole] = useState<'instructor' | 'student'>('student');
  const [showSettings, setShowSettings] = useState(false);

  return (
    <SafeAreaView style={{ flex: 1 }}>
      <ProfilePage
        userRole={role}
        onNavigateToSettings={() => setShowSettings(true)}
        showSettings={showSettings}
        onBack={() => setShowSettings(false)}
      />
    </SafeAreaView>
  );
}
