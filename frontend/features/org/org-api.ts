import { request } from '../../shared/api';

export type Employee = {
  id: string;
  name: string;
  team: string;
  rank: string;
  job_title: string;
  specialty: string;
};
export type Manager = {
  id: string;
  name: string;
  rank: string;
  job_title: string;
};
export type Team = { name: string; leader_id: string; member_ids: string[] };

export const getEmployees = () => request<Employee[]>('employees');
export const getTeams = () => request<Team[]>('teams');
export const getManager = () => request<Manager>('control-center/manager');
