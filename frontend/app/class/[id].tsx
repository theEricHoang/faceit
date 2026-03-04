import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { View, Text, Pressable, StyleSheet, ScrollView, Modal, Alert, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { getClassDetails, withdrawFromClass, getClassStudents, type ClassDetailResponse, type StudentEnrollmentItem } from '@/services/classes-service';
import { useAuthStore } from '@/stores/auth-store';

const MOCK_ATTENDANCE_RECORDS = [
  { date: '2025-10-20', status: 'present' as const },
  { date: '2025-10-18', status: 'present' as const },
  { date: '2025-10-16', status: 'absent' as const },
  { date: '2025-10-13', status: 'present' as const },
  { date: '2025-10-11', status: 'present' as const },
  { date: '2025-10-09', status: 'present' as const },
  { date: '2025-10-06', status: 'absent' as const },
  { date: '2025-10-04', status: 'present' as const },
  { date: '2025-10-02', status: 'present' as const },
  { date: '2025-09-29', status: 'present' as const },
];

export default function StudentClassDetailsScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ id: string }>();
  const [details, setDetails] = useState<ClassDetailResponse | null>(null);
  const [withdrawDialogOpen, setWithdrawDialogOpen] = useState(false);

  // instructor-specific student list
  const [students, setStudents] = useState<StudentEnrollmentItem[]>([]);
  const [studentsLoading, setStudentsLoading] = useState(false);
  const [studentsError, setStudentsError] = useState<string | null>(null);

  const user = useAuthStore((state) => state.user);
  const role = user?.type ?? 'student';

  const fetchStudents = useCallback(async (classId: string) => {
    try {
      setStudentsError(null);
      setStudentsLoading(true);
      const res = await getClassStudents(classId);
      setStudents(res.students);
    } catch (e) {
      console.error('Failed to load students', e);
      setStudentsError('Failed to load students');
    } finally {
      setStudentsLoading(false);
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        if (params.id) {
          const res = await getClassDetails(String(params.id));
          if (mounted) setDetails(res);
          if (role === 'instructor') {
            await fetchStudents(String(params.id));
          }
        }
      } catch (e: any) {
        console.warn('Failed to fetch class details', e?.message || e);
      }
    })();
    return () => { mounted = false; };
  }, [params.id, role, fetchStudents]);

  const presentCount = useMemo(() => MOCK_ATTENDANCE_RECORDS.filter(r => r.status === 'present').length, []);
  const totalSessions = MOCK_ATTENDANCE_RECORDS.length;
  const attendanceRate = Math.round((presentCount / totalSessions) * 100);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        {/* Class Info */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Class Information</Text>
          <View style={{ gap: 8 }}>
            <View>
              <Text style={styles.labelText}>Instructor</Text>
              <Text style={styles.valueText}>{details?.instructor_name || '-'}</Text>
            </View>
            <View>
              <Text style={styles.labelText}>Schedule</Text>
              <Text style={styles.valueText}>{details?.schedule || '-'}</Text>
            </View>
            <View>
              <Text style={styles.labelText}>Location</Text>
              <Text style={styles.valueText}>{details?.room || '-'}</Text>
            </View>
          </View>
        </View>

        {/* Enrolled students for instructors */}
        {role === 'instructor' && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Enrolled Students ({students.length})</Text>

            {studentsLoading && (
              <View style={styles.centerContainer}>
                <ActivityIndicator size="large" color="#000" />
              </View>
            )}

            {studentsError && !studentsLoading && (
              <View style={styles.centerContainer}>
                <Text style={styles.errorText}>{studentsError}</Text>
                <Pressable style={styles.retryButton} onPress={() => params.id && fetchStudents(params.id)}>
                  <Text style={styles.retryText}>Retry</Text>
                </Pressable>
              </View>
            )}

            {!studentsLoading && !studentsError && students.length === 0 && (
              <View style={styles.centerContainer}>
                <Text style={styles.emptyText}>No students enrolled yet</Text>
              </View>
            )}

            {!studentsLoading && !studentsError && students.map((s) => (
              <View key={s.user_id} style={styles.studentCard}>
                <View style={styles.studentAvatar}>
                  <Text style={styles.studentAvatarText}>
                    {s.first_name[0]?.toUpperCase() || 'S'}{s.last_name[0]?.toUpperCase() || 'T'}
                  </Text>
                </View>
                <View style={styles.studentInfo}>
                  <Text style={styles.studentName}>{s.first_name} {s.last_name}</Text>
                  <Text style={styles.studentEmail}>{s.email}</Text>
                </View>
              </View>
            ))}
          </View>
        )}

        {/* Attendance Summary */}
        <View style={styles.card}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <Ionicons name="trending-up-outline" size={18} color="#000" />
            <Text style={styles.cardTitle}>Attendance Summary</Text>
          </View>
          <View style={{ alignItems: 'center', justifyContent: 'center', paddingVertical: 8 }}>
            <View style={{ width: 160, height: 160, alignItems: 'center', justifyContent: 'center' }}>
              {/* Simple ring using text (RN SVG omitted) */}
              <Text style={[styles.valueText, { fontSize: 24 }]}>{attendanceRate}%</Text>
              <Text style={styles.labelText}>Attendance</Text>
            </View>
          </View>
          <View style={{ flexDirection: 'row', gap: 12 }}>
            <View style={styles.statBox}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                <Ionicons name="checkmark-outline" size={16} color="#16a34a" />
                <Text style={{ color: '#16a34a' }}>Present</Text>
              </View>
              <Text style={styles.valueText}>{presentCount} sessions</Text>
            </View>
            <View style={styles.statBox}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                <Ionicons name="close-outline" size={16} color="#dc2626" />
                <Text style={{ color: '#dc2626' }}>Absent</Text>
              </View>
              <Text style={styles.valueText}>{totalSessions - presentCount} sessions</Text>
            </View>
          </View>
        </View>

        {/* Attendance History */}
        <View style={{ gap: 8 }}>
          <Text style={styles.sectionTitle}>Attendance History</Text>
          {MOCK_ATTENDANCE_RECORDS.map((record, i) => (
            <View key={i} style={styles.cardRow}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                <Ionicons name="calendar-outline" size={16} color="#888" />
                <Text style={styles.valueText}>{formatDate(record.date)}</Text>
              </View>
              <View style={[styles.badge, record.status === 'present' ? styles.badgeSuccess : styles.badgeDestructive]}>
                <Text style={[styles.badgeText]}>{record.status === 'present' ? 'Present' : 'Absent'}</Text>
              </View>
            </View>
          ))}
        </View>

        {/* Withdraw Button (students only) */}
        {role === 'student' && (
          <Pressable style={[styles.primaryButton, styles.destructiveButton, { marginTop: 16 }]} onPress={() => setWithdrawDialogOpen(true)}>
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <Ionicons name="log-out-outline" size={18} color="#fff" style={{ marginRight: 8 }} />
              <Text style={styles.primaryButtonText}>Withdraw from Class</Text>
            </View>
          </Pressable>
        )}

        {/* Withdraw Confirmation Dialog */}
        <Modal visible={withdrawDialogOpen} transparent animationType="fade" onRequestClose={() => setWithdrawDialogOpen(false)}>
          <Pressable style={styles.menuOverlay} onPress={() => setWithdrawDialogOpen(false)}>
            <View style={styles.menuContainer}>
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>Are you sure Withdrawing from class?</Text>
              </View>
              <View style={{ flexDirection: 'row', justifyContent: 'flex-end', gap: 8, padding: 16 }}>
                <Pressable
                  style={[styles.primaryButton, { backgroundColor: '#fff', borderWidth: 1, borderColor: '#eee' }]}
                  onPress={() => setWithdrawDialogOpen(false)}
                >
                  <Text style={[styles.primaryButtonText, { color: '#000' }]}>No</Text>
                </Pressable>
                <Pressable
                  style={[styles.primaryButton, styles.destructiveButton]}
                  onPress={async () => {
                    try {
                      if (params.id) {
                        await withdrawFromClass(String(params.id));
                        setWithdrawDialogOpen(false);
                        Alert.alert('Withdrawn', 'You have withdrawn from the class');
                        router.back();
                      }
                    } catch (e: any) {
                      const msg = e?.data?.detail || e?.message || 'Failed to withdraw';
                      Alert.alert('Error', msg);
                    }
                  }}
                >
                  <Text style={styles.primaryButtonText}>Yes</Text>
                </Pressable>
              </View>
            </View>
          </Pressable>
        </Modal>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
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
  title: { fontSize: 20, fontWeight: '700' },
  content: { padding: 16, flexGrow: 1, gap: 12 },
  card: {
    borderWidth: 1,
    borderColor: '#eee',
    borderRadius: 12,
    padding: 12,
    backgroundColor: '#fff',
    gap: 8,
  },
  cardTitle: { fontSize: 16, fontWeight: '600', color: '#030213' },
  labelText: { color: '#717182', fontSize: 16, fontWeight: '500' },
  valueText: { color: '#030213', fontSize: 16, fontWeight: '500' },
  sectionTitle: { fontSize: 18, fontWeight: '600', color: '#030213' },
  cardRow: {
    borderWidth: 1,
    borderColor: '#eee',
    borderRadius: 12,
    padding: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#fff',
  },
  badge: {
    borderRadius: 8,
    paddingVertical: 4,
    paddingHorizontal: 8,
  },
  badgeText: { color: '#fff', fontWeight: '600' },
  badgeSuccess: { backgroundColor: '#16a34a' },
  badgeDestructive: { backgroundColor: '#dc2626' },
  statBox: { flex: 1, backgroundColor: '#f3f3f3', borderRadius: 10, padding: 12 },
  primaryButton: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: '#000',
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  destructiveButton: {
    backgroundColor: '#dc2626',
  },
  primaryButtonText: { color: '#fff', fontWeight: '600' },
  menuOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  menuContainer: {
    backgroundColor: '#fff',
    borderRadius: 12,
    width: '90%',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 5,
  },
  modalHeader: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderColor: '#eee',
  },
  modalTitle: { fontSize: 18, fontWeight: '600' },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: 120,
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
