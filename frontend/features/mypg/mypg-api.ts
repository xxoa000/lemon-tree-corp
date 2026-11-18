import type { Role } from '../auth/auth-api';
import { json, request } from '../../shared/api';

export type Profile = {
  username: string;
  display_name: string;
  email: string;
  phone: string;
  bio: string;
  role: Role;
  has_avatar: boolean;
};

type Staff = {
  employee_id: string;
  username: string;
  display_name: string;
  role: Role;
  enabled: boolean;
};

export const getProfile = () => request<Profile>('accounts/me');
export const saveProfile = (data: object) =>
  request<Profile>('accounts/me', json('PATCH', data));
export const uploadAvatar = (body: FormData) =>
  request('accounts/me/avatar', { method: 'PUT', body });
export const getStaff = () => request<Staff[]>('accounts/staff');
