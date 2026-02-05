import { apiClient } from '@/services/api-client';

export type ProfileType = 'instructor' | 'student';

export interface UserProfileResponse {
  user_id: string;
  email: string;
  type: ProfileType;
  first_name: string;
  last_name: string;
  full_name: string;
  student_number?: string | null;
  bio?: string | null;
  major?: string | null;
}

export const usersService = {
  getMyProfile: () => apiClient.get<UserProfileResponse>('/users/me/profile'),
  changePassword: (newPassword: string) =>
    apiClient.post('/users/me/change-password', { new_password: newPassword }),
};
