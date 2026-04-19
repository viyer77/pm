export type ApiColumn = {
  id: number;
  board_id: number;
  title: string;
  position: number;
};

export type ApiCard = {
  id: number;
  column_id: number;
  title: string;
  description: string;
  position: number;
};

export type ApiBoard = {
  id: number;
  title: string;
  columns: ApiColumn[];
  cards: ApiCard[];
};

type RetryOptions = {
  retries?: number;
  retryDelayMs?: number;
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const DEFAULT_RETRIES = 2;
const DEFAULT_RETRY_DELAY_MS = 200;

const sleep = (ms: number) =>
  new Promise((resolve) => {
    setTimeout(resolve, ms);
  });

const shouldRetryStatus = (status: number) => status >= 500 || status === 429;

async function requestJson<T>(
  input: string,
  init: RequestInit = {},
  options: RetryOptions = {}
): Promise<T> {
  const retries = options.retries ?? DEFAULT_RETRIES;
  const retryDelayMs = options.retryDelayMs ?? DEFAULT_RETRY_DELAY_MS;
  let attempt = 0;
  let lastError: unknown = null;

  while (attempt <= retries) {
    try {
      const response = await fetch(input, {
        ...init,
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(init.headers ?? {}),
        },
      });

      if (response.ok) {
        if (response.status === 204) {
          return undefined as T;
        }
        return (await response.json()) as T;
      }

      const message = response.statusText || "Request failed";
      const error = new ApiError(message, response.status);
      if (attempt < retries && shouldRetryStatus(response.status)) {
        attempt += 1;
        await sleep(retryDelayMs * attempt);
        continue;
      }
      throw error;
    } catch (error) {
      lastError = error;
      if (error instanceof ApiError) {
        throw error;
      }
      // Don't retry if request was intentionally aborted
      if (init.signal?.aborted) {
        throw new ApiError("Request aborted", 0);
      }
      if (attempt >= retries) {
        throw new ApiError("Network error", 0);
      }
      attempt += 1;
      await sleep(retryDelayMs * attempt);
    }
  }

  if (lastError instanceof ApiError) {
    throw lastError;
  }
  throw new ApiError("Request failed", 0);
}

export const api = {
  getBoard: () => requestJson<ApiBoard>("/api/boards", { method: "GET" }),
  renameColumn: (columnId: number, title: string) =>
    requestJson<ApiColumn>("/api/columns", {
      method: "POST",
      body: JSON.stringify({ column_id: columnId, title }),
    }),
  createCard: (columnId: number, title: string, description: string) =>
    requestJson<ApiCard>("/api/cards", {
      method: "POST",
      body: JSON.stringify({ column_id: columnId, title, description }),
    }),
  updateCard: (cardId: number, payload: { title?: string; description?: string }) =>
    requestJson<ApiCard>(`/api/cards/${cardId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteCard: (cardId: number) =>
    requestJson<{ success: boolean }>(`/api/cards/${cardId}`, {
      method: "DELETE",
    }),
  moveCard: (cardId: number, columnId: number, position: number) =>
    requestJson<ApiCard>(`/api/cards/${cardId}/move`, {
      method: "PUT",
      body: JSON.stringify({ column_id: columnId, position }),
    }),
  chatAI: (message: string, signal?: AbortSignal) =>
    requestJson<{ response: string; actions_executed: number }>("/api/ai/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
      signal,
    }),
  clearChatAI: () =>
    requestJson<{ cleared: boolean }>("/api/ai/chat", { method: "DELETE" }),
};

