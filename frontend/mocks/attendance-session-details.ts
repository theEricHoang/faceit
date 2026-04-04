export type MockInstructorSession = {
  id: string;
  date: string;
  presentCount: number;
  totalStudents: number;
  unknownCount: number;
};

export type MockAttendanceStudent = {
  studentId: string;
  firstName: string;
  lastName: string;
  status: 'present' | 'absent';
  confidence: number | null;
};

export type MockAttendanceSessionDetails = {
  sessionId: string;
  classId: string;
  createdAt: string;
  date: string;
  presentCount: number;
  absentCount: number;
  unknownCount: number;
  students: MockAttendanceStudent[];
};

const TOTAL_STUDENTS = 50;

const FIRST_NAMES = [
  'Ava',
  'Liam',
  'Mia',
  'Noah',
  'Ella',
  'Lucas',
  'Grace',
  'Ethan',
  'Chloe',
  'Mason',
];

const LAST_NAMES = ['Reyes', 'Santos', 'Garcia', 'Lim', 'Tan'];

const SESSION_CONFIGS = [
  { id: '2025-09-29-session', date: '2025-09-29', unknownCount: 1, absentNumbers: [3, 7, 11, 18, 22, 25, 29, 34, 39, 45, 47, 50] },
  { id: '2025-10-02-session', date: '2025-10-02', unknownCount: 2, absentNumbers: [2, 6, 9, 15, 19, 23, 31, 40, 44] },
  { id: '2025-10-04-session', date: '2025-10-04', unknownCount: 1, absentNumbers: [5, 8, 14, 24, 32, 41, 48] },
  { id: '2025-10-06-session', date: '2025-10-06', unknownCount: 3, absentNumbers: [1, 4, 10, 13, 17, 21, 27, 33, 36, 42, 49] },
  { id: '2025-10-09-session', date: '2025-10-09', unknownCount: 2, absentNumbers: [12, 16, 20, 26, 30, 35, 37, 46] },
  { id: '2025-10-11-session', date: '2025-10-11', unknownCount: 1, absentNumbers: [6, 18, 28, 38, 43, 50] },
  { id: '2025-10-13-session', date: '2025-10-13', unknownCount: 2, absentNumbers: [2, 7, 11, 15, 24, 29, 31, 40, 45, 48] },
  { id: '2025-10-16-session', date: '2025-10-16', unknownCount: 1, absentNumbers: [4, 9, 21, 33] },
  { id: '2025-10-18-session', date: '2025-10-18', unknownCount: 2, absentNumbers: [5, 12, 17, 22, 28, 36, 41, 47, 49] },
  { id: '2025-10-20-session', date: '2025-10-20', unknownCount: 1, absentNumbers: [3, 14, 19, 26, 32] },
] as const;

const MOCK_ROSTER = Array.from({ length: TOTAL_STUDENTS }, (_, index) => {
  const number = index + 1;
  const firstName = FIRST_NAMES[index % FIRST_NAMES.length];
  const lastName = LAST_NAMES[Math.floor(index / FIRST_NAMES.length) % LAST_NAMES.length];

  return {
    studentId: `student-${String(number).padStart(3, '0')}`,
    firstName,
    lastName,
  };
});

export const MOCK_INSTRUCTOR_SESSIONS: MockInstructorSession[] = SESSION_CONFIGS.map((session) => ({
  id: session.id,
  date: session.date,
  presentCount: TOTAL_STUDENTS - session.absentNumbers.length,
  totalStudents: TOTAL_STUDENTS,
  unknownCount: session.unknownCount,
}));

export function getMockAttendanceSessionDetails(
  classId: string,
  sessionId: string,
): MockAttendanceSessionDetails | null {
  const session = SESSION_CONFIGS.find((item) => item.id === sessionId);

  if (!session) {
    return null;
  }

  const absentSet = new Set(session.absentNumbers);
  const students: MockAttendanceStudent[] = MOCK_ROSTER.map((student, index) => {
    const studentNumber = index + 1;
    const status = absentSet.has(studentNumber) ? 'absent' : 'present';
    const confidence =
      status === 'present'
        ? Number((0.86 + ((studentNumber % 9) * 0.013)).toFixed(2))
        : null;

    return {
      studentId: student.studentId,
      firstName: student.firstName,
      lastName: student.lastName,
      status,
      confidence,
    };
  });

  const presentCount = students.filter((student) => student.status === 'present').length;

  return {
    sessionId: session.id,
    classId,
    createdAt: `${session.date}T09:00:00Z`,
    date: session.date,
    presentCount,
    absentCount: TOTAL_STUDENTS - presentCount,
    unknownCount: session.unknownCount,
    students,
  };
}
