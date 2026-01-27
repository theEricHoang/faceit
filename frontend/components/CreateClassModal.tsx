import { useState, useEffect } from "react";
import {
  View,
  Text,
  TextInput,
  Modal,
  Pressable,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
} from "react-native";

interface CreateClassModalProps {
  visible: boolean;
  onClose: () => void;
}

export default function CreateClassModal({
  visible,
  onClose,
}: CreateClassModalProps) {
  const [courseCode, setCourseCode] = useState("");
  const [courseName, setCourseName] = useState("");
  const [section, setSection] = useState("");
  const [term, setTerm] = useState("");
  const [schedule, setSchedule] = useState("");
  const [room, setRoom] = useState("");

  useEffect(() => {
    if (visible) {
      setCourseCode("");
      setCourseName("");
      setSection("");
      setTerm("");
      setSchedule("");
      setRoom("");
    }
  }, [visible]);

  const handleSubmit = () => {
    // TODO: call backend
    onClose();
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <Pressable style={styles.backdrop} onPress={onClose} />
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : "height"}
          style={{ flex: 1, justifyContent: "flex-end" }}
        >
          <View style={[styles.sheet, { maxHeight: undefined, minHeight: 0 }]}>
            <Text style={styles.title}>Create Class</Text>
            <Input
              placeholder="Course Code (e.g. CSC4352)"
              value={courseCode}
              onChangeText={setCourseCode}
            />
            <Input
              placeholder="Course Name"
              value={courseName}
              onChangeText={setCourseName}
            />
            <Input
              placeholder="Section"
              value={section}
              onChangeText={setSection}
            />
            <Input
              placeholder="Term (e.g. Spring 2026)"
              value={term}
              onChangeText={setTerm}
            />
            <Input
              placeholder="Schedule"
              value={schedule}
              onChangeText={setSchedule}
            />
            <Input
              placeholder="Room"
              value={room}
              onChangeText={setRoom}
            />
            <View style={styles.actions}>
              <Pressable style={styles.cancelButton} onPress={onClose}>
                <Text style={styles.cancelText}>Cancel</Text>
              </Pressable>
              <Pressable style={styles.primaryButton} onPress={handleSubmit}>
                <Text style={styles.primaryText}>Create Class</Text>
              </Pressable>
            </View>
          </View>
        </KeyboardAvoidingView>
      </View>
    </Modal>
  );
}

function Input(props: {
  placeholder: string;
  value: string;
  onChangeText: (text: string) => void;
}) {
  return (
    <TextInput
      {...props}
      placeholderTextColor="#888"
      style={styles.input}
    />
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: "flex-end",
  },
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0,0,0,0.4)",
  },
  sheet: {
    backgroundColor: "#fff",
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 24,
  },
  title: {
    fontSize: 20,
    fontWeight: "700",
    textAlign: "center",
    marginBottom: 16,
  },
  input: {
    backgroundColor: "#f3f3f3",
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    marginBottom: 12,
  },
  actions: {
    flexDirection: "row",
    gap: 12,
    marginTop: 12,
  },
  cancelButton: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 12,
    backgroundColor: "#e5e5e5",
    alignItems: "center",
  },
  cancelText: {
    fontSize: 16,
    fontWeight: "600",
  },
  primaryButton: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 12,
    backgroundColor: "#000",
    alignItems: "center",
  },
  primaryText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
});
