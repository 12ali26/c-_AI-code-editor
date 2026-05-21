const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/backend";

export type Project = {
  id: string;
  name: string;
  description?: string | null;
  review_status: string;
  created_at: string;
};

export type Dataset = {
  id: string;
  project_id: string;
  filename: string;
  value_type: string;
  triangle_basis: string;
  development_columns: string[];
  created_at: string;
};

export type TriangleDetail = {
  dataset_id: string;
  triangle_id: string;
  triangle_basis: string;
  origin_periods: string[];
  development_periods: string[];
  source_values: (number | null)[][];
  values: (number | null)[][];
  validation_warnings: string[];
};

export type ReservingResult = {
  latest_diagonal: number[];
  age_to_age_factors: number[];
  cumulative_development_factors: number[];
  link_ratio_triangle: (number | null)[][];
  projected_cumulative_triangle: (number | null)[][];
  incremental_triangle: (number | null)[][];
  factor_diagnostics: Record<string, number | string>[];
  ultimate_by_origin: number[];
  ibnr_by_origin: number[];
  total_latest: number;
  total_ultimate: number;
  total_ibnr: number;
  diagnostics: Record<string, unknown>;
};

export type ModelRun = {
  id: string;
  project_id: string;
  dataset_id: string;
  method: string;
  status: string;
  result: ReservingResult;
  created_at: string;
};

export type AuditEvent = {
  id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  details: Record<string, unknown>;
  created_at: string;
};

export type ExportJob = {
  id: string;
  export_type: "excel" | "pdf";
  file_path: string;
  status: string;
};

export type SystemStatus = {
  database_backend: string;
  database_url: string;
  persistence: string;
};

export type RunPayload = {
  method: string;
  assumption_name?: string;
  selected_factors?: number[];
  exposure_values?: number[];
  expected_loss_ratio?: number;
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "X-Org-Id": "demo-org",
      "X-User-Id": "demo-user",
      ...(options?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...options?.headers
    }
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const errorBody = await response.json();
      detail = errorBody.detail ?? detail;
    } catch {
      // Keep the status text when the response is not JSON.
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export function listProjects() {
  return request<Project[]>("/projects");
}

export function getSystemStatus() {
  return request<SystemStatus>("/system/status");
}

export function createProject(name: string) {
  return request<Project>("/projects", {
    method: "POST",
    body: JSON.stringify({ name })
  });
}

export async function deleteProject(projectId: string) {
  await request<void>(`/projects/${projectId}`, {
    method: "DELETE"
  });
}

export function listProjectDatasets(projectId: string) {
  return request<Dataset[]>(`/projects/${projectId}/datasets`);
}

export function listProjectRuns(projectId: string) {
  return request<ModelRun[]>(`/projects/${projectId}/runs`);
}

export function listProjectAuditEvents(projectId: string) {
  return request<AuditEvent[]>(`/projects/${projectId}/audit-events`);
}

export function getTriangle(datasetId: string) {
  return request<TriangleDetail>(`/datasets/${datasetId}/triangle`);
}

export function uploadDataset(
  projectId: string,
  file: File,
  valueType: string,
  triangleBasis: string
) {
  const body = new FormData();
  body.append("file", file);
  const params = new URLSearchParams({
    value_type: valueType,
    triangle_basis: triangleBasis
  });
  return request<Dataset>(`/projects/${projectId}/datasets?${params.toString()}`, {
    method: "POST",
    body
  });
}

export function createRun(datasetId: string, payload: RunPayload) {
  return request<ModelRun>(`/datasets/${datasetId}/runs`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function createExport(runId: string, exportType: "excel" | "pdf") {
  return request<ExportJob>(`/runs/${runId}/exports`, {
    method: "POST",
    body: JSON.stringify({ export_type: exportType })
  });
}
