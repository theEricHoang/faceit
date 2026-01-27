import { useState } from "react";
import {
  View,
  Text,
  ScrollView,
  TextInput,
  Pressable,
  StyleSheet,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import ClassCard from "../../components/ClassCard";
import { SafeAreaView } from "react-native-safe-area-context";

export default function HomeScreen() {
  const [searchQuery, setSearchQuery] = useState("");

  const classes = [
    {
      id: 1,
      courseCode: "CS101",
      section: "A",
      schedule: "M-W 10:00AM - 11:15AM",
      studentCount: 35,
    },
    {
      id: 2,
      courseCode: "CS102",
      section: "B",
      schedule: "T-Th 2:00PM - 3:15PM",
      studentCount: 42,
    },
    {
      id: 3,
      courseCode: "CS201",
      section: "A",
      schedule: "M-W-F 9:00AM - 9:50AM",
      studentCount: 28,
    },
    {
      id: 4,
      courseCode: "CS301",
      section: "C",
      schedule: "T-Th 11:00AM - 12:15PM",
      studentCount: 31,
    },
    {
      id: 5,
      courseCode: "CS150",
      section: "A",
      schedule: "M-W 1:00PM - 2:15PM",
      studentCount: 38,
    },
  ];

  const filteredClasses = classes.filter((cls) =>
    `${cls.courseCode} ${cls.section}`
      .toLowerCase()
      .includes(searchQuery.toLowerCase())
  );

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>FaceIT</Text>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>WJ</Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {/* Class list header */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>My Classes</Text>
          <Pressable style={styles.addButton}>
            <Ionicons name="add" size={20} color="#fff" />
          </Pressable>
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

        {/* Class list */}
        {filteredClasses.map((cls) => (
          <ClassCard
            key={cls.id}
            courseCode={cls.courseCode}
            section={cls.section}
            schedule={cls.schedule}
            studentCount={cls.studentCount}
          />
        ))}
      </ScrollView>
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
});