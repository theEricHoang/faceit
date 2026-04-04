import React, { useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams } from 'expo-router';
import { getMockAttendanceSessionDetails } from '@/mocks/attendance-session-details';
import { useAuthStore } from '@/stores/auth-store';

type FilterKey = 'all' | 'present' | 'absent';

export default function AttendanceSessionDetailsScreen() {
  const params = useLocalSearchParams<{ id: string; sessionId: string }>();
  const user = useAuthStore((state) => state.user);
  const isInstructor = user?.type === 'instructor';
  const [filter, setFilter] = useState<FilterKey>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const details = useMemo(() => {
    if (!params.id || !params.sessionId) {
      return null;
    }

    return getMockAttendanceSessionDetails(String(params.id), String(params.sessionId));
  }, [params.id, params.sessionId]);

  const filteredStudents = useMemo(() => {
    if (!details) {
      return [];
    }

    const normalizedQuery = searchQuery.trim().toLowerCase();

    const byFilter =
      filter === 'all'
        ? details.students
        : details.students.filter((student) => student.status === filter);

    if (!normalizedQuery) {
      return byFilter;
    }

    return byFilter.filter((student) => {
      const fullName = `${student.firstName} ${student.lastName}`.toLowerCase();
      return fullName.includes(normalizedQuery) || student.studentId.toLowerCase().includes(normalizedQuery);
    });
  }, [details, filter, searchQuery]);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (!isInstructor) {
    return (
      <View style={styles.centeredState}>
        <Ionicons name="lock-closed-outline" size={28} color="#8a8a97" />
        <Text style={styles.stateTitle}>Instructor access only</Text>
        <Text style={styles.stateText}>This view is only available from the instructor workflow.</Text>
      </View>
    );
  }

  if (!details) {
    return (
      <View style={styles.centeredState}>
        <Ionicons name="document-text-outline" size={28} color="#8a8a97" />
        <Text style={styles.stateTitle}>Session not found</Text>
        <Text style={styles.stateText}>The selected attendance session is not available in the current mock dataset.</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.heroCard}>
        <View style={styles.heroTopRow}>
          <View style={styles.heroCopy}>
            <Text style={styles.eyebrow}>Attendance Details</Text>
            <Text style={styles.heroTitle}>{formatDate(details.date)}</Text>
            <Text style={styles.heroSubtext}>Per-session attendance results for this class.</Text>
          </View>
          <View style={styles.unknownBadge}>
            <Ionicons name="sparkles-outline" size={16} color="#92400e" />
            <Text style={styles.unknownBadgeText}>{details.unknownCount} unknown</Text>
          </View>
        </View>

        <View style={styles.heroStatsRow}>
          <View style={[styles.heroStatCard, styles.presentTint]}>
            <Text style={styles.heroStatValue}>{details.presentCount}</Text>
            <Text style={styles.heroStatLabel}>Present</Text>
          </View>
          <View style={[styles.heroStatCard, styles.absentTint]}>
            <Text style={styles.heroStatValue}>{details.absentCount}</Text>
            <Text style={styles.heroStatLabel}>Absent</Text>
          </View>
          <View style={styles.heroStatCard}>
            <Text style={styles.heroStatValue}>{details.students.length}</Text>
            <Text style={styles.heroStatLabel}>Enrolled</Text>
          </View>
        </View>
      </View>

      <View style={styles.sectionCard}>
        <View style={styles.sectionHeader}>
          <View>
            <Text style={styles.sectionTitle}>Student Results</Text>
            <Text style={styles.sectionText}>Review each enrolled student&apos;s attendance status for this session.</Text>
          </View>
        </View>

        <View style={styles.searchBar}>
          <Ionicons name="search-outline" size={18} color="#8a8a97" />
          <TextInput
            value={searchQuery}
            onChangeText={setSearchQuery}
            placeholder="Search name or student ID"
            placeholderTextColor="#9ca3af"
            style={styles.searchInput}
            autoCapitalize="none"
            autoCorrect={false}
          />
          {searchQuery.length > 0 ? (
            <Pressable onPress={() => setSearchQuery('')} hitSlop={8}>
              <Ionicons name="close-circle" size={18} color="#8a8a97" />
            </Pressable>
          ) : null}
        </View>

        <View style={styles.filtersRow}>
          {(['all', 'present', 'absent'] as FilterKey[]).map((option) => {
            const selected = filter === option;

            return (
              <Pressable
                key={option}
                style={[styles.filterChip, selected && styles.filterChipActive]}
                onPress={() => setFilter(option)}
              >
                <Text style={[styles.filterChipText, selected && styles.filterChipTextActive]}>
                  {option === 'all' ? 'All' : option === 'present' ? 'Present' : 'Absent'}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <View style={styles.list}>
          {filteredStudents.length === 0 ? (
            <View style={styles.emptyStateCard}>
              <Ionicons name="search-outline" size={24} color="#8a8a97" />
              <Text style={styles.emptyStateTitle}>No students found</Text>
              <Text style={styles.emptyStateText}>Try another name or student ID, or clear the current filter.</Text>
            </View>
          ) : filteredStudents.map((student) => (
            <View key={student.studentId} style={styles.studentRow}>
              <View style={styles.studentIdentity}>
                <View style={[styles.avatarCircle, student.status === 'present' ? styles.avatarPresent : styles.avatarAbsent]}>
                  <Text style={styles.avatarText}>{student.firstName[0]}{student.lastName[0]}</Text>
                </View>
                <View style={styles.studentCopy}>
                  <Text style={styles.studentName}>{student.firstName} {student.lastName}</Text>
                  <Text style={styles.studentMeta}>{student.studentId}</Text>
                </View>
              </View>

              <View style={styles.studentStatusGroup}>
                <View style={[styles.statusBadge, student.status === 'present' ? styles.statusPresent : styles.statusAbsent]}>
                  <Text style={[styles.statusBadgeText, student.status === 'present' ? styles.statusPresentText : styles.statusAbsentText]}>
                    {student.status === 'present' ? 'Present' : 'Absent'}
                  </Text>
                </View>
                <Text style={styles.studentConfidence}>
                  {student.confidence ? `${Math.round(student.confidence * 100)}% match` : 'No match captured'}
                </Text>
              </View>
            </View>
          ))}
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  content: {
    padding: 16,
    gap: 14,
  },
  centeredState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
    backgroundColor: '#fff',
    gap: 8,
  },
  stateTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1f2937',
  },
  stateText: {
    fontSize: 14,
    lineHeight: 20,
    color: '#6b7280',
    textAlign: 'center',
  },
  heroCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#eee',
    gap: 18,
  },
  heroTopRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 12,
    flexWrap: 'wrap',
  },
  heroCopy: {
    flex: 1,
    minWidth: 220,
  },
  eyebrow: {
    color: '#717182',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.4,
    textTransform: 'uppercase',
    marginBottom: 6,
  },
  heroTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#030213',
    marginBottom: 4,
  },
  heroSubtext: {
    color: '#717182',
    fontSize: 14,
    lineHeight: 20,
    maxWidth: 320,
  },
  unknownBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#f3f3f3',
    borderWidth: 1,
    borderColor: '#eee',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 999,
    alignSelf: 'flex-start',
    maxWidth: '100%',
  },
  unknownBadgeText: {
    color: '#030213',
    fontWeight: '600',
    fontSize: 13,
  },
  heroStatsRow: {
    flexDirection: 'row',
    gap: 10,
    flexWrap: 'wrap',
  },
  heroStatCard: {
    flex: 1,
    minWidth: 96,
    borderRadius: 10,
    paddingVertical: 14,
    paddingHorizontal: 12,
    backgroundColor: '#f3f3f3',
    gap: 4,
  },
  presentTint: {
    backgroundColor: '#f0fdf4',
  },
  absentTint: {
    backgroundColor: '#fef2f2',
  },
  heroStatValue: {
    color: '#030213',
    fontSize: 24,
    fontWeight: '700',
  },
  heroStatLabel: {
    color: '#717182',
    fontSize: 13,
    fontWeight: '600',
  },
  sectionCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#eee',
    gap: 14,
  },
  sectionHeader: {
    gap: 4,
  },
  sectionTitle: {
    color: '#1f2937',
    fontSize: 20,
    fontWeight: '700',
  },
  sectionText: {
    color: '#6b7280',
    fontSize: 14,
    lineHeight: 20,
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#eee',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  searchInput: {
    flex: 1,
    color: '#111827',
    fontSize: 14,
    padding: 0,
  },
  filtersRow: {
    flexDirection: 'row',
    gap: 8,
    flexWrap: 'wrap',
  },
  filterChip: {
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 9,
    backgroundColor: '#f3f3f3',
  },
  filterChipActive: {
    backgroundColor: '#000',
  },
  filterChipText: {
    color: '#5b6470',
    fontSize: 13,
    fontWeight: '700',
  },
  filterChipTextActive: {
    color: '#f8fafc',
  },
  list: {
    gap: 10,
  },
  emptyStateCard: {
    alignItems: 'center',
    gap: 8,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#eee',
    backgroundColor: '#fff',
    paddingVertical: 24,
    paddingHorizontal: 16,
  },
  emptyStateTitle: {
    color: '#1f2937',
    fontSize: 16,
    fontWeight: '700',
  },
  emptyStateText: {
    color: '#6b7280',
    fontSize: 13,
    lineHeight: 18,
    textAlign: 'center',
  },
  studentRow: {
    borderRadius: 12,
    padding: 14,
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#eee',
    gap: 12,
  },
  studentIdentity: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  avatarCircle: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarPresent: {
    backgroundColor: '#dcfce7',
  },
  avatarAbsent: {
    backgroundColor: '#fee2e2',
  },
  avatarText: {
    color: '#1f2937',
    fontSize: 14,
    fontWeight: '800',
  },
  studentCopy: {
    flex: 1,
    gap: 2,
  },
  studentName: {
    color: '#111827',
    fontSize: 15,
    fontWeight: '700',
  },
  studentMeta: {
    color: '#6b7280',
    fontSize: 12,
  },
  studentStatusGroup: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 12,
  },
  statusBadge: {
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  statusPresent: {
    backgroundColor: '#dcfce7',
  },
  statusAbsent: {
    backgroundColor: '#fee2e2',
  },
  statusBadgeText: {
    fontSize: 12,
    fontWeight: '800',
  },
  statusPresentText: {
    color: '#166534',
  },
  statusAbsentText: {
    color: '#b91c1c',
  },
  studentConfidence: {
    color: '#6b7280',
    fontSize: 12,
    fontWeight: '600',
  },
});
