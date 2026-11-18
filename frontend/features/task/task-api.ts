import { json, request } from '../../shared/api';

export const statuses = {
  todo: '할 일',
  in_progress: '진행 중',
  done: '완료',
} as const;
export type Status = keyof typeof statuses;
export type Task = {
  id: string;
  title: string;
  description: string;
  assignee_id: string;
  status: Status;
};

export const getTasks = () => request<Task[]>('tasks');
export const updateTask = (task: Task, status: Status) =>
  request<Task>('tasks/' + task.id, json('PATCH', { status }));
