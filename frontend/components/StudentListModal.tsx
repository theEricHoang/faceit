import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  Modal,
  ScrollView,
  StyleSheet,
  Pressable,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { StudentEnrollmentItem } from '@/services/classes-service';

type StudentListModalProps = {
  visible: boolean;
  classId: string;
  courseName: string;
  courseCode: string;
  section: string;
  students: StudentEnrollmentItem[];
  isLoading: boolean;
  error: string | null;
  onClose: () => void;
  onRetry?: () => void;
};

export default function StudentListModal({
  visible,
  classId,
  courseName,
  courseCode,
  section,
  students,
  isLoading,
  error,
  onClose,
  onRetry,
}: StudentListModalProps) {
  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <View style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <Pressable onPress={onClose} style={styles.closeButton}>
            <Ionicons name="close" size={24} color="#000" />
          </Pressable>
          <View style={styles.headerContent}>
            <Text style={styles.headerTitle}>{courseCode} - Section {section}</Text>
            {courseName && <Text style={styles.headerSubtitle}>{courseName}</Text>}
          </View>
          <View style={{ width: 40 }} />
        </View>

        {/* Content */}
        <ScrollView style={styles.content} contentContainerStyle={styles.contentContainer}>
          <Text style={styles.sectionTitle}>Enrolled Students ({students.length})</Text>

          {/* Loading state */}
          {isLoading && (
            <View style={styles.centerContainer}>
              <ActivityIndicator size="large" color="#000" />
            </View>
          )}

          {/* Error state */}
          {error && !isLoading && (
            <View style={styles.centerContainer}>
              <Text style={styles.errorText}>{error}</Text>
              {onRetry && (
                <Pressable style={styles.retryButton} onPress={onRetry}>
                  <Text style={styles.retryText}>Retry</Text>
                </Pressable>
              )}
            </View>
          )}

          {/* Empty state */}
          {!isLoading && !error && students.length === 0 && (
            <View style={styles.centerContainer}>
              <Text style={styles.emptyText}>No students enrolled yet</Text>
            </View>
          )}

          {/* Student list */}
          {!isLoading &&
            !error &&
            students.map((student) => (
              <View key={student.user_id} style={styles.studentCard}>
                <View style={styles.studentAvatar}>
                  <Text style={styles.studentAvatarText}>
                    {student.first_name[0]?.toUpperCase() || 'S'}
                    {student.last_name[0]?.toUpperCase() || 'T'}
                  </Text>
                </View>
                <View style={styles.studentInfo}>
                  <Text style={styles.studentName}>
                    {student.first_name} {student.last_name}
                  </Text>
                  <Text style={styles.studentEmail}>{student.email}</Text>
                </View>
              </View>
            ))}
        </ScrollView>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  closeButton: {
    padding: 8,
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerContent: {
    flex: 1,
    marginHorizontal: 12,
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 2,
  },
  headerSubtitle: {
    fontSize: 13,
    color: '#666',
  },
  content: {
    flex: 1,
  },
  contentContainer: {
    padding: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 16,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: 200,
  },
  errorText: {
    color: '#e53935',
    fontSize: 14,
    marginBottom: 12,
    textAlign: 'center',
  },
  retryButton: {
    backgroundColor: '#e53935',
    paddingHorizontal: 24,
    paddingVertical: 8,
    borderRadius: 6,
  },
  retryText: {
    color: '#fff',
    fontWeight: '600',
  },
  emptyText: {
    color: '#888',
    fontSize: 14,
    textAlign: 'center',
  },
  studentCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f9f9f9',
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
  },
  studentAvatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  studentAvatarText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  studentInfo: {
    flex: 1,
  },
  studentName: {
    fontSize: 15,
    fontWeight: '500',
    marginBottom: 4,
  },
  studentEmail: {
    fontSize: 13,
    color: '#666',
  },
});
