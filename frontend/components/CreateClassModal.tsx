import { useState } from "react";
import {
  View,
  Text,
  TextInput,
  Button,
  Modal,
  StyleSheet,
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
        <View style={styles.modal}>
          <Text style={styles.title}>Create Class</Text>

          <TextInput style={styles.input} placeholder="Course Code" placeholderTextColor="#999" value={courseCode} onChangeText={setCourseCode} />
          <TextInput style={styles.input} placeholder="Course Name" placeholderTextColor="#999" value={courseName} onChangeText={setCourseName} />
          <TextInput style={styles.input} placeholder="Section" placeholderTextColor="#999" value={section} onChangeText={setSection} />
          <TextInput style={styles.input} placeholder="Term" placeholderTextColor="#999" value={term} onChangeText={setTerm} />
          <TextInput style={styles.input} placeholder="Schedule" placeholderTextColor="#999" value={schedule} onChangeText={setSchedule} />
          <TextInput style={styles.input} placeholder="Room" placeholderTextColor="#999" value={room} onChangeText={setRoom} />

          <View style={styles.actions}>
            <Button title="Cancel" onPress={onClose} />
            <Button title="Create" onPress={handleSubmit} />
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.5)",
    justifyContent: "center",
    alignItems: "center",
  },
  modal: {
    width: "90%",
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
  },
  title: {
    fontSize: 18,
    fontWeight: "600",
    marginBottom: 12,
    textAlign: "center",
  },
  input: {
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 8,
    padding: 10,
    marginBottom: 10,
  },
  actions: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 12,
  },
});
