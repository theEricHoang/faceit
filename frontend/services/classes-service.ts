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
  section: string;
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

export interface UploadUrlResponse {
  upload_url: string;
  bucket: string;
  key: string;
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
 * Join a class by section (student only)
 */
export async function joinClassBySection(data: JoinClassRequest): Promise<JoinClassResponse> {
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

/**
 * Get a presigned S3 upload URL for an attendance photo (instructor only)
 */
export async function getAttendanceUploadUrl(classId: string): Promise<UploadUrlResponse> {
  return apiClient.post<UploadUrlResponse>(`/classes/${classId}/attendance/upload-url`);
}

/**
 * Upload a photo to S3 using a presigned URL.
 * Reads the local file URI as a blob and PUTs it directly to S3.
 */
export async function uploadPhotoToS3(presignedUrl: string, photoUri: string): Promise<void> {
  const response = await fetch(photoUri);
  const blob = await response.blob();

  const uploadResponse = await fetch(presignedUrl, {
    method: 'PUT',
    body: blob,
    headers: {
      'Content-Type': 'image/jpeg',
    },
  });

  if (!uploadResponse.ok) {
    throw new Error(`S3 upload failed with status ${uploadResponse.status}`);
  }
}
