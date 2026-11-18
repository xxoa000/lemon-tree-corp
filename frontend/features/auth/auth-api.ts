import { json, request } from '../../shared/api';

export type Role = 'member' | 'admin';
export type Session = {
  employee_id: string;
  org_employee_id: string | null;
  role: Role;
};

export const getSession = () => request<Session>('session');
export const createSession = (credentials: object) =>
  request<Session>('session', json('POST', credentials));
export const deleteSession = () => request('session', { method: 'DELETE' });

export const register = (data: object) =>
  request<{ recovery_code: string }>('accounts', json('POST', data));
export const findUsername = (data: object) =>
  request<{ username: string }>('accounts/find', json('POST', data));
export const resetPassword = (data: object) =>
  request<{ recovery_code: string }>('accounts/reset', json('POST', data));
