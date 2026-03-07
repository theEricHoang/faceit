import { Stack } from 'expo-router';

export default function ClassLayout() {
  return (
    <Stack>
      <Stack.Screen
        name="index"
        options={{
          title: 'Class Details',
          headerBackTitle: 'Back',
        }}
      />
      <Stack.Screen
        name="take-attendance"
        options={{
          title: 'Take Attendance',
          headerShown: false,
        }}
      />
      <Stack.Screen
        name="review-photos"
        options={{
          title: 'Review Photos',
          headerBackTitle: 'Camera',
        }}
      />
    </Stack>
  );
}
