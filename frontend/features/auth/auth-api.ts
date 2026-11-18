import { json, request } from '../../shared/api';

export type Session = { employee_id: string };

export const getSession = () => request<Session>('session');
export const createSession = (credentials: object) =>
  request<Session>('session', json('POST', credentials));
export const deleteSession = () => request('session', { method: 'DELETE' });
