export class RequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch('/api/v1/' + path, options);
  if (!response.ok) {
    const { detail } = await response.json().catch(() => ({}));
    throw new RequestError(
      typeof detail === 'string' ? detail : '요청을 처리하지 못했습니다.',
      response.status,
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export function json(method: string, data: object): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  };
}
