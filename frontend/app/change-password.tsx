import React, { useState } from 'react';
import { View, Text, TextInput, StyleSheet, Pressable, Alert, ActivityIndicator, SafeAreaView } from 'react-native';
import { useRouter } from 'expo-router';
import { usersService } from '@/services/users-service';

export default function ChangePasswordScreen() {
  const router = useRouter();
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const canSubmit = newPassword.length >= 8 && confirmPassword.length >= 8 && newPassword === confirmPassword;

  const handleSubmit = () => {
    if (!canSubmit) {
      Alert.alert('Invalid Input', 'Passwords must match and be at least 8 characters.');
      return;
    }

    Alert.alert('Confirm', 'Are you sure you want to change your password?', [
      { text: 'No', style: 'cancel' },
      {
        text: 'Yes',
        style: 'destructive',
        onPress: async () => {
          try {
            setLoading(true);
            await usersService.changePassword(newPassword);
            Alert.alert('Success', 'Password changed successfully');
            router.back();
          } catch (e) {
            Alert.alert('Error', 'Failed to change password');
          } finally {
            setLoading(false);
          }
        },
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.form}>
        <View style={styles.card}>
          <Text style={styles.label}>New Password</Text>
          <TextInput
            value={newPassword}
            onChangeText={setNewPassword}
            secureTextEntry
            placeholder="Enter new password"
            style={styles.input}
            placeholderTextColor="#888"
          />
        </View>
        <View style={styles.card}>
          <Text style={styles.label}>Confirm Password</Text>
          <TextInput
            value={confirmPassword}
            onChangeText={setConfirmPassword}
            secureTextEntry
            placeholder="Confirm new password"
            style={styles.input}
            placeholderTextColor="#888"
          />
        </View>
        <Pressable style={[styles.submitButton, !canSubmit && styles.submitButtonDisabled]} onPress={handleSubmit} disabled={!canSubmit || loading}>
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.submitText}>Submit</Text>
          )}
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  header: {
    paddingHorizontal: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderColor: '#eee',
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#030213',
  },
  form: {
    padding: 16,
  },
  card: {
    borderWidth: 1,
    borderColor: '#eee',
    borderRadius: 12,
    padding: 12,
    backgroundColor: '#fff',
    marginBottom: 12,
  },
  label: {
    color: '#030213',
    fontSize: 16,
    fontWeight: '500',
    marginBottom: 8,
  },
  input: {
    fontSize: 16,
    paddingVertical: 10,
    color: '#030213',
  },
  submitButton: {
    marginTop: 8,
    paddingVertical: 12,
    borderRadius: 12,
    alignItems: 'center',
    backgroundColor: '#000',
  },
  submitButtonDisabled: {
    backgroundColor: '#000',
    opacity: 0.5,
  },
  submitText: {
    color: '#fff',
    fontWeight: '600',
  },
});
