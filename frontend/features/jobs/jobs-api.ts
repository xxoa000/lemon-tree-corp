import { json, request } from '../../shared/api';

export type Posting = {
  role: string;
  criteria: string;
  title: string;
  team: string;
  duties: string[];
  format: string;
};
export type Application = {
  role: string;
  id: number;
  filename: string;
  stage: string;
  feedback: string;
  created_at: string;
  question: { id: string; interviewer: string; prompt: string } | null;
};

export const getPostings = () => request<Posting[]>('jobs/postings');
export const getApplications = () =>
  request<Application[]>('jobs/applications');
export const apply = (data: FormData) =>
  request<Application>('jobs/applications', { method: 'POST', body: data });
export const answerQuestion = (
  id: number,
  questionId: string,
  answer: string,
) =>
  request<Application>(
    `jobs/applications/${id}/answers`,
    json('POST', { question_id: questionId, answer }),
  );
