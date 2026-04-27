export interface ApiError {
  status: number;
  code?: string;
  message: string;
  details?: unknown;
}

const API_BASE_URL = 'http://localhost:5000/api';

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
    ...init,
  });

  if (!response.ok) {
    const error: ApiError = {
      status: response.status,
      message: `Request failed with status ${response.status}`,
    };
    throw error;
  }

  return response.json() as Promise<T>;
}
