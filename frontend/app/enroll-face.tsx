import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet, Alert, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { Ionicons } from '@expo/vector-icons';
import { ThemedView } from '@/components/themed-view';
import { enrollmentService } from '@/services/enrollment-service';
import { useAuthStore } from '@/stores/auth-store';

export default function EnrollFaceScreen() {
  const router = useRouter();
  const setNeedsFaceEnrollment = useAuthStore((state) => state.setNeedsFaceEnrollment);
  const [isEnrolling, setIsEnrolling] = useState(false);
  const [enrollmentStatus, setEnrollmentStatus] = useState<string | null>(null);

  const navigateToHome = () => {
    setNeedsFaceEnrollment(false);
    router.replace('/');
  };

  const handleTakePhoto = async () => {
    try {
      const { status } = await ImagePicker.requestCameraPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert(
          'Permission Required',
          'Camera access is needed to take your face signature photo.'
        );
        return;
      }

      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: 'images',
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.8,
        cameraType: ImagePicker.CameraType.front,
      });

      if (result.canceled || !result.assets?.[0]?.uri) {
        return;
      }

      await performEnrollment(result.assets[0].uri);
    } catch (e) {
      console.error('Error launching camera:', e);
      Alert.alert('Error', 'Failed to open camera. Please try again.');
    }
  };

  const performEnrollment = async (imageUri: string) => {
    setIsEnrolling(true);
    setEnrollmentStatus('Starting enrollment...');

    try {
      const result = await enrollmentService.enrollFace(imageUri, (step) => {
        setEnrollmentStatus(step);
      });

      if (result.status === 'SUCCEEDED') {
        Alert.alert(
          'Success!',
          'Your face signature has been enrolled successfully. You can now be recognized for attendance.',
          [{ text: 'Continue', onPress: navigateToHome }]
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

  const handleSkip = () => {
    Alert.alert(
      'Skip Face Enrollment?',
      'You can enroll your face signature later from your profile. Without it, you won\'t be able to check in to classes.',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Skip for Now', onPress: navigateToHome },
      ]
    );
  };

  return (
    <ThemedView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.iconContainer}>
          <Ionicons name="scan" size={80} color="#000" />
        </View>

        <Text style={styles.title}>Set Up Face Signature</Text>
        <Text style={styles.subtitle}>
          Take a photo of your face to enable automatic attendance check-in. Make sure you're in a well-lit area and your face is clearly visible.
        </Text>

        <View style={styles.tipsContainer}>
          <Text style={styles.tipsTitle}>Tips for a good photo:</Text>
          <View style={styles.tipRow}>
            <Ionicons name="sunny-outline" size={20} color="#666" />
            <Text style={styles.tipText}>Good lighting on your face</Text>
          </View>
          <View style={styles.tipRow}>
            <Ionicons name="person-outline" size={20} color="#666" />
            <Text style={styles.tipText}>Face the camera directly</Text>
          </View>
          <View style={styles.tipRow}>
            <Ionicons name="close-circle-outline" size={20} color="#666" />
            <Text style={styles.tipText}>No sunglasses or face coverings</Text>
          </View>
        </View>

        <Pressable
          style={[styles.primaryButton, isEnrolling && styles.primaryButtonDisabled]}
          onPress={handleTakePhoto}
          disabled={isEnrolling}
        >
          {isEnrolling ? (
            <View style={styles.enrollingContainer}>
              <ActivityIndicator size="small" color="#fff" />
              <Text style={styles.primaryButtonText}>{enrollmentStatus || 'Enrolling...'}</Text>
            </View>
          ) : (
            <>
              <Ionicons name="camera" size={20} color="#fff" />
              <Text style={styles.primaryButtonText}>Take Photo</Text>
            </>
          )}
        </Pressable>

        <Pressable style={styles.skipButton} onPress={handleSkip} disabled={isEnrolling}>
          <Text style={styles.skipButtonText}>Skip for Now</Text>
        </Pressable>
      </View>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
    alignItems: 'center',
  },
  iconContainer: {
    width: 140,
    height: 140,
    borderRadius: 70,
    backgroundColor: '#f3f3f3',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#030213',
    textAlign: 'center',
    marginBottom: 12,
  },
  subtitle: {
    fontSize: 16,
    color: '#717182',
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 32,
  },
  tipsContainer: {
    width: '100%',
    backgroundColor: '#f9f9f9',
    borderRadius: 12,
    padding: 16,
    marginBottom: 32,
  },
  tipsTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#030213',
    marginBottom: 12,
  },
  tipRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 8,
  },
  tipText: {
    fontSize: 14,
    color: '#666',
  },
  primaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    width: '100%',
    paddingVertical: 16,
    backgroundColor: '#000',
    borderRadius: 12,
  },
  primaryButtonDisabled: {
    backgroundColor: '#666',
  },
  primaryButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 16,
  },
  enrollingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  skipButton: {
    marginTop: 16,
    paddingVertical: 12,
  },
  skipButtonText: {
    color: '#717182',
    fontSize: 16,
  },
});
