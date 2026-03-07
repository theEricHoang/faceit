import React, { useRef, useState } from 'react';
import { View, Text, Pressable, StyleSheet, SafeAreaView, Alert } from 'react-native';
import { CameraView, useCameraPermissions, type CameraType } from 'expo-camera';
import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useAttendancePhotoStore } from '@/stores/attendance-photo-store';

export default function TakeAttendanceScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ id: string }>();
  const cameraRef = useRef<CameraView>(null);
  const [facing, setFacing] = useState<CameraType>('back');
  const [capturing, setCapturing] = useState(false);
  const [permission, requestPermission] = useCameraPermissions();

  const photos = useAttendancePhotoStore((state) => state.photos);
  const addPhoto = useAttendancePhotoStore((state) => state.addPhoto);
  const clearPhotos = useAttendancePhotoStore((state) => state.clearPhotos);

  // Clear photos when first entering the camera flow
  const hasCleared = useRef(false);
  if (!hasCleared.current) {
    clearPhotos();
    hasCleared.current = true;
  }

  const handleCapture = async () => {
    if (!cameraRef.current || capturing) return;
    setCapturing(true);
    try {
      const photo = await cameraRef.current.takePictureAsync({ quality: 0.8 });
      if (photo?.uri) {
        addPhoto(photo.uri);
      }
    } catch (e: any) {
      console.warn('Failed to capture photo:', e?.message || e);
    } finally {
      setCapturing(false);
    }
  };

  const handleFlipCamera = () => {
    setFacing((prev) => (prev === 'back' ? 'front' : 'back'));
  };

  const handleClose = () => {
    if (photos.length > 0) {
      Alert.alert(
        'Discard Photos?',
        `You have ${photos.length} photo${photos.length > 1 ? 's' : ''} captured. Discard and go back?`,
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Discard',
            style: 'destructive',
            onPress: () => {
              clearPhotos();
              router.back();
            },
          },
        ],
      );
    } else {
      router.back();
    }
  };

  const handleReview = () => {
    router.push(`/class/${params.id}/review-photos`);
  };

  // Permission not yet determined
  if (!permission) {
    return (
      <View style={styles.centeredContainer}>
        <Text style={styles.permissionText}>Loading camera...</Text>
      </View>
    );
  }

  // Permission denied
  if (!permission.granted) {
    return (
      <SafeAreaView style={styles.centeredContainer}>
        <Ionicons name="camera-outline" size={64} color="#888" style={{ marginBottom: 16 }} />
        <Text style={styles.permissionTitle}>Camera Permission Required</Text>
        <Text style={styles.permissionText}>
          FaceIT needs camera access to capture attendance photos for your class.
        </Text>
        <Pressable style={styles.permissionButton} onPress={requestPermission}>
          <Text style={styles.permissionButtonText}>Grant Camera Access</Text>
        </Pressable>
        <Pressable style={styles.secondaryButton} onPress={() => router.back()}>
          <Text style={styles.secondaryButtonText}>Go Back</Text>
        </Pressable>
      </SafeAreaView>
    );
  }

  return (
    <View style={styles.container}>
      <CameraView ref={cameraRef} style={styles.camera} facing={facing}>
        {/* Top bar */}
        <SafeAreaView style={styles.topBar}>
          <Pressable style={styles.topButton} onPress={handleClose}>
            <Ionicons name="close" size={28} color="#fff" />
          </Pressable>
          <View style={styles.photoCountBadge}>
            <Ionicons name="images-outline" size={16} color="#fff" />
            <Text style={styles.photoCountText}>
              {photos.length} photo{photos.length !== 1 ? 's' : ''}
            </Text>
          </View>
          <Pressable style={styles.topButton} onPress={handleFlipCamera}>
            <Ionicons name="camera-reverse-outline" size={28} color="#fff" />
          </Pressable>
        </SafeAreaView>

        {/* Bottom bar */}
        <SafeAreaView style={styles.bottomBar}>
          {/* Review button (left) */}
          <Pressable
            style={[styles.reviewButton, photos.length === 0 && styles.disabledButton]}
            onPress={handleReview}
            disabled={photos.length === 0}
          >
            <Ionicons name="checkmark-circle-outline" size={20} color="#fff" />
            <Text style={styles.reviewButtonText}>Review</Text>
          </Pressable>

          {/* Shutter button (center) */}
          <Pressable
            style={[styles.shutterButton, capturing && styles.shutterButtonCapturing]}
            onPress={handleCapture}
            disabled={capturing}
          >
            <View style={styles.shutterInner} />
          </Pressable>

          {/* Spacer for layout balance (right) */}
          <View style={{ minWidth: 100 }} />
        </SafeAreaView>
      </CameraView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  camera: {
    flex: 1,
  },
  centeredContainer: {
    flex: 1,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
  },
  permissionTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#030213',
    marginBottom: 8,
    textAlign: 'center',
  },
  permissionText: {
    fontSize: 16,
    color: '#717182',
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 22,
  },
  permissionButton: {
    paddingVertical: 14,
    paddingHorizontal: 24,
    backgroundColor: '#000',
    borderRadius: 12,
    marginBottom: 12,
  },
  permissionButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 16,
  },
  secondaryButton: {
    paddingVertical: 12,
    paddingHorizontal: 24,
  },
  secondaryButtonText: {
    color: '#717182',
    fontWeight: '500',
    fontSize: 16,
  },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 8,
    marginLeft: 6,
    marginRight: 6,
  },
  topButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(0,0,0,0.4)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  photoCountBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(0,0,0,0.5)',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 16,
  },
  photoCountText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  bottomBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingBottom: 24,
  },
  shutterButton: {
    width: 76,
    height: 76,
    borderRadius: 38,
    backgroundColor: 'rgba(255,255,255,0.3)',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 4,
    borderColor: '#fff',
  },
  shutterButtonCapturing: {
    opacity: 0.5,
  },
  shutterInner: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#fff',
  },
  reviewButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: 'rgba(0,0,0,0.5)',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 20,
    minWidth: 100,
    marginLeft: 4,
  },
  reviewButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  disabledButton: {
    opacity: 0.4,
  },
});
