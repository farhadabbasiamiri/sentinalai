const BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new Error(payload?.detail ?? `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export type Agent = {
  agent_id: string; name: string; description: string; owner: string | null; status: string
  created_at: string; last_activity: string | null; tools: string[]; permissions: string[]; scopes: string[]
  data_categories: string[]; sensitivity: string; approval_required: boolean; risk_score: number
  risk_level: string; last_review: string | null; events?: { action: string; sensitive?: boolean; approved?: boolean }[]
}
export type Finding = {
  finding_id: string; agent_id: string; rule_id: string; severity: string; title: string; evidence: string[]
  rationale: string; remediation: string; approval_required: boolean; status: string; created_at: string
}
export type Approval = {
  approval_id: string; agent_id: string; finding_id: string | null; change_type: string
  current_configuration: Record<string, unknown>; proposed_change: Record<string, unknown>; rationale: string
  evidence: string[]; status: string; reviewer: string | null; decision_at: string | null; applied_at: string | null
}
export type AuditEvent = { event_id: string; action: string; object_type: string; object_id: string | null; details: Record<string, unknown>; created_at: string }
export type Summary = {
  total_agents: number; risk_distribution: Record<string, number>; open_findings: number
  over_privileged_agents: number; pending_approvals: number; sensitive_findings: number
  findings_by_category: Record<string, number>; highest_risk_agents: Agent[]; recent_events: AuditEvent[]
}
export type Page<T> = { items: T[]; total: number; page: number; page_size: number; pages?: number }

export const api = {
  health: () => request<{ status: string; version: string; ai_mode: string }>('/health'),
  ready: () => request<{ ready: boolean; agents: number; database: string }>('/ready'),
  summary: () => request<Summary>('/summary'),
  agents: (params: URLSearchParams) => request<Page<Agent>>(`/agents?${params}`),
  agent: (id: string) => request<Agent & { findings: Finding[] }>(`/agents/${id}`),
  evaluate: (id: string) => request<{ findings: Finding[]; risk_score: number; risk_level: string }>(`/agents/${id}/evaluate`, { method: 'POST' }),
  findings: (params: URLSearchParams) => request<Page<Finding>>(`/findings?${params}`),
  markReviewed: (id: string) => request<Finding>(`/findings/${id}/review`, { method: 'PATCH' }),
  policies: () => request<{ rules: { rule_id: string; title: string; severity: string; description: string }[]; document: string }>('/policies'),
  searchPolicy: (q: string) => request<{ results: { source: string; section: string; excerpt: string; retrieval: string }[] }>(`/policies/search?q=${encodeURIComponent(q)}`),
  review: (requestText: string) => request<Record<string, any>>('/reviews', { method: 'POST', body: JSON.stringify({ request: requestText }) }),
  approvals: () => request<{ items: Approval[] }>('/approvals'),
  propose: (agentId: string, body: Record<string, unknown>) => request<Approval>(`/agents/${agentId}/proposals`, { method: 'POST', body: JSON.stringify(body) }),
  decide: (id: string, decision: 'approve' | 'reject', reviewer: string) => request<Approval>(`/approvals/${id}/decision?decision=${decision}`, { method: 'POST', body: JSON.stringify({ reviewer }) }),
  apply: (id: string, reviewer: string) => request<Record<string, unknown>>(`/approvals/${id}/apply`, { method: 'POST', body: JSON.stringify({ reviewer, confirmation: true }) }),
  audit: (params: URLSearchParams) => request<Page<AuditEvent>>(`/audit?${params}`),
  evaluation: () => request<Record<string, any>>('/evaluation'),
}

export function download(path: string) { window.open(`${BASE}${path}`, '_blank', 'noopener,noreferrer') }
