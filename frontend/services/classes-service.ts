import { apiClient } from '@/services/api-client';

// Types matching backend schemas
export interface ClassItem {
  class_id: string;
  course_code: string;
  course_name: string;
  section: string;
  term: string;
  schedule: string;
  room: string | null;
}

export interface ListClassesResponse {
  classes: ClassItem[];
}

export interface CreateClassRequest {
  course_code: string;
  course_name: string;
  section: string;
  term: string;
  schedule: string;
  room?: string | null;
}

export interface CreateClassResponse {
  class_id: string;
  course_code: string;
  course_name: string;
  section: string;
  term: string;
}

export interface JoinClassRequest {
  course_code: string;
}

export interface JoinClassResponse {
  class_id: string;
  student_id: string;
  course_name: string;
  section: string;
}

export interface ClassDetailResponse {
  class_id: string;
  course_code: string;
  course_name: string;
  section: string;
  schedule: string;
  room: string | null;
  instructor_name: string;
}

export interface WithdrawClassResponse {
  class_id: string;
  student_id: string;
}

/**
 * Get all classes for the current authenticated user
 * Returns instructor's classes or student's enrolled classes based on user type
 */
export async function getClasses(): Promise<ListClassesResponse> {
  return apiClient.get<ListClassesResponse>('/classes');
}

/**
 * Get all classes available (Open Classes)
 */
export async function getOpenClasses(): Promise<ListClassesResponse> {
  return apiClient.get<ListClassesResponse>('/classes/open');
}

/**
 * Create a new class (instructor only)
 */
export async function createClass(data: CreateClassRequest): Promise<CreateClassResponse> {
  return apiClient.post<CreateClassResponse>('/classes', data);
}

/**
 * Join a class by course code (student only)
 */
export async function joinClassByCode(data: JoinClassRequest): Promise<JoinClassResponse> {
  return apiClient.post<JoinClassResponse>('/classes/join', data);
}

/**
 * Get class details by id including instructor name
 */
export async function getClassDetails(classId: string): Promise<ClassDetailResponse> {
  return apiClient.get<ClassDetailResponse>(`/classes/${classId}`);
}

/**
 * Withdraw current student from a class
 */
export async function withdrawFromClass(classId: string): Promise<WithdrawClassResponse> {
  return apiClient.delete<WithdrawClassResponse>(`/classes/${classId}/withdraw`);
}
