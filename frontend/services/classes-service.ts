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

/**
 * Get all classes for the current authenticated user
 * Returns instructor's classes or student's enrolled classes based on user type
 */
export async function getClasses(): Promise<ListClassesResponse> {
  return apiClient.get<ListClassesResponse>('/classes');
}

/**
 * Create a new class (instructor only)
 */
export async function createClass(data: CreateClassRequest): Promise<CreateClassResponse> {
  return apiClient.post<CreateClassResponse>('/classes', data);
}
