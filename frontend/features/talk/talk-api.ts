import { json, request } from '../../shared/api';

export type Contact = { id: number; name: string; employee_id: string | null };
export type Room = {
  id: number;
  name: string;
  team: string | null;
  owner: boolean;
  latest: number;
  earliest: number;
  participants: number;
  unread: number;
};
export type Message = {
  id: number;
  sender: number;
  name: string;
  body: string;
  sent_at: string;
  simulated: boolean;
};
export type Conversation = {
  me: number;
  members: Contact[];
  messages: Message[];
  has_more: boolean;
};

export const contacts = () => request<Contact[]>('talk/contacts');
export const rooms = () => request<Room[]>('talk/rooms');
export const conversation = (id: number, before?: number) =>
  request<Conversation>(`talk/rooms/${id}${before ? '?before=' + before : ''}`);
export const openDm = (contact: number) =>
  request<{ id: number }>('talk/dm', json('POST', { contact }));
export const createGroup = (data: object) =>
  request<{ id: number }>('talk/groups', json('POST', data));
export const sendMessage = (id: number, body: string) =>
  request<{ id: number; mock: string }>(
    `talk/rooms/${id}/messages`,
    json('POST', { body }),
  );
export const markRead = (id: number, message_id: number) =>
  request(`talk/rooms/${id}/read`, json('POST', { message_id }));
export const changeMember = (id: number, contact: number, remove: boolean) =>
  request(`talk/rooms/${id}/members/${contact}`, {
    method: remove ? 'DELETE' : 'PUT',
  });
