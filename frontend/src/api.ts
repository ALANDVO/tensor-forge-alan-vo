/** Typed client for the tensor-forge backend API.

The envelope mirrors the FastAPI response models in `backend/app/models/schema.py`
so the frontend never trusts an un-typed shape.
*/
export interface ArgumentSchema {
  name: string;
  py_type: string;
  cli_type: string;
  required: boolean;
  default: string | null;
  help: string;
}

export interface CommandSchema {
  name: string;
  kind: string;
  docstring: string;
  location: string;
  rendered: string;
  arguments: ArgumentSchema[];
}

export interface ForgeResponse {
  program_name: string;
  language: string;
  commands: CommandSchema[];
  error: string | null;
}

export interface ForgeRequest {
  source: string;
  program_name: string;
  language?: string;
}

/** Base URL for the API. In dev this is proxied to the backend. */
export const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export class ForgeError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ForgeError";
  }
}

/** Submit source code and receive a forged CLI manifest. */
export async function forgeSource(req: ForgeRequest): Promise<ForgeResponse> {
  const res = await fetch(`${API_BASE}/forge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      // non-JSON error body
    }
    throw new ForgeError(detail);
  }
  return res.json() as Promise<ForgeResponse>;
}

export const ForgeAPI = { forgeSource };