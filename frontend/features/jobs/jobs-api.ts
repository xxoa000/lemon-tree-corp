import { json, request } from '../../shared/api';

export type Posting = {
  role: string;
  criteria: string;
  title: string;
  team: string;
  duties: string[];
  format: string;
};
export type Evaluation = {
  question_id: string;
  score: number;
  labels: string[];
  criteria: { met: boolean; evidence: string }[];
  feedback: string;
  corrections: { quote: string; correction: string }[];
  model_answer: string;
};
export type History = {
  application: Application;
  answers: {
    question_id: string;
    prompt: string;
    answer: string;
    score: number;
    evaluation: Evaluation | null;
  }[];
};

export type Application = {
  role: string;
  id: number;
  filename: string;
  stage: string;
  feedback: string;
  created_at: string;
  latest_evaluation: Evaluation | null;
  latest_answer: string | null;
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

export const prepareQuestion = (id: number) =>
  request<Application>(`jobs/applications/${id}/question`, { method: 'POST' });

export const interviewHistory = (id: number) =>
  request<History>(`jobs/applications/${id}/history`);
export const stages: Record<string, string> = {
  screen_failed: '서류 불합격',
  technical: '1차 기술 면접',
  technical_failed: '기술 면접 불합격',
  behavioral: '2차 인성 면접',
  behavioral_failed: '인성 면접 불합격',
  hired: '최종 합격',
};
