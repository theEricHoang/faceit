import React, { useEffect, useMemo, useState } from 'react';
import { View, Text, Pressable, StyleSheet, ScrollView, Modal, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { getClassDetails, withdrawFromClass, type ClassDetailResponse } from '@/services/classes-service';
import { useAuthStore } from '@/stores/auth-store';

const MOCK_STUDENT_ATTENDANCE_RECORDS = [
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

const MOCK_INSTRUCTOR_SESSIONS = [
  { date: '2025-09-29', presentCount: 38, totalStudents: 50 },
  { date: '2025-10-02', presentCount: 41, totalStudents: 50 },
  { date: '2025-10-04', presentCount: 43, totalStudents: 50 },
  { date: '2025-10-06', presentCount: 39, totalStudents: 50 },
  { date: '2025-10-09', presentCount: 42, totalStudents: 50 },
  { date: '2025-10-11', presentCount: 44, totalStudents: 50 },
  { date: '2025-10-13', presentCount: 40, totalStudents: 50 },
  { date: '2025-10-16', presentCount: 46, totalStudents: 50 },
  { date: '2025-10-18', presentCount: 41, totalStudents: 50 },
  { date: '2025-10-20', presentCount: 45, totalStudents: 50 },
];

type TrendChartPoint = {
  date: string;
  percentage: number;
};

function AttendanceTrendChart({ points }: { points: TrendChartPoint[] }) {
  const [plotWidth, setPlotWidth] = useState(240);
  const chartHeight = 140;
  const paddingX = 14;
  const paddingY = 16;
  const innerWidth = Math.max(plotWidth - paddingX * 2, 1);
  const innerHeight = chartHeight - paddingY * 2;
  const axisLabels = [100, 75, 50, 25];
  const visibleDateIndexes =
    points.length <= 5 ? points.map((_, index) => index) : [0, 2, 4, 6, points.length - 1];

  const pointPositions = points.map((point, index) => {
    const x = points.length === 1 ? plotWidth / 2 : paddingX + (index / (points.length - 1)) * innerWidth;
    const y = paddingY + ((100 - point.percentage) / 100) * innerHeight;
    return { ...point, x, y };
  });

  return (
    <View style={styles.chartCard}>
      <View style={styles.chartHeaderRow}>
        <View>
          <Text style={styles.cardTitle}>Attendance Trend</Text>
          <Text style={styles.helperText}>Percent of enrolled students present per session</Text>
        </View>
      </View>

      <View style={styles.chartWrapper}>
        <View style={styles.chartGrid}>
          {axisLabels.map((label) => (
            <View key={label} style={styles.chartGridLineRow}>
              <Text style={styles.chartAxisLabel}>{label}%</Text>
              <View style={styles.chartGridLine} />
            </View>
          ))}
        </View>

        <View style={styles.chartPlotArea} onLayout={(event) => setPlotWidth(event.nativeEvent.layout.width)}>
          {pointPositions.slice(0, -1).map((point, index) => {
            const nextPoint = pointPositions[index + 1];
            const dx = nextPoint.x - point.x;
            const dy = nextPoint.y - point.y;
            const length = Math.sqrt(dx * dx + dy * dy);
            const angle = `${Math.atan2(dy, dx)}rad`;

            return (
              <View
                key={`${point.date}-${nextPoint.date}`}
                style={[
                  styles.chartLineSegment,
                  {
                    width: length,
                    left: point.x,
                    top: point.y,
                    transform: [{ rotate: angle }],
                  },
                ]}
              />
            );
          })}

          {pointPositions.map((point) => (
            <View key={point.date} style={[styles.chartPoint, { left: point.x - 5, top: point.y - 5 }]} />
          ))}
        </View>
      </View>

      <View style={styles.chartLabelsRow}>
        <View style={styles.chartLabelsSpacer} />
        <View style={[styles.chartLabelsTrack, { width: plotWidth }]}> 
          {pointPositions.map((point, index) => {
            if (!visibleDateIndexes.includes(index)) {
              return null;
            }

            return (
              <Text
                key={point.date}
                style={[
                  styles.chartDateLabel,
                  {
                    left: point.x - 18,
                  },
                ]}
              >
                {new Date(point.date).toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' })}
              </Text>
            );
          })}
        </View>
      </View>
    </View>
  );
}

export default function ClassDetailsScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ id: string }>();
  const user = useAuthStore((state) => state.user);
  const isInstructor = user?.type === 'instructor';
  const [details, setDetails] = useState<ClassDetailResponse | null>(null);
  const [withdrawDialogOpen, setWithdrawDialogOpen] = useState(false);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        if (params.id) {
          const res = await getClassDetails(String(params.id));
          if (mounted) setDetails(res);
        }
      } catch (e: any) {
        console.warn('Failed to fetch class details', e?.message || e);
      }
    })();
    return () => { mounted = false; };
  }, [params.id]);

  const presentCount = useMemo(() => MOCK_STUDENT_ATTENDANCE_RECORDS.filter(r => r.status === 'present').length, []);
  const totalSessions = MOCK_STUDENT_ATTENDANCE_RECORDS.length;
  const attendanceRate = Math.round((presentCount / totalSessions) * 100);

  const instructorSummary = useMemo(() => {
    const totalStudents = MOCK_INSTRUCTOR_SESSIONS[0]?.totalStudents ?? 0;
    const averagePresentCount = Math.round(
      MOCK_INSTRUCTOR_SESSIONS.reduce((sum, session) => sum + session.presentCount, 0) / MOCK_INSTRUCTOR_SESSIONS.length,
    );
    const classAttendanceRate = totalStudents === 0 ? 0 : Math.round((averagePresentCount / totalStudents) * 100);
    const lastSession = MOCK_INSTRUCTOR_SESSIONS[MOCK_INSTRUCTOR_SESSIONS.length - 1];

    return {
      totalStudents,
      averagePresentCount,
      classAttendanceRate,
      lastSessionRate: lastSession ? Math.round((lastSession.presentCount / lastSession.totalStudents) * 100) : 0,
    };
  }, []);

  const instructorTrendData = useMemo(
    () =>
      MOCK_INSTRUCTOR_SESSIONS.map((session) => ({
        date: session.date,
        percentage: Math.round((session.presentCount / session.totalStudents) * 100),
      })),
    [],
  );

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

        {/* Take Attendance (Instructor only) */}
        {isInstructor && (
          <>
            <Pressable
              style={styles.takeAttendanceButton}
              onPress={() => {
                router.push(`/class/${params.id}/take-attendance`);
              }}
            >
              <Ionicons name="camera-outline" size={20} color="#fff" style={{ marginRight: 8 }} />
              <Text style={styles.primaryButtonText}>Take Attendance</Text>
            </Pressable>

            <View style={styles.card}>
              <View style={styles.sectionHeaderRow}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  <Ionicons name="analytics-outline" size={18} color="#000" />
                  <Text style={styles.cardTitle}>Class Attendance Summary</Text>
                </View>
              </View>

              <View style={styles.instructorHeroStat}>
                <Text style={styles.instructorHeroValue}>{instructorSummary.classAttendanceRate}%</Text>
                <Text style={styles.helperText}>Overall class attendance rate</Text>
              </View>

              <View style={styles.instructorStatsRow}>
                <View style={styles.statBox}>
                  <Text style={styles.statLabel}>Average students present</Text>
                  <Text style={styles.valueText}>
                    {instructorSummary.averagePresentCount}/{instructorSummary.totalStudents}
                  </Text>
                </View>
                <View style={styles.statBox}>
                  <Text style={styles.statLabel}>Last session attendance</Text>
                  <Text style={styles.valueText}>{instructorSummary.lastSessionRate}%</Text>
                </View>
              </View>
            </View>

            <AttendanceTrendChart points={instructorTrendData} />

            <View style={styles.card}>
              <View style={styles.breakdownHeader}>
                <View>
                  <Text style={styles.cardTitle}>Session History</Text>
                  <Text style={styles.helperText}>Review attendance by class meeting</Text>
                </View>
                <Pressable style={[styles.secondaryActionButton, styles.disabledActionButton, styles.reportButton]} disabled>
                  <Ionicons name="document-text-outline" size={16} color="#8a8a97" />
                  <Text style={styles.disabledActionText}>View Attendance Report</Text>
                </Pressable>
              </View>

              <View style={styles.breakdownList}>
                {[...MOCK_INSTRUCTOR_SESSIONS].reverse().map((session) => {
                  const sessionAttendanceRate = Math.round((session.presentCount / session.totalStudents) * 100);

                  return (
                    <View key={session.date} style={styles.sessionCard}>
                      <View style={styles.sessionRowTop}>
                        <View>
                          <Text style={styles.valueText}>{formatDate(session.date)}</Text>
                          <Text style={styles.helperText}>
                            {session.presentCount}/{session.totalStudents} students present
                          </Text>
                        </View>
                        <View style={styles.sessionPercentageBadge}>
                          <Text style={styles.sessionPercentageText}>{sessionAttendanceRate}%</Text>
                        </View>
                      </View>

                      <Pressable style={[styles.outlineButton, styles.disabledOutlineButton]} disabled>
                        <Text style={styles.disabledOutlineButtonText}>View Details</Text>
                      </Pressable>
                    </View>
                  );
                })}
              </View>
            </View>
          </>
        )}

        {!isInstructor && (
          <>
            {/* Attendance Summary */}
            <View style={styles.card}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <Ionicons name="trending-up-outline" size={18} color="#000" />
                <Text style={styles.cardTitle}>Attendance Summary</Text>
              </View>
              <View style={{ alignItems: 'center', justifyContent: 'center', paddingVertical: 8 }}>
                <View style={{ width: 160, height: 160, alignItems: 'center', justifyContent: 'center' }}>
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
              {MOCK_STUDENT_ATTENDANCE_RECORDS.map((record, i) => (
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
          </>
        )}

        {/* Withdraw Button (Student only) */}
        {!isInstructor && (
          <Pressable style={[styles.primaryButton, styles.destructiveButton, { marginTop: 16 }]} onPress={() => setWithdrawDialogOpen(true)}>
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <Ionicons name="log-out-outline" size={18} color="#fff" style={{ marginRight: 8 }} />
              <Text style={styles.primaryButtonText}>Withdraw from Class</Text>
            </View>
          </Pressable>
        )}

        {/* Withdraw Confirmation Dialog (Student only) */}
        <Modal visible={withdrawDialogOpen} transparent animationType="fade" onRequestClose={() => setWithdrawDialogOpen(false)}>
          <Pressable style={styles.menuOverlay} onPress={() => setWithdrawDialogOpen(false)}>
            <View style={styles.menuContainer}>
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>Are you sure you want to withdraw from class?</Text>
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
  helperText: { color: '#717182', fontSize: 13, lineHeight: 18 },
  sectionTitle: { fontSize: 18, fontWeight: '600', color: '#030213' },
  sectionHeaderRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 12,
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
  },
  badge: {
    borderRadius: 8,
    paddingVertical: 4,
    paddingHorizontal: 8,
  },
  badgeText: { color: '#fff', fontWeight: '600' },
  badgeSuccess: { backgroundColor: '#16a34a' },
  badgeDestructive: { backgroundColor: '#dc2626' },
  statBox: { flex: 1, backgroundColor: '#f3f3f3', borderRadius: 10, padding: 12, gap: 4 },
  statLabel: { color: '#717182', fontSize: 13, fontWeight: '500' },
  primaryButton: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: '#000',
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  outlineButton: {
    borderWidth: 1,
    borderColor: '#d4d4da',
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  secondaryActionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderWidth: 1,
    borderColor: '#d4d4da',
    borderRadius: 999,
    paddingVertical: 9,
    paddingHorizontal: 12,
  },
  disabledActionButton: {
    backgroundColor: '#f3f4f6',
    borderColor: '#e4e4e7',
  },
  disabledActionText: {
    color: '#8a8a97',
    fontSize: 13,
    fontWeight: '600',
  },
  disabledOutlineButton: {
    backgroundColor: '#f8f8f9',
    borderColor: '#e4e4e7',
  },
  disabledOutlineButtonText: {
    color: '#8a8a97',
    fontWeight: '600',
  },
  destructiveButton: {
    backgroundColor: '#dc2626',
  },
  takeAttendanceButton: {
    flexDirection: 'row',
    paddingVertical: 14,
    paddingHorizontal: 16,
    backgroundColor: '#000',
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  instructorHeroStat: {
    paddingVertical: 8,
    alignItems: 'center',
    gap: 4,
  },
  instructorHeroValue: {
    color: '#030213',
    fontSize: 40,
    fontWeight: '700',
  },
  instructorStatsRow: {
    flexDirection: 'row',
    gap: 12,
  },
  chartCard: {
    borderWidth: 1,
    borderColor: '#eee',
    borderRadius: 12,
    padding: 12,
    backgroundColor: '#fff',
    gap: 12,
  },
  chartHeaderRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  chartWrapper: {
    flexDirection: 'row',
    gap: 8,
    minHeight: 140,
  },
  chartGrid: {
    width: 38,
    justifyContent: 'space-between',
    paddingVertical: 6,
  },
  chartGridLineRow: {
    flex: 1,
    justifyContent: 'space-between',
  },
  chartAxisLabel: {
    color: '#8a8a97',
    fontSize: 11,
  },
  chartGridLine: {
    height: 1,
    backgroundColor: '#ececf2',
    marginTop: 6,
  },
  chartPlotArea: {
    flex: 1,
    height: 140,
    borderRadius: 12,
    backgroundColor: '#fafafa',
    position: 'relative',
  },
  chartLineSegment: {
    position: 'absolute',
    height: 2,
    backgroundColor: '#2563eb',
  },
  chartPoint: {
    position: 'absolute',
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#2563eb',
    borderWidth: 2,
    borderColor: '#fff',
  },
  chartLabelsRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  chartLabelsSpacer: {
    width: 38,
  },
  chartLabelsTrack: {
    height: 18,
    position: 'relative',
  },
  chartDateLabel: {
    position: 'absolute',
    width: 36,
    color: '#8a8a97',
    fontSize: 10,
    textAlign: 'center',
  },
  breakdownList: {
    gap: 10,
  },
  breakdownHeader: {
    gap: 10,
    marginBottom: 4,
  },
  reportButton: {
    alignSelf: 'flex-start',
  },
  sessionCard: {
    borderWidth: 1,
    borderColor: '#ececf2',
    borderRadius: 12,
    padding: 12,
    gap: 12,
    backgroundColor: '#fcfcfd',
  },
  sessionRowTop: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  sessionPercentageBadge: {
    backgroundColor: '#e9f7ee',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 999,
  },
  sessionPercentageText: {
    color: '#15803d',
    fontSize: 14,
    fontWeight: '700',
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
});
