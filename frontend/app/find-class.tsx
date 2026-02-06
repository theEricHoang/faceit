import React, { useEffect, useMemo, useState } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet, ScrollView, Modal, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { getOpenClasses, joinClassByCode, type ClassItem } from '@/services/classes-service';
import { useRouter } from 'expo-router';

type OpenClass = {
  id: string;
  code: string;
  section: string;
  schedule: string;
  studentCount: number;
  instructorName?: string;
};

// Backend-provided classes will be displayed under Open Classes

export default function FindClassScreen() {
  const router = useRouter();
  const [inviteCode, setInviteCode] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedClass, setSelectedClass] = useState<OpenClass | null>(null);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [requestSent, setRequestSent] = useState<string[]>([]);
  const [successDialogOpen, setSuccessDialogOpen] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorDialogOpen, setErrorDialogOpen] = useState(false);
  const [openClasses, setOpenClasses] = useState<ClassItem[]>([]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await getOpenClasses();
        if (mounted) setOpenClasses(res.classes || []);
      } catch (err: any) {
        // Non-blocking: keep UI usable even if fetch fails
        console.warn('Failed to fetch open classes', err?.message || err);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const filteredClasses = useMemo(() => {
    const q = searchQuery.toLowerCase();
    return openClasses.filter(cls =>
      (cls.course_code || '').toLowerCase().includes(q) ||
      (cls.course_name || '').toLowerCase().includes(q) ||
      (cls.section || '').toLowerCase().includes(q)
    );
  }, [searchQuery, openClasses]);

  const handleJoinWithCode = async () => {
    if (!inviteCode.trim()) {
      Alert.alert('Missing Code', 'Please enter an invite code');
      return;
    }
    try {
      const res = await joinClassByCode({ course_code: inviteCode.trim() });
      setSuccessMessage(`Successfully join the class: ${res.course_name}, section: ${res.section}`);
      setSuccessDialogOpen(true);
    } catch (e: any) {
      const msg = e?.data?.detail || e?.message || '';
      // Show specific modal text for class not found, else generic error
      if ((msg || '').toLowerCase().includes('class not found')) {
        setErrorDialogOpen(true);
      } else {
        Alert.alert('Error', msg || 'Failed to join class');
      }
    }
  };

  const handleRequestToJoin = (cls: OpenClass) => {
    setSelectedClass(cls);
    setConfirmDialogOpen(true);
  };

  const handleConfirmRequest = () => {
    if (selectedClass) {
      setRequestSent(prev => [...prev, selectedClass.id]);
      Alert.alert('Request Sent', `Join request sent for ${selectedClass.code} ${selectedClass.section}`);
      setConfirmDialogOpen(false);
      setSelectedClass(null);
    }
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        {/* Invite Code Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Enter Invite Code</Text>
          <View style={styles.cardRow}>
            <View style={[styles.searchContainer, { flex: 1, marginBottom: 0 }]}>
              <Ionicons name="pricetag-outline" size={18} color="#888" />
              <TextInput
                placeholder="Enter code from instructor"
                value={inviteCode}
                onChangeText={(t) => setInviteCode(t)}
                autoCapitalize="none"
                autoCorrect={false}
                style={styles.searchInput}
                placeholderTextColor={'#888'}
              />
            </View>
            <Pressable style={styles.primaryButton} onPress={handleJoinWithCode}>
              <Text style={styles.primaryButtonText}>Join</Text>
            </Pressable>
          </View>
          <Text style={styles.labelText}>Ask your instructor for an invite code to join their class directly.</Text>
        </View>

        {/* Divider */}
        <View style={styles.divider} />

        {/* Search Section */}
        <View style={styles.section}>
          <View style={styles.searchContainer}>
            <Ionicons name="search" size={18} color="#888" />
            <TextInput
              placeholder="Search by course code, section, or instructor"
              value={searchQuery}
              onChangeText={setSearchQuery}
              style={styles.searchInput}
              placeholderTextColor={'#888'}
            />
          </View>
        </View>

        {/* Open Classes */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Open Classes</Text>
          {filteredClasses.length === 0 ? (
            <View style={styles.centerContainer}>
              <Ionicons name="search" size={48} color="#888" />
              <Text style={styles.emptyText}>No classes found</Text>
            </View>
          ) : (
            filteredClasses.map((cls) => {
              const isRequested = requestSent.includes(String(cls.class_id));
              return (
                <View key={String(cls.class_id)} style={styles.card}>
                  <View style={styles.cardInnerRow}>
                    <View style={{ flex: 1 }}>
                      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                        <Text style={styles.valueText}>{cls.course_code}</Text>
                        <Text style={[styles.labelText, { borderWidth: 1, borderColor: '#eee', borderRadius: 8, paddingHorizontal: 8 }]}> {cls.section} </Text>
                      </View>
                      <Text style={[styles.labelText, { marginTop: 4 }]}>{cls.course_name}</Text>
                      <View style={{ marginTop: 6 }}>
                        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                          <Ionicons name="calendar-outline" size={16} color="#888" />
                          <Text style={styles.labelText}>{cls.schedule}</Text>
                        </View>
                        {!!cls.room && (
                          <View style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 6, marginTop: 4 }}>
                            <Ionicons name="home-outline" size={16} color="#888" />
                            <Text style={[styles.labelText, { flex: 1 }]}>{cls.room}</Text>
                          </View>
                        )}
                      </View>
                    </View>
                  </View>

                  <Pressable
                    style={[styles.primaryButton, isRequested && { backgroundColor: '#fff', borderWidth: 1, borderColor: '#eee' }]}
                    onPress={() => !isRequested && handleRequestToJoin({
                      id: String(cls.class_id),
                      code: cls.course_code,
                      section: cls.section,
                      schedule: cls.schedule,
                      studentCount: 0,
                      instructorName: undefined,
                    })}
                    disabled={isRequested}
                  >
                    {isRequested ? (
                      <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        <Ionicons name="checkmark-outline" size={18} color="#000" style={{ marginRight: 8 }} />
                        <Text style={[styles.primaryButtonText, { color: '#000' }]}>Request Sent</Text>
                      </View>
                    ) : (
                      <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        <Ionicons name="send-outline" size={18} color="#fff" style={{ marginRight: 8 }} />
                        <Text style={styles.primaryButtonText}>Request to Join</Text>
                      </View>
                    )}
                  </Pressable>
                </View>
              );
            })
          )}
        </View>
      </ScrollView>

      {/* Confirmation Dialog */}
      <Modal visible={confirmDialogOpen} transparent animationType="fade" onRequestClose={() => setConfirmDialogOpen(false)}>
        <Pressable style={styles.menuOverlay} onPress={() => setConfirmDialogOpen(false)}>
          <View style={styles.menuContainer}>
            <View style={styles.header}>
              <Text style={styles.title}>Request to Join Class</Text>
            </View>
            {selectedClass && (
              <View style={{ padding: 16 }}>
                <View style={styles.card}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                    <Text style={styles.valueText}>{selectedClass.code}</Text>
                    <Text style={[styles.labelText, { borderWidth: 1, borderColor: '#eee', borderRadius: 8, paddingHorizontal: 8 }]}>{selectedClass.section}</Text>
                  </View>
                  {!!selectedClass.instructorName && (
                    <Text style={[styles.labelText, { marginTop: 4 }]}>{selectedClass.instructorName}</Text>
                  )}
                  <Text style={[styles.labelText, { marginTop: 4 }]}>{selectedClass.schedule}</Text>
                </View>
              </View>
            )}
            <View style={{ flexDirection: 'row', justifyContent: 'flex-end', gap: 8, padding: 16 }}>
              <Pressable style={[styles.primaryButton, { backgroundColor: '#fff', borderWidth: 1, borderColor: '#eee' }]} onPress={() => setConfirmDialogOpen(false)}>
                <Text style={[styles.primaryButtonText, { color: '#000' }]}>Cancel</Text>
              </Pressable>
              <Pressable style={styles.primaryButton} onPress={handleConfirmRequest}>
                <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                  <Ionicons name="send-outline" size={18} color="#fff" style={{ marginRight: 8 }} />
                  <Text style={styles.primaryButtonText}>Send Request</Text>
                </View>
              </Pressable>
            </View>
          </View>
        </Pressable>
      </Modal>

      {/* Success Dialog */}
      <Modal visible={successDialogOpen} transparent animationType="fade" onRequestClose={() => setSuccessDialogOpen(false)}>
        <Pressable style={styles.menuOverlay} onPress={() => setSuccessDialogOpen(false)}>
          <View style={styles.menuContainer}>
            <View style={styles.header}>
              <Text style={styles.title}>Success</Text>
            </View>
            <View style={{ padding: 16 }}>
              <Text style={styles.valueText}>{successMessage}</Text>
            </View>
            <View style={{ flexDirection: 'row', justifyContent: 'flex-end', gap: 8, padding: 16 }}>
              <Pressable
                style={styles.primaryButton}
                onPress={() => {
                  setSuccessDialogOpen(false);
                  setInviteCode('');
                  router.back();
                }}
              >
                <Text style={styles.primaryButtonText}>OK</Text>
              </Pressable>
            </View>
          </View>
        </Pressable>
      </Modal>

      {/* Error Dialog for No Class Found */}
      <Modal visible={errorDialogOpen} transparent animationType="fade" onRequestClose={() => setErrorDialogOpen(false)}>
        <Pressable style={styles.menuOverlay} onPress={() => setErrorDialogOpen(false)}>
          <View style={styles.menuContainer}>
            <View style={styles.header}>
              <Text style={styles.title}>Not Found</Text>
            </View>
            <View style={{ padding: 16 }}>
              <Text style={styles.valueText}>No class with the corresponding code</Text>
            </View>
            <View style={{ flexDirection: 'row', justifyContent: 'flex-end', gap: 8, padding: 16 }}>
              <Pressable
                style={[styles.primaryButton, { backgroundColor: '#fff', borderWidth: 1, borderColor: '#eee' }]}
                onPress={() => setErrorDialogOpen(false)}
              >
                <Text style={[styles.primaryButtonText, { color: '#000' }]}>Close</Text>
              </Pressable>
            </View>
          </View>
        </Pressable>
      </Modal>
    </View>
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
  title: {
    fontSize: 24,
    fontWeight: '700',
  },
  content: {
    padding: 16,
    flexGrow: 1,
  },
  section: {
    marginTop: 16,
    gap: 8,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#030213',
  },
  labelText: {
    color: '#717182',
    fontSize: 16,
    fontWeight: '500',
  },
  valueText: {
    color: '#030213',
    fontSize: 16,
    fontWeight: '500',
  },
  card: {
    borderWidth: 1,
    borderColor: '#eee',
    borderRadius: 12,
    padding: 12,
    gap: 4,
    backgroundColor: '#fff',
    marginBottom: 12,
  },
  cardInnerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
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
    marginBottom: 8,
    gap: 8,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f3f3f3',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 16,
  },
  searchInput: {
    flex: 1,
    marginLeft: 8,
    fontSize: 16,
  },
  primaryButton: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: '#000',
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryButtonText: {
    color: '#fff',
    fontWeight: '600',
  },
  divider: {
    height: 1,
    backgroundColor: '#eee',
    marginVertical: 8,
  },
  centerContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 24,
    gap: 8,
  },
  emptyText: {
    color: '#888',
    fontSize: 16,
    textAlign: 'center',
  },
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
});
