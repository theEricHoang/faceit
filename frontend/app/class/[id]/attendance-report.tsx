import React, { useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import * as FileSystem from 'expo-file-system/legacy';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';
import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import {
  getAttendanceSessionPdfResponse,
  getAttendanceSessionReport,
  type AttendanceSessionReportResponse,
} from '@/services/classes-service';

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

type ReportViewer = 'instructor' | 'student';

type MockStudentRow = {
  name: string;
  attendedSessions: number;
  missedSessions: number;
  grade: number;
};

const MOCK_STUDENT_NAMES = [
  'Liam Carter',
  'Olivia Bennett',
  'Noah Walker',
  'Emma Brooks',
  'Ava Collins',
  'Elijah Murphy',
  'Sophia Hayes',
  'James Foster',
  'Mia Reed',
  'Lucas Rogers',
  'Amelia Cox',
  'Ethan Bailey',
  'Charlotte Perry',
  'Mason Price',
  'Harper Kelly',
  'Benjamin Ward',
  'Evelyn Barnes',
  'Henry Ross',
  'Abigail Sanders',
  'Alexander Long',
  'Isabella Turner',
  'Daniel Brooks',
  'Chloe Morgan',
  'Michael Foster',
  'Emily Sullivan',
  'Matthew Hughes',
  'Grace Coleman',
  'David Patterson',
  'Avery Jenkins',
  'Joseph Powell',
  'Sofia Richardson',
  'Andrew Butler',
  'Ella Simmons',
  'Christopher Flores',
  'Scarlett Washington',
  'Ryan Bryant',
  'Victoria Griffin',
  'Nathan Diaz',
  'Lily Hayes',
  'Samuel Myers',
];

const MOCK_CS_COURSE_CODES = ['CSC4311', 'CSC3231', 'CSC2112', 'CSC1110'];

const MOCK_CS_COURSE_NAMES = [
  'Operating Systems',
  'Cloud Computing',
  'Data Structures',
  'Algorithms',
  'Computer Networks',
  'Database Systems',
  'Software Engineering',
  'Distributed Systems',
];

const MOCK_CS_SECTIONS = ['002', '003', '004', '005', '006'];

type MockCourseDetails = {
  courseCode: string;
  courseName: string;
  section: string;
};

function pickRandom<T>(items: T[]): T {
  return items[Math.floor(Math.random() * items.length)];
}

function generateMockCourseDetails(): MockCourseDetails {
  return {
    courseCode: pickRandom(MOCK_CS_COURSE_CODES),
    courseName: pickRandom(MOCK_CS_COURSE_NAMES),
    section: pickRandom(MOCK_CS_SECTIONS),
  };
}

function bytesToBase64(bytes: Uint8Array): string {
  const base64Chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  let output = '';
  let index = 0;

  while (index < bytes.length) {
    const remaining = bytes.length - index;
    const byte1 = bytes[index++] ?? 0;
    const byte2 = remaining > 1 ? bytes[index++] ?? 0 : 0;
    const byte3 = remaining > 2 ? bytes[index++] ?? 0 : 0;

    const hasByte2 = remaining > 1;
    const hasByte3 = remaining > 2;

    const encoded1 = byte1 >> 2;
    const encoded2 = ((byte1 & 0x03) << 4) | (byte2 >> 4);
    const encoded3 = hasByte2 ? (((byte2 & 0x0f) << 2) | (byte3 >> 6)) : 64;
    const encoded4 = hasByte3 ? (byte3 & 0x3f) : 64;

    output += base64Chars.charAt(encoded1);
    output += base64Chars.charAt(encoded2);
    output += hasByte2 ? base64Chars.charAt(encoded3) : '=';
    output += hasByte3 ? base64Chars.charAt(encoded4) : '=';
  }

  return output;
}

function formatDateTime(value: string | null) {
  if (!value) {
    return '-';
  }

  const date = new Date(value);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function buildMockReportHtml(options: {
  viewer: ReportViewer;
  reportDate: string;
  courseCode: string;
  courseName: string;
  section: string;
  totalSessionsTaken: number;
  averageAttendanceRate: number;
  sessionWithMostStudents: string;
  sessionWithLeastStudents: string;
  sessionSummaryText: string;
  students: MockStudentRow[];
}) {
  const {
    viewer,
    reportDate,
    courseCode,
    courseName,
    section,
    totalSessionsTaken,
    averageAttendanceRate,
    sessionWithMostStudents,
    sessionWithLeastStudents,
    sessionSummaryText,
    students,
  } = options;

  const studentRows = students
    .map(
      (student) => `
      <tr>
        <td>${student.name}</td>
        <td style="text-align:center;">${student.attendedSessions}</td>
        <td style="text-align:center;">${student.missedSessions}</td>
        <td style="text-align:center;">${student.grade}%</td>
      </tr>`,
    )
    .join('');

  return `
  <html>
    <head>
      <meta charset="utf-8" />
      <style>
        body { font-family: Arial, sans-serif; color: #111827; padding: 24px; }
        h1 { margin: 0 0 8px; font-size: 24px; }
        .meta { color: #4b5563; margin-bottom: 16px; }
        .box { border: 1px solid #d1d5db; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
        .title { font-weight: 700; margin-bottom: 6px; }
        table { width: 100%; border-collapse: collapse; margin-top: 8px; }
        th, td { border: 1px solid #d1d5db; padding: 8px; font-size: 12px; }
        th { background: #f3f4f6; text-align: left; }
      </style>
    </head>
    <body>
      <h1>Attendance Report</h1>
      <div class="meta">${courseCode} - ${courseName} | Section ${section} | Generated: ${reportDate} | Viewer: ${viewer}</div>

      <div class="box">
        <div class="title">Instructor Attendance Snapshot</div>
        <div>Total attendance sessions taken: ${totalSessionsTaken}</div>
        <div>Average attendance rate: ${averageAttendanceRate}%</div>
        <div>Session with most students: ${sessionWithMostStudents}</div>
        <div>Session with least students: ${sessionWithLeastStudents}</div>
      </div>

      <div class="box">
        <div class="title">Session Summary</div>
        <div>${sessionSummaryText}</div>
      </div>

      <div class="box">
        <div class="title">Student Performance (20 Students)</div>
        <table>
          <thead>
            <tr>
              <th>Student Name</th>
              <th style="text-align:center;">Attended Sessions</th>
              <th style="text-align:center;">Missed Sessions</th>
              <th style="text-align:center;">Current Grade</th>
            </tr>
          </thead>
          <tbody>
            ${studentRows}
          </tbody>
        </table>
      </div>
    </body>
  </html>
  `;
}

async function saveAttendancePdf(classId: string, sessionId: string) {
  const response = await getAttendanceSessionPdfResponse(classId, sessionId);
  const filename = `attendance-report-${classId}-${sessionId}.pdf`;

  if (Platform.OS === 'web') {
    const buffer = await response.arrayBuffer();
    const blob = new Blob([buffer], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
    return;
  }

  const buffer = await response.arrayBuffer();
  const base64 = bytesToBase64(new Uint8Array(buffer));
  const fileUri = `${FileSystem.cacheDirectory}${filename}`;
  await FileSystem.writeAsStringAsync(fileUri, base64, {
    encoding: FileSystem.EncodingType.Base64,
  });

  if (await Sharing.isAvailableAsync()) {
    await Sharing.shareAsync(fileUri, {
      mimeType: 'application/pdf',
      dialogTitle: 'Save attendance report',
    });
    return;
  }

  Alert.alert('Saved', `Attendance report saved to ${fileUri}`);
}

async function saveMockAttendancePdf(html: string) {
  if (Platform.OS === 'web') {
    Alert.alert('Not supported', 'Mock PDF generation is currently available on native devices only.');
    return;
  }

  const { uri } = await Print.printToFileAsync({ html });

  if (await Sharing.isAvailableAsync()) {
    await Sharing.shareAsync(uri, {
      mimeType: 'application/pdf',
      dialogTitle: 'Save attendance report',
    });
    return;
  }

  Alert.alert('Saved', `Attendance report saved to ${uri}`);
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.statCard}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={styles.statValue}>{value}</Text>
    </View>
  );
}

function LandscapeMetric({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.landscapeMetricCard}>
      <Text style={styles.landscapeMetricLabel}>{label}</Text>
      <Text style={styles.landscapeMetricValue}>{value}</Text>
    </View>
  );
}

export default function AttendanceReportScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{
    id: string;
    sessionId?: string;
    mock?: string;
    viewer?: string;
    sessionDate?: string;
    presentCount?: string;
    totalStudents?: string;
  }>();

  const [report, setReport] = useState<AttendanceSessionReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingPdf, setSavingPdf] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sessionId = typeof params.sessionId === 'string' ? params.sessionId : '';
  const isMockMode = params.mock === '1';
  const viewer: ReportViewer = params.viewer === 'student' ? 'student' : 'instructor';
  const selectedSessionDate = typeof params.sessionDate === 'string' ? params.sessionDate : null;
  const selectedPresentCount = Number(params.presentCount ?? NaN);
  const selectedTotalStudents = Number(params.totalStudents ?? NaN);

  useEffect(() => {
    let mounted = true;

    (async () => {
      if (isMockMode) {
        if (mounted) {
          setReport(null);
          setLoading(false);
        }
        return;
      }

      if (!params.id || !sessionId) {
        if (mounted) {
          setError('Missing session information for this report.');
          setLoading(false);
        }
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const response = await getAttendanceSessionReport(String(params.id), sessionId);
        if (mounted) {
          setReport(response);
        }
      } catch (e: any) {
        if (mounted) {
          setError(e?.data?.detail || e?.message || 'Failed to load the attendance report.');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    })();

    return () => {
      mounted = false;
    };
  }, [isMockMode, params.id, sessionId]);

  const presentCount = report?.present_students.length ?? 0;
  const unknownCount = report?.unknown_count ?? 0;
  const totalMarked = presentCount + unknownCount;
  const attendanceRate = useMemo(() => {
    if (totalMarked === 0) {
      return 0;
    }

    return Math.round((presentCount / totalMarked) * 100);
  }, [presentCount, totalMarked]);

  const totalAttendanceSessionsTaken = MOCK_INSTRUCTOR_SESSIONS.length;
  const averageAttendanceRate = useMemo(() => {
    if (MOCK_INSTRUCTOR_SESSIONS.length === 0) {
      return 0;
    }

    const totalRate = MOCK_INSTRUCTOR_SESSIONS.reduce((sum, session) => {
      if (session.totalStudents === 0) {
        return sum;
      }
      return sum + (session.presentCount / session.totalStudents) * 100;
    }, 0);

    return Math.round(totalRate / MOCK_INSTRUCTOR_SESSIONS.length);
  }, []);

  const sessionWithMostStudents = useMemo(() => {
    if (MOCK_INSTRUCTOR_SESSIONS.length === 0) {
      return '-';
    }

    const topSession = MOCK_INSTRUCTOR_SESSIONS.reduce((max, current) =>
      current.presentCount > max.presentCount ? current : max,
    );

    return `${topSession.date} (${topSession.presentCount} students)`;
  }, []);

  const sessionWithLeastStudents = useMemo(() => {
    if (MOCK_INSTRUCTOR_SESSIONS.length === 0) {
      return '-';
    }

    const lowSession = MOCK_INSTRUCTOR_SESSIONS.reduce((min, current) =>
      current.presentCount < min.presentCount ? current : min,
    );

    return `${lowSession.date} (${lowSession.presentCount} students)`;
  }, []);

  const mockStudentRows = useMemo<MockStudentRow[]>(() => {
    const totalSessions = Math.max(totalAttendanceSessionsTaken, 1);
    return MOCK_STUDENT_NAMES.map((name, index) => {
      const attendedSessions = Math.max(totalSessions - (index % 5), 4);
      const missedSessions = Math.max(totalSessions - attendedSessions, 0);
      const grade = Math.round((attendedSessions / totalSessions) * 100);

      return {
        name,
        attendedSessions,
        missedSessions,
        grade,
      };
    });
  }, [totalAttendanceSessionsTaken]);

  const mockSessionSummaryText = useMemo(() => {
    if (
      selectedSessionDate &&
      Number.isFinite(selectedPresentCount) &&
      Number.isFinite(selectedTotalStudents)
    ) {
      const rate =
        selectedTotalStudents > 0
          ? Math.round((selectedPresentCount / selectedTotalStudents) * 100)
          : 0;
      return `Session ${selectedSessionDate}: ${selectedPresentCount}/${selectedTotalStudents} students present (${rate}%).`;
    }

    const latest = MOCK_INSTRUCTOR_SESSIONS[MOCK_INSTRUCTOR_SESSIONS.length - 1];
    const rate = Math.round((latest.presentCount / latest.totalStudents) * 100);
    return `Latest session ${latest.date}: ${latest.presentCount}/${latest.totalStudents} students present (${rate}%).`;
  }, [selectedPresentCount, selectedSessionDate, selectedTotalStudents]);

  const handleDownload = async () => {
    if (!params.id) {
      return;
    }

    setSavingPdf(true);
    try {
      if (isMockMode) {
        const courseDetails = generateMockCourseDetails();
        const html = buildMockReportHtml({
          viewer,
          reportDate: new Date().toLocaleString('en-US'),
          courseCode: courseDetails.courseCode,
          courseName: courseDetails.courseName,
          section: courseDetails.section,
          totalSessionsTaken: totalAttendanceSessionsTaken,
          averageAttendanceRate,
          sessionWithMostStudents,
          sessionWithLeastStudents,
          sessionSummaryText: mockSessionSummaryText,
          students: mockStudentRows,
        });
        await saveMockAttendancePdf(html);
      } else {
        if (!sessionId) {
          return;
        }
        await saveAttendancePdf(String(params.id), sessionId);
      }
    } catch (e: any) {
      Alert.alert('Download failed', e?.message || 'Unable to save the attendance report.');
    } finally {
      setSavingPdf(false);
    }
  };

  const roster = report?.present_students ?? [];

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.heroCard}>
          <View style={styles.heroTopRow}>
            <View style={styles.heroBadge}>
              <Ionicons name="document-text-outline" size={16} color="#14324a" />
              <Text style={styles.heroBadgeText}>Attendance report</Text>
            </View>
            <Text style={styles.heroTitle}>Ready for grading</Text>
            <Text style={styles.heroText}>
              Review the session summary below, then save the PDF to your device or share it with your grading workflow.
            </Text>
          </View>

          <View style={styles.heroActionsRow}>
            <Pressable
              style={[styles.primaryButton, savingPdf && styles.disabledButton]}
              onPress={handleDownload}
              disabled={savingPdf || loading || (!isMockMode && !report)}
            >
              {savingPdf ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Ionicons name="download-outline" size={18} color="#fff" style={{ marginRight: 8 }} />
              )}
              <Text style={styles.primaryButtonText}>{Platform.OS === 'web' ? 'Download PDF' : 'Save PDF'}</Text>
            </Pressable>
          </View>
        </View>

        {loading && (
          <View style={styles.loadingCard}>
            <ActivityIndicator size="large" color="#030213" />
            <Text style={styles.loadingText}>Loading session report...</Text>
          </View>
        )}

        {!loading && error && (
          <View style={styles.errorCard}>
            <Ionicons name="alert-circle-outline" size={24} color="#dc2626" />
            <Text style={styles.errorText}>{error}</Text>
            <Pressable style={styles.secondaryButton} onPress={() => router.back()}>
              <Text style={styles.secondaryButtonText}>Go back</Text>
            </Pressable>
          </View>
        )}

        {!loading && report && (
          <>
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Session Summary</Text>
              <Text style={styles.helperText}>{formatDateTime(report.created_at)}</Text>

              <View style={styles.statsRow}>
                <StatCard label="Present" value={`${presentCount}`} />
                <StatCard label="Unknown" value={`${unknownCount}`} />
                <StatCard label="Marked" value={`${attendanceRate}%`} />
              </View>
            </View>

            <View style={styles.card}>
              <View style={styles.sectionHeaderRow}>
                <Text style={styles.cardTitle}>Present Students</Text>
                <Text style={styles.helperText}>{roster.length} student{roster.length === 1 ? '' : 's'}</Text>
              </View>

              {roster.length === 0 ? (
                <Text style={styles.emptyText}>No students were recognized in this session.</Text>
              ) : (
                roster.map((student, index) => (
                  <View key={`${student.student_id}-${index}`} style={styles.rosterRow}>
                    <View>
                      <Text style={styles.valueText}>
                        {student.first_name} {student.last_name}
                      </Text>
                      <Text style={styles.helperText}>{student.student_id}</Text>
                    </View>
                    <View style={styles.confidenceBadge}>
                      <Text style={styles.confidenceText}>
                        {typeof student.confidence === 'number' ? `${Math.round(student.confidence * 100)}%` : '-'}
                      </Text>
                    </View>
                  </View>
                ))
              )}
            </View>
          </>
        )}

        {!loading && isMockMode && (
          <>
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Instructor Attendance Snapshot</Text>
              <Text style={styles.helperText}>Based on latest attendance history</Text>

              <View style={styles.compactStatsRow}>
                <View style={styles.compactStatCard}>
                  <Text style={styles.statLabel}>Total Sessions Taken</Text>
                  <Text style={styles.compactStatValue}>{totalAttendanceSessionsTaken}</Text>
                </View>
                <View style={styles.compactStatCard}>
                  <Text style={styles.statLabel}>Average Attendance Rate</Text>
                  <Text style={styles.compactStatValue}>{averageAttendanceRate}%</Text>
                </View>
              </View>

              <View style={styles.landscapeMetricsStack}>
                <LandscapeMetric label="Session With Most Students" value={sessionWithMostStudents} />
                <LandscapeMetric label="Session With Least Students" value={sessionWithLeastStudents} />
              </View>
            </View>

            <View style={styles.card}>
              <Text style={styles.cardTitle}>Session Summary Preview</Text>
              <Text style={styles.helperText}>{mockSessionSummaryText}</Text>
            </View>
          </>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f6f8fc',
  },
  content: {
    padding: 16,
    gap: 12,
    flexGrow: 1,
  },
  heroCard: {
    borderRadius: 24,
    padding: 20,
    backgroundColor: '#eaf3ff',
    borderWidth: 1,
    borderColor: '#cfe1f8',
    gap: 20,
  },
  heroTopRow: {
    gap: 10,
  },
  heroBadge: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#dcecff',
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  heroBadgeText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#14324a',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  heroTitle: {
    fontSize: 28,
    lineHeight: 34,
    fontWeight: '800',
    color: '#08101a',
  },
  heroText: {
    fontSize: 15,
    lineHeight: 22,
    color: '#4b5b6b',
  },
  heroActionsRow: {
    flexDirection: 'row',
    gap: 10,
    flexWrap: 'wrap',
  },
  primaryButton: {
    minHeight: 48,
    paddingHorizontal: 18,
    borderRadius: 14,
    backgroundColor: '#030213',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  secondaryButton: {
    minHeight: 48,
    paddingHorizontal: 18,
    borderRadius: 14,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#d8dde6',
    alignItems: 'center',
    justifyContent: 'center',
  },
  secondaryButtonText: {
    color: '#08101a',
    fontSize: 16,
    fontWeight: '700',
  },
  disabledButton: {
    opacity: 0.7,
  },
  loadingCard: {
    borderRadius: 20,
    backgroundColor: '#fff',
    padding: 28,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  loadingText: {
    color: '#4b5b6b',
    fontSize: 15,
  },
  errorCard: {
    borderRadius: 20,
    backgroundColor: '#fff',
    padding: 20,
    gap: 12,
    alignItems: 'flex-start',
    borderWidth: 1,
    borderColor: '#f1c6c6',
  },
  errorText: {
    color: '#991b1b',
    fontSize: 15,
    lineHeight: 22,
  },
  card: {
    borderRadius: 20,
    backgroundColor: '#fff',
    padding: 18,
    gap: 14,
    borderWidth: 1,
    borderColor: '#e7ebf2',
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: '#08101a',
  },
  helperText: {
    color: '#6b7280',
    fontSize: 13,
    lineHeight: 18,
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: 12,
  },
  statsRow: {
    flexDirection: 'row',
    gap: 10,
    flexWrap: 'wrap',
  },
  compactStatsRow: {
    flexDirection: 'row',
    gap: 10,
  },
  compactStatCard: {
    flex: 1,
    borderRadius: 14,
    backgroundColor: '#f8fafc',
    borderWidth: 1,
    borderColor: '#e7ebf2',
    paddingVertical: 10,
    paddingHorizontal: 12,
    gap: 4,
  },
  compactStatValue: {
    color: '#08101a',
    fontSize: 20,
    fontWeight: '800',
  },
  landscapeMetricsStack: {
    gap: 8,
  },
  landscapeMetricCard: {
    borderRadius: 14,
    backgroundColor: '#f8fafc',
    borderWidth: 1,
    borderColor: '#e7ebf2',
    paddingVertical: 10,
    paddingHorizontal: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
  },
  landscapeMetricLabel: {
    color: '#6b7280',
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    fontWeight: '700',
    flexShrink: 1,
  },
  landscapeMetricValue: {
    color: '#08101a',
    fontSize: 15,
    fontWeight: '700',
    textAlign: 'right',
    flexShrink: 1,
  },
  statCard: {
    flexGrow: 1,
    flexBasis: 100,
    borderRadius: 16,
    backgroundColor: '#f8fafc',
    borderWidth: 1,
    borderColor: '#e7ebf2',
    paddingVertical: 14,
    paddingHorizontal: 14,
    gap: 4,
  },
  statLabel: {
    color: '#6b7280',
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    fontWeight: '700',
  },
  statValue: {
    color: '#08101a',
    fontSize: 24,
    fontWeight: '800',
  },
  rosterRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#eef2f7',
  },
  confidenceBadge: {
    borderRadius: 999,
    backgroundColor: '#eaf3ff',
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  confidenceText: {
    color: '#14324a',
    fontWeight: '800',
    fontSize: 12,
  },
  valueText: {
    color: '#08101a',
    fontSize: 16,
    fontWeight: '700',
  },
  emptyText: {
    color: '#6b7280',
    fontSize: 15,
    lineHeight: 22,
  },
});
