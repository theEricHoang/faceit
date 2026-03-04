import React, { useState } from 'react';
import {
  View,
  Text,
  Pressable,
  StyleSheet,
  ScrollView,
  Alert,
  Dimensions,
  ActivityIndicator,
} from 'react-native';
import { Image } from 'expo-image';
import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useAttendancePhotoStore } from '@/stores/attendance-photo-store';
import { getAttendanceUploadUrl, uploadPhotoToS3 } from '@/services/classes-service';

const SCREEN_WIDTH = Dimensions.get('window').width;
const THUMBNAIL_GAP = 8;
const THUMBNAIL_PADDING = 16;
const THUMBNAILS_PER_ROW = 3;
const THUMBNAIL_SIZE =
  (SCREEN_WIDTH - THUMBNAIL_PADDING * 2 - THUMBNAIL_GAP * (THUMBNAILS_PER_ROW - 1)) / THUMBNAILS_PER_ROW;

export default function ReviewPhotosScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ id: string }>();
  const photos = useAttendancePhotoStore((state) => state.photos);
  const removePhoto = useAttendancePhotoStore((state) => state.removePhoto);
  const clearPhotos = useAttendancePhotoStore((state) => state.clearPhotos);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({ current: 0, total: 0 });

  const handleAddMore = () => {
    router.back();
  };

  const handleSubmit = async () => {
    if (photos.length === 0 || !params.id) return;

    setUploading(true);
    setUploadProgress({ current: 0, total: photos.length });

    try {
      for (let i = 0; i < photos.length; i++) {
        setUploadProgress({ current: i + 1, total: photos.length });

        // 1. Get a presigned upload URL from the backend
        const { upload_url } = await getAttendanceUploadUrl(params.id);

        // 2. Upload the photo directly to S3
        await uploadPhotoToS3(upload_url, photos[i]);
      }

      const count = photos.length;
      clearPhotos();
      Alert.alert(
        'Photos Submitted',
        `${count} photo${count > 1 ? 's' : ''} uploaded for attendance.`,
        [{ text: 'OK', onPress: () => router.dismiss(2) }],
      );
    } catch (e: any) {
      Alert.alert('Upload Failed', e?.message || 'Failed to upload photos. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleRemovePhoto = (uri: string) => {
    removePhoto(uri);
    // If all photos removed, go back to camera
    if (photos.length <= 1) {
      router.back();
    }
  };

  return (
    <View style={styles.container}>
      {/* Header summary */}
      <View style={styles.header}>
        <View style={styles.headerBadge}>
          <Ionicons name="images-outline" size={18} color="#030213" />
          <Text style={styles.headerBadgeText}>
            {photos.length} photo{photos.length !== 1 ? 's' : ''} ready
          </Text>
        </View>
        <Text style={styles.headerSubtext}>Tap the X on a photo to remove it</Text>
      </View>

      {/* Photo grid */}
      <ScrollView contentContainerStyle={styles.grid}>
        {photos.map((uri, index) => (
          <View key={uri} style={styles.thumbnailContainer}>
            <Image source={{ uri }} style={styles.thumbnail} contentFit="cover" />
            <Pressable
              style={styles.removeButton}
              onPress={() => handleRemovePhoto(uri)}
              hitSlop={8}
            >
              <Ionicons name="close-circle" size={24} color="#dc2626" />
            </Pressable>
            <View style={styles.photoIndex}>
              <Text style={styles.photoIndexText}>{index + 1}</Text>
            </View>
          </View>
        ))}
      </ScrollView>

      {/* Upload progress overlay */}
      {uploading && (
        <View style={styles.uploadOverlay}>
          <View style={styles.uploadCard}>
            <ActivityIndicator size="large" color="#000" />
            <Text style={styles.uploadText}>
              Uploading {uploadProgress.current} of {uploadProgress.total}...
            </Text>
          </View>
        </View>
      )}

      {/* Bottom actions */}
      <View style={styles.bottomBar}>
        <Pressable style={styles.addMoreButton} onPress={handleAddMore} disabled={uploading}>
          <Ionicons name="camera-outline" size={20} color="#030213" />
          <Text style={styles.addMoreText}>Add More</Text>
        </Pressable>
        <Pressable
          style={[styles.submitButton, (photos.length === 0 || uploading) && styles.disabledButton]}
          onPress={handleSubmit}
          disabled={photos.length === 0 || uploading}
        >
          <Ionicons name="cloud-upload-outline" size={20} color="#fff" />
          <Text style={styles.submitButtonText}>Submit</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  header: {
    paddingHorizontal: THUMBNAIL_PADDING,
    paddingTop: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderColor: '#eee',
  },
  headerBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  headerBadgeText: {
    fontSize: 18,
    fontWeight: '700',
    color: '#030213',
  },
  headerSubtext: {
    fontSize: 14,
    color: '#717182',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: THUMBNAIL_PADDING,
    gap: THUMBNAIL_GAP,
  },
  thumbnailContainer: {
    width: THUMBNAIL_SIZE,
    height: THUMBNAIL_SIZE,
    borderRadius: 12,
    overflow: 'hidden',
    position: 'relative',
  },
  thumbnail: {
    width: '100%',
    height: '100%',
    borderRadius: 12,
  },
  removeButton: {
    position: 'absolute',
    top: 4,
    right: 4,
    backgroundColor: 'rgba(255,255,255,0.9)',
    borderRadius: 12,
  },
  photoIndex: {
    position: 'absolute',
    bottom: 4,
    left: 4,
    backgroundColor: 'rgba(0,0,0,0.6)',
    borderRadius: 10,
    width: 20,
    height: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  photoIndexText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '700',
  },
  uploadOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(255,255,255,0.85)',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 10,
  },
  uploadCard: {
    alignItems: 'center',
    gap: 12,
    padding: 32,
    backgroundColor: '#fff',
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 5,
  },
  uploadText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#030213',
  },
  bottomBar: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 32,
    gap: 12,
    borderTopWidth: 1,
    borderColor: '#eee',
  },
  addMoreButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 14,
    backgroundColor: '#f3f3f3',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#eee',
  },
  addMoreText: {
    fontWeight: '600',
    fontSize: 16,
    color: '#030213',
  },
  submitButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 14,
    backgroundColor: '#000',
    borderRadius: 12,
  },
  submitButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 16,
  },
  disabledButton: {
    opacity: 0.4,
  },
});
