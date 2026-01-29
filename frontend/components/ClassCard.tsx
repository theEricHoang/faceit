import { View, Text, Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";

type AttendanceStatus = "Present" | "Absent" | "Late";

type ClassCardProps = {
  courseCode: string;
  section: string;
  schedule: string;
  studentCount?: number;
  attendanceStatus?: AttendanceStatus;
  onPress?: () => void;
};


export default function ClassCard({
  courseCode,
  section,
  schedule,
  studentCount,
  attendanceStatus,
  onPress,
}: ClassCardProps) {
  return (
    <Pressable style={styles.card} onPress={onPress}>
      <View>
        <Text style={styles.title}>
          {courseCode} – Section {section}
        </Text>
        <Text style={styles.subtitle}>{schedule}</Text>
        {studentCount !== undefined && (
          <Text style={styles.meta}>{studentCount} Students</Text>
        )}
        {attendanceStatus && (
            <Text style={styles.meta}>Attendance: {attendanceStatus}</Text>
        )}
      </View>
      <Ionicons name="chevron-forward" size={20} color="#999" />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#eee",
  },
  title: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 4,
  },
  subtitle: {
    color: "#666",
    marginBottom: 4,
  },
  meta: {
    color: "#888",
    fontSize: 12,
  },
});