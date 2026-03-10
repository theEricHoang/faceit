import { useState, useEffect, useCallback } from "react";
import { useFocusEffect } from "@react-navigation/native";
import {
  View,
  Text,
  ScrollView,
  TextInput,
  Pressable,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
  Modal,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import ClassCard from "../../components/ClassCard";
import StudentListModal from "../../components/StudentListModal";
import { SafeAreaView } from "react-native-safe-area-context";
import CreateClassModal from "../../components/CreateClassModal";
import { useAuthStore } from "@/stores/auth-store";
import { getClasses, ClassItem, getClassStudents, StudentEnrollmentItem } from "@/services/classes-service";
import { logout } from "@/services/auth-service";

export default function HomeScreen() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showStudentList, setShowStudentList] = useState(false);
  const [selectedClass, setSelectedClass] = useState<ClassItem | null>(null);
  const [students, setStudents] = useState<StudentEnrollmentItem[]>([]);
  const [studentListLoading, setStudentListLoading] = useState(false);
  const [studentListError, setStudentListError] = useState<string | null>(null);
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const user = useAuthStore((state) => state.user);
  const role = user?.type ?? "student";

  const fetchClasses = useCallback(async () => {
    try {
      setError(null);
      const response = await getClasses();
      setClasses(response.classes);
    } catch (err) {
      console.error("Failed to fetch classes:", err);
      setError("Failed to load classes");
    }
  }, []);

  // Initial load
  useEffect(() => {
    const loadClasses = async () => {
      setIsLoading(true);
      await fetchClasses();
      setIsLoading(false);
    };
    loadClasses();
  }, [fetchClasses]);

  // Pull to refresh
  const onRefresh = useCallback(async () => {
    setIsRefreshing(true);
    await fetchClasses();
    setIsRefreshing(false);
  }, [fetchClasses]);

  // Refresh when screen regains focus (e.g., after joining a class)
  useFocusEffect(
    useCallback(() => {
      fetchClasses();
    }, [fetchClasses])
  );

  // Called when a class is created successfully
  const handleClassCreated = useCallback(() => {
    setShowModal(false);
    fetchClasses();
  }, [fetchClasses]);

  const filteredClasses = classes.filter((cls) =>
    `${cls.course_code} ${cls.course_name} ${cls.section}`
      .toLowerCase()
      .includes(searchQuery.toLowerCase())
  );

  // Get user initials for avatar
  const userInitials = user
    ? `${user.first_name?.[0] ?? ""}${user.last_name?.[0] ?? ""}`.toUpperCase()
    : "??";

  const handleLogout = async () => {
    setShowProfileMenu(false);
    await logout();
    router.replace("/(auth)/login");
  };

  // Fetch students for a selected class (instructor only)
  const fetchClassStudents = useCallback(async (classId: string) => {
    try {
      setStudentListError(null);
      setStudentListLoading(true);
      const response = await getClassStudents(classId);
      setStudents(response.students);
    } catch (err) {
      console.error("Failed to fetch students:", err);
      setStudentListError("Failed to load students");
    } finally {
      setStudentListLoading(false);
    }
  }, []);

  const handleViewStudents = useCallback((classItem: ClassItem) => {
    setSelectedClass(classItem);
    setShowStudentList(true);
    fetchClassStudents(classItem.class_id);
  }, [fetchClassStudents]);

  const handleCloseStudentList = useCallback(() => {
    setShowStudentList(false);
    setSelectedClass(null);
    setStudents([]);
    setStudentListError(null);
  }, []);

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>FaceIT</Text>
        <Pressable style={styles.avatar} onPress={() => setShowProfileMenu(true)}>
          <Text style={styles.avatarText}>{userInitials}</Text>
        </Pressable>
      </View>

      {/* Profile Menu Modal */}
      <Modal
        visible={showProfileMenu}
        transparent
        animationType="fade"
        onRequestClose={() => setShowProfileMenu(false)}
      >
        <Pressable 
          style={styles.menuOverlay} 
          onPress={() => setShowProfileMenu(false)}
        >
          <View style={styles.menuContainer}>
            <View style={styles.menuHeader}>
              <View style={styles.menuAvatar}>
                <Text style={styles.menuAvatarText}>{userInitials}</Text>
              </View>
              <View style={styles.menuUserInfo}>
                <Text style={styles.menuUserName}>
                  {user?.first_name} {user?.last_name}
                </Text>
                <Text style={styles.menuUserEmail}>{user?.email}</Text>
                <Text style={styles.menuUserType}>
                  {role === "instructor" ? "Instructor" : "Student"}
                </Text>
              </View>
            </View>
            <View style={styles.menuDivider} />
            <Pressable style={styles.menuItem} onPress={handleLogout}>
              <Ionicons name="log-out-outline" size={20} color="#e53935" />
              <Text style={styles.menuItemTextDanger}>Log Out</Text>
            </Pressable>
          </View>
        </Pressable>
      </Modal>

      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl refreshing={isRefreshing} onRefresh={onRefresh} />
        }
      >
        {/* Class list header */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>My Classes</Text>
          {role === "instructor" ? (
            <Pressable style={styles.addButton} onPress={() => setShowModal(true)}>
              <Ionicons name="add" size={20} color="#fff" />
            </Pressable>
          ) : (
            <Pressable
              style={styles.sectionActionButton}
              onPress={() => router.push("/find-class")}
            >
              <Text style={styles.sectionActionText}>+ Find Class</Text>
            </Pressable>
          )}
        </View>

        {/* Search */}
        <View style={styles.searchContainer}>
          <Ionicons name="search" size={18} color="#888" />
          <TextInput
            placeholder="Search classes..."
            value={searchQuery}
            onChangeText={setSearchQuery}
            style={styles.searchInput}
            placeholderTextColor={"#888"}
          />
        </View>

        {/* Find Class button moved to header */}

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
            <Pressable style={styles.retryButton} onPress={fetchClasses}>
              <Text style={styles.retryText}>Retry</Text>
            </Pressable>
          </View>
        )}

        {/* Empty state */}
        {!isLoading && !error && filteredClasses.length === 0 && (
          <View style={styles.centerContainer}>
            <Text style={styles.emptyText}>
              {searchQuery
                ? "No classes match your search"
                : role === "instructor"
                ? "You haven't created any classes yet"
                : "You're not enrolled in any classes yet"}
            </Text>
          </View>
        )}

        {/* Class list */}
        {!isLoading &&
          !error &&
          filteredClasses.map((cls) => (
            <ClassCard
              key={cls.class_id}
              courseCode={cls.course_code}
              courseName={cls.course_name}
              section={cls.section}
              schedule={cls.schedule}
              room={cls.room}
              onPress={() => 
                role === "instructor" 
                  ? handleViewStudents(cls)
                  : router.push(`/class/${cls.class_id}`)
              }
            />
          ))}
      </ScrollView>
      {role === "instructor" && (
        <CreateClassModal
          visible={showModal}
          onClose={() => setShowModal(false)}
          onSuccess={handleClassCreated}
        />
      )}

      {selectedClass && (
        <StudentListModal
          visible={showStudentList}
          classId={selectedClass.class_id}
          courseCode={selectedClass.course_code}
          courseName={selectedClass.course_name}
          section={selectedClass.section}
          students={students}
          isLoading={studentListLoading}
          error={studentListError}
          onClose={handleCloseStudentList}
          onRetry={() => selectedClass && fetchClassStudents(selectedClass.class_id)}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#fff",
  },
  safeArea: {
    flex: 1,
    backgroundColor: "#fff",
  },
  header: {
    paddingHorizontal: 16,
    paddingBottom: 12,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderBottomWidth: 1,
    borderColor: "#eee",
  },
  title: {
    fontSize: 24,
    fontWeight: "700",
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "#000",
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: {
    color: "#fff",
    fontWeight: "600",
  },
  content: {
    padding: 16,
    flexGrow: 1,
  },
  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "600",
  },
  addButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "#000",
    alignItems: "center",
    justifyContent: "center",
  },
  searchContainer: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#f3f3f3",
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
  centerContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 40,
  },
  errorText: {
    color: "#e53935",
    fontSize: 16,
    marginBottom: 12,
  },
  retryButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: "#000",
    borderRadius: 8,
  },
  retryText: {
    color: "#fff",
    fontWeight: "600",
  },
  primaryButton: {
    marginTop: 8,
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: "#000",
    borderRadius: 12,
    alignItems: "center",
  },
  primaryButtonText: {
    color: "#fff",
    fontWeight: "600",
  },
  sectionActionButton: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: "#000",
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
  },
  sectionActionText: {
    color: "#fff",
    fontWeight: "600",
  },
  emptyText: {
    color: "#888",
    fontSize: 16,
    textAlign: "center",
  },
  // Profile Menu styles
  menuOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.4)",
    justifyContent: "flex-start",
    alignItems: "flex-end",
    paddingTop: 100,
    paddingRight: 16,
  },
  menuContainer: {
    backgroundColor: "#fff",
    borderRadius: 12,
    width: 250,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 5,
  },
  menuHeader: {
    flexDirection: "row",
    alignItems: "center",
    padding: 16,
  },
  menuAvatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: "#000",
    alignItems: "center",
    justifyContent: "center",
  },
  menuAvatarText: {
    color: "#fff",
    fontWeight: "600",
    fontSize: 18,
  },
  menuUserInfo: {
    marginLeft: 12,
    flex: 1,
  },
  menuUserName: {
    fontSize: 16,
    fontWeight: "600",
  },
  menuUserEmail: {
    fontSize: 12,
    color: "#666",
    marginTop: 2,
  },
  menuUserType: {
    fontSize: 12,
    color: "#888",
    marginTop: 2,
    textTransform: "capitalize",
  },
  menuDivider: {
    height: 1,
    backgroundColor: "#eee",
  },
  menuItem: {
    flexDirection: "row",
    alignItems: "center",
    padding: 16,
  },
  menuItemTextDanger: {
    marginLeft: 12,
    fontSize: 16,
    color: "#e53935",
    fontWeight: "500",
  },
});