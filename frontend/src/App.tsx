import { useEffect, useState } from "react";
import {
  Activity,
  ArrowDownToLine,
  ArrowLeft,
  Bot,
  Check,
  ChevronRight,
  CircleHelp,
  ClipboardCheck,
  Database,
  FileText,
  Fingerprint,
  Gauge,
  KeyRound,
  LayoutDashboard,
  LoaderCircle,
  LockKeyhole,
  RefreshCw,
  Search,
  Settings,
  Shield,
  ShieldAlert,
  Sparkles,
  X,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  api,
  download,
  type Agent,
  type Approval,
  type AuditEvent,
  type Finding,
  type Summary,
} from "./api";

type PageName =
  | "Overview"
  | "Agent registry"
  | "Agent details"
  | "Governance findings"
  | "Policy explorer"
  | "Activity & audit"
  | "Approval queue"
  | "Reports & evaluation"
  | "Settings";
const navigation: { name: PageName; icon: typeof Gauge }[] = [
  { name: "Overview", icon: LayoutDashboard },
  { name: "Agent registry", icon: Bot },
  { name: "Agent details", icon: Fingerprint },
  { name: "Governance findings", icon: ShieldAlert },
  { name: "Policy explorer", icon: FileText },
  { name: "Activity & audit", icon: Activity },
  { name: "Approval queue", icon: ClipboardCheck },
  { name: "Reports & evaluation", icon: ArrowDownToLine },
  { name: "Settings", icon: Settings },
];
const riskColors: Record<string, string> = {
  low: "#a5d369",
  medium: "#dfc66d",
  high: "#f09a60",
  critical: "#eb7470",
};
const categoryNames: Record<string, string> = {
  "GOV-001": "Purpose mismatch",
  "GOV-002": "Broad scopes",
  "GOV-003": "Sensitive data",
  "GOV-004": "Tool combinations",
  "GOV-005": "Missing owner",
  "GOV-006": "Stale access",
  "GOV-007": "Admin capability",
  "GOV-008": "Approval gap",
  "GOV-009": "Duty conflict",
  "GOV-010": "Unapproved activity",
};

function Badge({ value }: { value: string }) {
  return (
    <span className={`badge ${value.toLowerCase()}`}>
      {value.replaceAll("_", " ")}
    </span>
  );
}
function Stat({
  label,
  value,
  note,
  icon: Icon,
  color,
}: {
  label: string;
  value: string | number;
  note: string;
  icon: typeof Gauge;
  color?: string;
}) {
  return (
    <div className="stat-card">
      <div className="stat-top">
        <span>{label}</span>
        <Icon style={{ color }} />
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-note">{note}</div>
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState<PageName>("Overview");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [audits, setAudits] = useState<AuditEvent[]>([]);
  const [rules, setRules] = useState<
    { rule_id: string; title: string; severity: string; description: string }[]
  >([]);
  const [selected, setSelected] = useState<
    (Agent & { findings?: Finding[] }) | null
  >(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [agentQuery, setAgentQuery] = useState("");
  const [ownerFilter, setOwnerFilter] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sensitivityFilter, setSensitivityFilter] = useState("");
  const [findingSeverity, setFindingSeverity] = useState("");
  const [findingStatus, setFindingStatus] = useState("open");
  const [policyQuery, setPolicyQuery] = useState("least privilege");
  const [policyMatches, setPolicyMatches] = useState<
    { source: string; section: string; excerpt: string }[]
  >([]);
  const [reviewText, setReviewText] = useState(
    "Review SA-1002 and explain its governance risks.",
  );
  const [reviewResult, setReviewResult] = useState<Record<string, any> | null>(
    null,
  );
  const [evaluation, setEvaluation] = useState<Record<string, any> | null>(
    null,
  );
  const [auditFilter, setAuditFilter] = useState("");

  async function loadBase() {
    setLoading(true);
    setError("");
    try {
      const [dash, policyResponse] = await Promise.all([
        api.summary(),
        api.policies(),
      ]);
      setSummary(dash);
      setRules(policyResponse.rules);
      const [agentPage, findingPage, approvalResponse, auditPage] =
        await Promise.all([
          api.agents(
            new URLSearchParams({
              page: "1",
              page_size: "100",
              sort_by: "risk_score",
              order: "desc",
            }),
          ),
          api.findings(new URLSearchParams({ page: "1", page_size: "100" })),
          api.approvals(),
          api.audit(new URLSearchParams({ page: "1", page_size: "100" })),
        ]);
      setAgents(agentPage.items);
      setFindings(findingPage.items);
      setApprovals(approvalResponse.items);
      setAudits(auditPage.items);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Unable to connect to SentinelAI API",
      );
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void loadBase();
    void api
      .evaluation()
      .then(setEvaluation)
      .catch(() => undefined);
  }, []);

  async function refresh() {
    await loadBase();
    if (selected) await openAgent(selected.agent_id);
  }
  async function openAgent(agentId: string) {
    try {
      const item = await api.agent(agentId);
      setSelected(item);
      setPage("Agent details");
      setError("");
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Unable to load agent",
      );
    }
  }
  async function runEvaluation(agentId: string) {
    setBusy(true);
    try {
      await api.evaluate(agentId);
      await refresh();
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Evaluation failed");
    } finally {
      setBusy(false);
    }
  }
  async function loadAgents() {
    const params = new URLSearchParams({
      page: "1",
      page_size: "100",
      sort_by: "risk_score",
      order: "desc",
    });
    if (agentQuery) params.set("q", agentQuery);
    if (ownerFilter) params.set("owner", ownerFilter);
    if (riskFilter) params.set("risk", riskFilter);
    if (statusFilter) params.set("status", statusFilter);
    if (sensitivityFilter) params.set("sensitivity", sensitivityFilter);
    setBusy(true);
    try {
      setAgents((await api.agents(params)).items);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Registry query failed",
      );
    } finally {
      setBusy(false);
    }
  }
  async function loadFindings() {
    const params = new URLSearchParams({ page: "1", page_size: "100" });
    if (findingSeverity) params.set("severity", findingSeverity);
    if (findingStatus) params.set("status", findingStatus);
    setBusy(true);
    try {
      setFindings((await api.findings(params)).items);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Finding query failed",
      );
    } finally {
      setBusy(false);
    }
  }
  async function markReviewed(finding: Finding) {
    try {
      await api.markReviewed(finding.finding_id);
      await refresh();
    } catch (reason) {
      setError(String(reason));
    }
  }
  async function proposeFinding(finding: Finding) {
    const type =
      finding.rule_id === "GOV-002"
        ? "restrict_scope"
        : finding.rule_id === "GOV-003" || finding.rule_id === "GOV-008"
          ? "set_approval"
          : finding.rule_id === "GOV-006"
            ? "deactivate_agent"
            : finding.rule_id === "GOV-001"
              ? "remove_permission"
              : "set_approval";
    const change =
      type === "restrict_scope"
        ? { scope: "*" }
        : type === "remove_permission"
          ? { permission: "delete_records" }
          : type === "deactivate_agent"
            ? { status: "inactive" }
            : { required: true };
    try {
      await api.propose(finding.agent_id, {
        finding_id: finding.finding_id,
        change_type: type,
        proposed_change: change,
        rationale: finding.remediation,
        evidence: finding.evidence,
      });
      await refresh();
      setPage("Approval queue");
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Could not create proposal",
      );
    }
  }
  async function decide(item: Approval, decision: "approve" | "reject") {
    try {
      await api.decide(item.approval_id, decision, "Security reviewer");
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Decision failed");
    }
  }
  async function apply(item: Approval) {
    if (
      !window.confirm(
        "Apply this change to the synthetic agent record? This does not affect any external system.",
      )
    )
      return;
    try {
      await api.apply(item.approval_id, "Security reviewer");
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Simulation failed");
    }
  }
  async function searchPolicies() {
    try {
      setPolicyMatches((await api.searchPolicy(policyQuery)).results);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Policy search failed",
      );
    }
  }
  async function runReview(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setReviewResult(null);
    try {
      setReviewResult(await api.review(reviewText));
      setError("");
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Review failed");
    } finally {
      setBusy(false);
    }
  }
  async function loadAudit() {
    const params = new URLSearchParams({ page: "1", page_size: "100" });
    if (auditFilter) params.set("action", auditFilter);
    try {
      setAudits((await api.audit(params)).items);
    } catch (reason) {
      setError(String(reason));
    }
  }

  const nav = (
    <div className="nav-list">
      {navigation.map(({ name, icon: Icon }) => (
        <button
          key={name}
          className={`nav-item ${page === name ? "active" : ""}`}
          onClick={() => setPage(name)}
        >
          <Icon />
          <span>{name}</span>
        </button>
      ))}
    </div>
  );
  const headingCopy: Record<PageName, string> = {
    Overview: "A live posture view across your synthetic agent inventory.",
    "Agent registry":
      "Search, compare, and inspect registered agent capabilities.",
    "Agent details":
      "Permission inventory, activity evidence, and deterministic analysis.",
    "Governance findings":
      "Evidence-linked policy matches awaiting analyst review.",
    "Policy explorer": "Local governance rules and traceable policy passages.",
    "Activity & audit":
      "Recorded reviews, tool calls, policy matches, and decisions.",
    "Approval queue": "Review proposed changes before they are simulated.",
    "Reports & evaluation":
      "Export findings and inspect measured evaluation results.",
    Settings: "Local service health and safe configuration status.",
  };
  const headingAction =
    page === "Agent registry" ? (
      <button
        className="btn primary"
        onClick={() => {
          setReviewResult(null);
          setReviewText("Review SA-1002 and explain its governance risks.");
          window.setTimeout(() => {
            const prompt = document.getElementById("review-prompt");
            prompt?.scrollIntoView({ behavior: "smooth", block: "center" });
            prompt?.focus();
          }, 0);
        }}
      >
        <Sparkles /> Run governance review
      </button>
    ) : (
      <button
        className="btn ghost"
        onClick={() => void refresh()}
        aria-label="Refresh dashboard"
      >
        <RefreshCw size={15} /> Refresh
      </button>
    );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">
            <Shield size={19} />
          </span>
          <span>
            <strong>SentinelAI</strong>
            <small>Governance console</small>
          </span>
        </div>
        <div className="nav-label">Workspace</div>
        {nav}
        <div className="sidebar-bottom">
          <div className="system-status">
            <span className="status-dot" /> Local system operational
          </div>
          <small>v1.0.0 · Synthetic environment</small>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div className="breadcrumb">
            SentinelAI{" "}
            <ChevronRight size={13} style={{ verticalAlign: "middle" }} />{" "}
            <b>{page}</b>
          </div>
          <div className="top-actions">
            <span className="top-date">FALL 2026 · CAPSTONE</span>
            <span className="live-pill">
              <span className="status-dot" /> Local mode
            </span>
          </div>
        </header>
        <div className="mobile-nav">{nav}</div>
        <div className="content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">AI Agent Governance / 01</div>
              <h1>{page}</h1>
              <p>{headingCopy[page]}</p>
            </div>
            {headingAction}
          </div>
          {error && (
            <div role="alert" className="error-banner">
              {error}
            </div>
          )}
          {loading ? (
            <div className="loading">
              <LoaderCircle className="spin" size={16} /> Connecting to local
              governance service…
            </div>
          ) : !summary ? (
            <div className="panel empty-state">
              Backend unavailable. Start the API with{" "}
              <code>uvicorn app.main:app --reload --port 8000</code> from the
              backend folder, then refresh.
            </div>
          ) : (
            <>
              {page === "Overview" && (
                <Overview
                  summary={summary}
                  onOpen={openAgent}
                  onPage={setPage}
                />
              )}
              {page === "Agent registry" && (
                <Registry
                  agents={agents}
                  busy={busy}
                  agentQuery={agentQuery}
                  setAgentQuery={setAgentQuery}
                  ownerFilter={ownerFilter}
                  setOwnerFilter={setOwnerFilter}
                  riskFilter={riskFilter}
                  setRiskFilter={setRiskFilter}
                  statusFilter={statusFilter}
                  setStatusFilter={setStatusFilter}
                  sensitivityFilter={sensitivityFilter}
                  setSensitivityFilter={setSensitivityFilter}
                  onSearch={() => void loadAgents()}
                  onOpen={openAgent}
                  onEvaluate={runEvaluation}
                  onReview={() =>
                    document
                      .getElementById("review-agent")
                      ?.scrollIntoView({ behavior: "smooth" })
                  }
                />
              )}
              {page === "Agent registry" && (
                <ReviewPanel
                  reviewText={reviewText}
                  setReviewText={setReviewText}
                  result={reviewResult}
                  busy={busy}
                  onSubmit={runReview}
                />
              )}
              {page === "Agent details" && (
                <AgentDetail
                  agent={selected}
                  busy={busy}
                  onBack={() => setPage("Agent registry")}
                  onEvaluate={runEvaluation}
                  onPropose={async (agent) => {
                    const finding = agent.findings?.find(
                      (item) => item.status === "open",
                    );
                    if (finding) await proposeFinding(finding);
                    else
                      setError(
                        "Run a review first to generate an evidence-linked remediation proposal.",
                      );
                  }}
                />
              )}
              {page === "Governance findings" && (
                <FindingsView
                  findings={findings}
                  severity={findingSeverity}
                  setSeverity={setFindingSeverity}
                  status={findingStatus}
                  setStatus={setFindingStatus}
                  onSearch={() => void loadFindings()}
                  onReview={markReviewed}
                  onPropose={proposeFinding}
                  onOpen={openAgent}
                />
              )}
              {page === "Policy explorer" && (
                <PoliciesView
                  rules={rules}
                  query={policyQuery}
                  setQuery={setPolicyQuery}
                  matches={policyMatches}
                  onSearch={() => void searchPolicies()}
                />
              )}
              {page === "Activity & audit" && (
                <AuditView
                  events={audits}
                  filter={auditFilter}
                  setFilter={setAuditFilter}
                  onSearch={() => void loadAudit()}
                />
              )}
              {page === "Approval queue" && (
                <ApprovalsView
                  approvals={approvals}
                  onDecide={decide}
                  onApply={apply}
                  onOpen={openAgent}
                />
              )}
              {page === "Reports & evaluation" && (
                <ReportsView
                  findings={findings}
                  evaluation={evaluation}
                  onDownload={download}
                />
              )}
              {page === "Settings" && <SettingsView />}
            </>
          )}
        </div>
      </main>
    </div>
  );
}

function Overview({
  summary,
  onOpen,
  onPage,
}: {
  summary: Summary;
  onOpen: (id: string) => void;
  onPage: (page: PageName) => void;
}) {
  const riskData = Object.entries(summary.risk_distribution).map(
    ([name, value]) => ({ name, value }),
  );
  const categoryData = Object.entries(summary.findings_by_category).map(
    ([key, value]) => ({ name: categoryNames[key] ?? key, count: value }),
  );
  return (
    <>
      <div className="stat-grid">
        <Stat
          label="Registered agents"
          value={summary.total_agents}
          note="Synthetic inventory"
          icon={Bot}
        />
        <Stat
          label="Open findings"
          value={summary.open_findings}
          note={`${summary.sensitive_findings} involve sensitive access`}
          icon={ShieldAlert}
          color="#f09a60"
        />
        <Stat
          label="Over-privileged"
          value={summary.over_privileged_agents}
          note="Least-privilege rules matched"
          icon={KeyRound}
          color="#eb7470"
        />
        <Stat
          label="Pending approvals"
          value={summary.pending_approvals}
          note="Awaiting reviewer decision"
          icon={ClipboardCheck}
          color="#dfc66d"
        />
      </div>
      <div className="grid-two">
        <div className="panel">
          <div className="panel-head">
            <div>
              <h2>Risk distribution</h2>
              <p>Agent counts by deterministic risk band</p>
            </div>
            <button
              className="btn small ghost"
              onClick={() => onPage("Agent registry")}
            >
              View registry <ChevronRight size={13} />
            </button>
          </div>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={riskData}
                margin={{ top: 18, right: 20, left: -18, bottom: 0 }}
              >
                <CartesianGrid stroke="#2b3b3d" vertical={false} />
                <XAxis
                  dataKey="name"
                  tick={{ fill: "#90a09a", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fill: "#768681", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "#111b20",
                    border: "1px solid #405052",
                    borderRadius: 5,
                    color: "#e6eeec",
                    fontSize: 11,
                  }}
                />
                <Bar dataKey="value" name="Agents" radius={[3, 3, 0, 0]}>
                  {riskData.map((entry) => (
                    <Cell
                      key={entry.name}
                      fill={riskColors[entry.name] ?? "#a5d369"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-legend">
            {riskData.map((item) => (
              <span className="legend-item" key={item.name}>
                <i
                  className="legend-dot"
                  style={{ background: riskColors[item.name] }}
                />
                {item.name} <b>{item.value}</b>
              </span>
            ))}
          </div>
        </div>
        <div className="panel">
          <div className="panel-head">
            <div>
              <h2>Findings by rule</h2>
              <p>Open matches across the inventory</p>
            </div>
          </div>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={categoryData}
                  dataKey="count"
                  nameKey="name"
                  innerRadius={53}
                  outerRadius={83}
                  paddingAngle={3}
                  stroke="none"
                >
                  {categoryData.map((entry, index) => (
                    <Cell
                      key={entry.name}
                      fill={
                        [
                          "#b8dd6c",
                          "#71b8a5",
                          "#e5c96f",
                          "#ec9860",
                          "#e77370",
                          "#78aabd",
                          "#a8a4cf",
                        ][index % 7]
                      }
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "#111b20",
                    border: "1px solid #405052",
                    borderRadius: 5,
                    color: "#e6eeec",
                    fontSize: 11,
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-legend">
            {categoryData.slice(0, 4).map((item, index) => (
              <span className="legend-item" key={item.name}>
                <i
                  className="legend-dot"
                  style={{
                    background: ["#b8dd6c", "#71b8a5", "#e5c96f", "#ec9860"][
                      index
                    ],
                  }}
                />
                {item.name} <b>{item.count}</b>
              </span>
            ))}
          </div>
        </div>
      </div>
      <div className="grid-two">
        <div className="panel">
          <div className="panel-head">
            <div>
              <h2>Highest-risk agents</h2>
              <p>Prioritized by current project-specific score</p>
            </div>
            <span className="badge">Decision support only</span>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Agent</th>
                  <th>Owner</th>
                  <th>Score</th>
                  <th>Risk</th>
                </tr>
              </thead>
              <tbody>
                {summary.highest_risk_agents.map((agent) => (
                  <tr key={agent.agent_id}>
                    <td>
                      <button
                        className="text-button"
                        onClick={() => onOpen(agent.agent_id)}
                      >
                        {agent.name}
                        <small
                          className="muted mono"
                          style={{ display: "block", marginTop: 3 }}
                        >
                          {agent.agent_id}
                        </small>
                      </button>
                    </td>
                    <td>
                      {agent.owner ?? <span className="muted">Unassigned</span>}
                    </td>
                    <td>
                      <span className="score">
                        {agent.risk_score}
                        <span className="score-track">
                          <i style={{ width: `${agent.risk_score}%` }} />
                        </span>
                      </span>
                    </td>
                    <td>
                      <Badge value={agent.risk_level} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="panel">
          <div className="panel-head">
            <div>
              <h2>Recent audit activity</h2>
              <p>Most recent recorded events</p>
            </div>
            <button
              className="btn small ghost"
              onClick={() => onPage("Activity & audit")}
            >
              All activity <ChevronRight size={13} />
            </button>
          </div>
          <div className="panel-body" style={{ paddingTop: 6 }}>
            {summary.recent_events.length ? (
              summary.recent_events.slice(0, 6).map((event) => (
                <div className="setting-row" key={event.event_id}>
                  <span>
                    <b style={{ color: "#c5d2cc", fontWeight: 500 }}>
                      {event.action.replaceAll("_", " ")}
                    </b>
                    <small style={{ display: "block", marginTop: 4 }}>
                      {event.object_id ?? event.object_type}
                    </small>
                  </span>
                  <small className="muted">
                    {new Date(event.created_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </small>
                </div>
              ))
            ) : (
              <div className="empty-state">No audit activity yet.</div>
            )}
          </div>
        </div>
      </div>
      <div className="notice">
        Risk scores are deterministic project indicators for prioritization, not
        proof of compromise or a production security certification.
      </div>
    </>
  );
}

function Registry({
  agents,
  busy,
  agentQuery,
  setAgentQuery,
  ownerFilter,
  setOwnerFilter,
  riskFilter,
  setRiskFilter,
  statusFilter,
  setStatusFilter,
  sensitivityFilter,
  setSensitivityFilter,
  onSearch,
  onOpen,
  onEvaluate,
  onReview,
}: {
  agents: Agent[];
  busy: boolean;
  agentQuery: string;
  setAgentQuery: (v: string) => void;
  ownerFilter: string;
  setOwnerFilter: (v: string) => void;
  riskFilter: string;
  setRiskFilter: (v: string) => void;
  statusFilter: string;
  setStatusFilter: (v: string) => void;
  sensitivityFilter: string;
  setSensitivityFilter: (v: string) => void;
  onSearch: () => void;
  onOpen: (id: string) => void;
  onEvaluate: (id: string) => void;
  onReview: () => void;
}) {
  const [toolFilter, setToolFilter] = useState("");
  const [sortBy, setSortBy] = useState("risk_score");
  const [sortOrder, setSortOrder] = useState("desc");
  const [registryPage, setRegistryPage] = useState(1);
  const pageSize = 10;
  const filteredAgents = agents
    .filter((agent) => !toolFilter || agent.tools.includes(toolFilter))
    .sort((left, right) => {
      const leftValue = sortBy === "name" ? left.name : sortBy === "last_activity" ? left.last_activity ?? "" : left.risk_score;
      const rightValue = sortBy === "name" ? right.name : sortBy === "last_activity" ? right.last_activity ?? "" : right.risk_score;
      const comparison = leftValue < rightValue ? -1 : leftValue > rightValue ? 1 : 0;
      return sortOrder === "asc" ? comparison : -comparison;
    });
  const pageCount = Math.max(1, Math.ceil(filteredAgents.length / pageSize));
  const visibleAgents = filteredAgents.slice((registryPage - 1) * pageSize, registryPage * pageSize);
  const submitSearch = () => {
    setRegistryPage(1);
    onSearch();
  };
  return (
    <div className="content-grid">
      <div className="panel">
        <div className="filters">
          <input
            className="input"
            aria-label="Search agents"
            placeholder="Search name or agent ID"
            value={agentQuery}
            onChange={(e) => setAgentQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submitSearch()}
          />
          <input
            className="input"
            aria-label="Filter by owner"
            placeholder="Owner or team"
            value={ownerFilter}
            onChange={(e) => setOwnerFilter(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submitSearch()}
          />
          <select
            className="select"
            aria-label="Filter risk"
            value={riskFilter}
            onChange={(e) => {
              setRiskFilter(e.target.value);
              setRegistryPage(1);
            }}
          >
            <option value="">All risk levels</option>
            {["critical", "high", "medium", "low"].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
          <select
            className="select"
            aria-label="Filter status"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setRegistryPage(1);
            }}
          >
            <option value="">All statuses</option>
            {["active", "inactive", "suspended"].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
          <select
            className="select"
            aria-label="Filter sensitivity"
            value={sensitivityFilter}
            onChange={(e) => {
              setSensitivityFilter(e.target.value);
              setRegistryPage(1);
            }}
          >
            <option value="">All sensitivity</option>
            {["low", "moderate", "high", "restricted"].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
          <input
            className="input"
            aria-label="Filter by assigned tool"
            placeholder="Assigned tool"
            value={toolFilter}
            onChange={(e) => {
              setToolFilter(e.target.value);
              setRegistryPage(1);
            }}
          />
          <select className="select" aria-label="Sort agents by" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="risk_score">Sort: risk score</option>
            <option value="name">Sort: name</option>
            <option value="last_activity">Sort: last activity</option>
          </select>
          <select className="select" aria-label="Sort direction" value={sortOrder} onChange={(e) => setSortOrder(e.target.value)}>
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
          <button className="btn" onClick={submitSearch}>
            <Search size={14} /> Search
          </button>
        </div>
        <div className="result-meta">
          {filteredAgents.length} agent{filteredAgents.length === 1 ? "" : "s"} in this view
          {busy && " · Updating…"}
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Agent</th>
                <th>Owner</th>
                <th>Last activity</th>
                <th>Data sensitivity</th>
                <th>Risk</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {visibleAgents.map((agent) => (
                <tr key={agent.agent_id}>
                  <td>
                    <button
                      className="text-button"
                      onClick={() => onOpen(agent.agent_id)}
                    >
                      {agent.name}
                      <small
                        className="muted mono"
                        style={{ display: "block", marginTop: 3 }}
                      >
                        {agent.agent_id}
                      </small>
                    </button>
                  </td>
                  <td>
                    {agent.owner ?? <span className="muted">Unassigned</span>}
                  </td>
                  <td>
                    {agent.last_activity
                      ? new Date(agent.last_activity).toLocaleDateString()
                      : "No record"}
                  </td>
                  <td>
                    <Badge value={agent.sensitivity} />
                  </td>
                  <td>
                    <span className="score">
                      {agent.risk_score} <Badge value={agent.risk_level} />
                    </span>
                  </td>
                  <td>
                    <Badge value={agent.status} />
                  </td>
                  <td>
                    <div className="row-actions">
                      <button
                        className="btn small"
                        title="Run permission evaluation"
                        onClick={() => onEvaluate(agent.agent_id)}
                      >
                        <RefreshCw size={13} />
                      </button>
                      <button
                        className="btn small"
                        title="Open agent details"
                        onClick={() => onOpen(agent.agent_id)}
                      >
                        <ChevronRight size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!visibleAgents.length && (
            <div className="empty-state">No agents match these filters.</div>
          )}
        </div>
      </div>
      <div className="panel panel-body" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
        <span className="muted" style={{ fontSize: 11 }}>
          {filteredAgents.length ? `${(registryPage - 1) * pageSize + 1}–${Math.min(registryPage * pageSize, filteredAgents.length)} of ${filteredAgents.length}` : "0 agents"}
        </span>
        <div className="row-actions">
          <button className="btn small" disabled={registryPage <= 1} onClick={() => setRegistryPage((current) => current - 1)}>Previous</button>
          <span className="muted" style={{ alignSelf: "center", fontSize: 11 }}>Page {registryPage} of {pageCount}</span>
          <button className="btn small" disabled={registryPage >= pageCount} onClick={() => setRegistryPage((current) => current + 1)}>Next</button>
        </div>
      </div>
      <div id="review-agent">
        <ReviewPanelCompact onReview={onReview} />
      </div>
    </div>
  );
}

function ReviewPanelCompact({ onReview }: { onReview: () => void }) {
  return (
    <div className="panel">
      <div className="panel-head">
        <div>
          <h2>Governance review agent</h2>
          <p>Bounded tools · deterministic scoring · local policy evidence</p>
        </div>
        <Sparkles size={17} color="#bfdc77" />
      </div>
      <div className="panel-body">
        <p className="muted" style={{ fontSize: 12, marginTop: 0 }}>
          Run a structured review to inspect a profile, evaluate permissions,
          and retrieve cited policy sections.
        </p>
        <button
          className="btn"
          onClick={() => {
            onReview();
            window.setTimeout(() => {
              const prompt = document.getElementById("review-prompt");
              prompt?.scrollIntoView({ behavior: "smooth", block: "center" });
              prompt?.focus();
            }, 250);
          }}
        >
          Open review workspace <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}

function ReviewPanel({
  reviewText,
  setReviewText,
  result,
  busy,
  onSubmit,
}: {
  reviewText: string;
  setReviewText: (v: string) => void;
  result: Record<string, any> | null;
  busy: boolean;
  onSubmit: (event: React.FormEvent) => void;
}) {
  return (
    <div className="content-grid">
      <form className="panel" onSubmit={onSubmit}>
        <div className="panel-head">
          <div>
            <h2>Governance review agent</h2>
            <p>
              Profile inspection, deterministic evaluation, local policy
              retrieval
            </p>
          </div>
          <span className="badge">No external execution</span>
        </div>
        <div className="panel-body">
          <label
            htmlFor="review-prompt"
            className="muted"
            style={{ display: "block", fontSize: 11, marginBottom: 8 }}
          >
            Review request
          </label>
          <textarea
            id="review-prompt"
            className="textarea"
            maxLength={1000}
            value={reviewText}
            onChange={(e) => setReviewText(e.target.value)}
          />
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: 10,
              marginTop: 12,
              alignItems: "center",
            }}
          >
            <span className="muted" style={{ fontSize: 10 }}>
              Agent ID example: SA-1002. Metadata is treated as untrusted
              evidence.
            </span>
            <button className="btn primary" disabled={busy}>
              <Sparkles size={14} /> {busy ? "Reviewing…" : "Run review"}
            </button>
          </div>
        </div>
      </form>
      {result && (
        <>
          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Structured governance report</h2>
                <p>
                  {result.mode === "ollama"
                    ? "Optional local Ollama model"
                    : "Deterministic fallback · not LLM-generated"}
                </p>
              </div>
              <Badge value={result.mode === "ollama" ? "ollama" : "fallback"} />
            </div>
            <div className="panel-body">
              <p style={{ color: "#dce6e0", fontSize: 13, lineHeight: 1.6 }}>
                {result.summary}
              </p>
              {result.risk_score !== null && (
                <div className="definition-grid">
                  <div>
                    <small>Deterministic score</small>
                    <strong>{result.risk_score} / 100</strong>
                  </div>
                  <div>
                    <small>Risk band</small>
                    <Badge value={result.risk_level} />
                  </div>
                  <div>
                    <small>Findings</small>
                    <strong>{result.findings?.length ?? 0}</strong>
                  </div>
                  <div>
                    <small>Retrieved policy passages</small>
                    <strong>{result.policy_references?.length ?? 0}</strong>
                  </div>
                </div>
              )}
              {result.uncertainty?.map((item: string) => (
                <p className="muted" key={item} style={{ fontSize: 11 }}>
                  Uncertainty: {item}
                </p>
              ))}
            </div>
          </div>
          {result.findings?.length > 0 && (
            <div className="panel">
              <div className="panel-head">
                <h2>Evidence-backed findings</h2>
              </div>
              <div className="panel-body finding-list">
                {result.findings.map((finding: Finding) => (
                  <FindingCard key={finding.finding_id} finding={finding} />
                ))}
              </div>
            </div>
          )}
          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Actual tool invocations</h2>
                <p>Arguments and returned structured evidence</p>
              </div>
            </div>
            <div className="panel-body">
              {result.tool_calls?.map((call: any, index: number) => (
                <details
                  className="tool-call"
                  key={`${call.tool}-${index}`}
                  open={index === 0}
                >
                  <summary>
                    <span className="mono">{call.tool}</span>{" "}
                    <span className="muted">
                      · {JSON.stringify(call.arguments)}
                    </span>
                  </summary>
                  <pre>{JSON.stringify(call.result, null, 2)}</pre>
                </details>
              ))}
            </div>
          </div>
          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Policy evidence</h2>
                <p>Retrieved references from the local policy file only</p>
              </div>
            </div>
            <div className="panel-body">
              {result.policy_references?.length ? (
                result.policy_references.map((item: any, i: number) => (
                  <div className="finding-item" key={`${item.section}-${i}`}>
                    <h3>{item.section}</h3>
                    <p>{item.excerpt}</p>
                    <div className="policy-ref">
                      {item.source} · keyword retrieval
                    </div>
                  </div>
                ))
              ) : (
                <div className="empty-state">
                  No matching policy evidence retrieved.
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function FindingCard({ finding }: { finding: Finding }) {
  return (
    <article className="finding-item">
      <div
        style={{ display: "flex", justifyContent: "space-between", gap: 10 }}
      >
        <span className="mono muted">
          {finding.rule_id} · {finding.agent_id}
        </span>
        <Badge value={finding.severity} />
      </div>
      <h3>{finding.title}</h3>
      <p>{finding.rationale}</p>
      <div className="evidence">
        <b>Evidence:</b> {finding.evidence.join(" · ")}
      </div>
      <div className="evidence">
        <b>Recommended:</b> {finding.remediation}
      </div>
    </article>
  );
}

function AgentDetail({
  agent,
  busy,
  onBack,
  onEvaluate,
  onPropose,
}: {
  agent: (Agent & { findings?: Finding[] }) | null;
  busy: boolean;
  onBack: () => void;
  onEvaluate: (id: string) => void;
  onPropose: (agent: Agent & { findings?: Finding[] }) => void;
}) {
  if (!agent)
    return (
      <div className="panel empty-state">
        Choose an agent from the registry to inspect its permissions.
      </div>
    );
  return (
    <div className="content-grid">
      <div style={{ display: "flex", gap: 8 }}>
        <button className="btn ghost" onClick={onBack}>
          <ArrowLeft size={14} /> Registry
        </button>
        <button
          className="btn"
          disabled={busy}
          onClick={() => onEvaluate(agent.agent_id)}
        >
          <RefreshCw size={14} /> Run deterministic review
        </button>
        <button className="btn primary" onClick={() => onPropose(agent)}>
          <ClipboardCheck size={14} /> Propose remediation
        </button>
      </div>
      <div className="detail-grid">
        <div className="panel">
          <div className="panel-head">
            <div className="detail-title">
              <span className="agent-avatar">
                {agent.name.slice(0, 2).toUpperCase()}
              </span>
              <span>
                <h2>{agent.name}</h2>
                <p className="mono">
                  {agent.agent_id} · {agent.description}
                </p>
              </span>
            </div>
            <Badge value={agent.risk_level} />
          </div>
          <div className="detail-section">
            <div className="definition-grid">
              <div>
                <small>Owner / team</small>
                <strong>{agent.owner ?? "Unassigned"}</strong>
              </div>
              <div>
                <small>Risk score</small>
                <strong>{agent.risk_score} / 100</strong>
              </div>
              <div>
                <small>Lifecycle status</small>
                <Badge value={agent.status} />
              </div>
              <div>
                <small>Data sensitivity</small>
                <Badge value={agent.sensitivity} />
              </div>
              <div>
                <small>Last activity</small>
                <strong>
                  {agent.last_activity
                    ? new Date(agent.last_activity).toLocaleString()
                    : "Not recorded"}
                </strong>
              </div>
              <div>
                <small>Human approval</small>
                <strong>
                  {agent.approval_required ? "Required" : "Not required"}
                </strong>
              </div>
            </div>
          </div>
          {[
            ["Assigned tools", agent.tools],
            ["Permissions", agent.permissions],
            ["API scopes", agent.scopes],
            ["Data categories", agent.data_categories],
          ].map(([label, values]) => (
            <div className="detail-section" key={label as string}>
              <h3>{label as string}</h3>
              <div className="chip-list">
                {(values as string[]).length ? (
                  (values as string[]).map((value) => (
                    <span className="chip" key={value}>
                      {value}
                    </span>
                  ))
                ) : (
                  <span className="muted" style={{ fontSize: 11 }}>
                    None assigned
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
        <div className="panel">
          <div className="panel-head">
            <div>
              <h2>Permission analysis</h2>
              <p>Deterministic findings tied to evidence</p>
            </div>
          </div>
          <div className="panel-body finding-list">
            {agent.findings?.length ? (
              agent.findings.map((item) => (
                <FindingCard key={item.finding_id} finding={item} />
              ))
            ) : (
              <div className="empty-state">
                No findings loaded. Run a governance review.
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="notice">
        Recommended changes are proposals only. A reviewer must approve and
        separately confirm simulated application.
      </div>
    </div>
  );
}

function FindingsView({
  findings,
  severity,
  setSeverity,
  status,
  setStatus,
  onSearch,
  onReview,
  onPropose,
  onOpen,
}: {
  findings: Finding[];
  severity: string;
  setSeverity: (v: string) => void;
  status: string;
  setStatus: (v: string) => void;
  onSearch: () => void;
  onReview: (f: Finding) => void;
  onPropose: (f: Finding) => void;
  onOpen: (id: string) => void;
}) {
  const [ruleFilter, setRuleFilter] = useState("");
  const [agentFilter, setAgentFilter] = useState("");
  const visibleFindings = findings.filter(
    (finding) =>
      (!ruleFilter || finding.rule_id === ruleFilter) &&
      (!agentFilter || finding.agent_id.toLowerCase().includes(agentFilter.toLowerCase())),
  );
  return (
    <div className="panel">
      <div className="filters">
        <select
          className="select"
          aria-label="Severity filter"
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
        >
          <option value="">All severities</option>
          {["critical", "high", "medium", "low"].map((v) => (
            <option key={v}>{v}</option>
          ))}
        </select>
        <select
          className="select"
          aria-label="Finding category filter"
          value={ruleFilter}
          onChange={(e) => setRuleFilter(e.target.value)}
        >
          <option value="">All categories</option>
          {Object.entries(categoryNames).map(([ruleId, name]) => (
            <option key={ruleId} value={ruleId}>{name}</option>
          ))}
        </select>
        <input
          className="input"
          aria-label="Filter findings by agent"
          placeholder="Agent ID"
          value={agentFilter}
          onChange={(e) => setAgentFilter(e.target.value)}
        />
        <select
          className="select"
          aria-label="Finding status filter"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">All statuses</option>
          {["open", "reviewed", "resolved"].map((v) => (
            <option key={v}>{v}</option>
          ))}
        </select>
        <button className="btn" onClick={onSearch}>
          <Search size={14} /> Filter
        </button>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Finding / rule</th>
              <th>Agent</th>
              <th>Severity</th>
              <th>Evidence</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {visibleFindings.map((finding) => (
              <tr key={finding.finding_id}>
                <td>
                  <strong>{finding.title}</strong>
                  <small
                    className="muted mono"
                    style={{ display: "block", marginTop: 4 }}
                  >
                    {finding.rule_id}
                  </small>
                </td>
                <td>
                  <button
                    className="text-button mono"
                    onClick={() => onOpen(finding.agent_id)}
                  >
                    {finding.agent_id}
                  </button>
                </td>
                <td>
                  <Badge value={finding.severity} />
                </td>
                <td style={{ maxWidth: 260 }}>
                  {finding.evidence.slice(0, 2).join(" · ")}
                </td>
                <td>
                  <Badge value={finding.status} />
                </td>
                <td>
                  <div className="row-actions">
                    {finding.status === "open" && (
                      <button
                        className="btn small"
                        title="Mark reviewed"
                        onClick={() => onReview(finding)}
                      >
                        <Check size={13} />
                      </button>
                    )}
                    <button
                      className="btn small"
                      title="Propose remediation"
                      onClick={() => onPropose(finding)}
                    >
                      <ClipboardCheck size={13} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!visibleFindings.length && (
          <div className="empty-state">No findings match this filter.</div>
        )}
      </div>
      <div className="result-meta">{visibleFindings.length} displayed findings</div>
    </div>
  );
}

function PoliciesView({
  rules,
  query,
  setQuery,
  matches,
  onSearch,
}: {
  rules: {
    rule_id: string;
    title: string;
    severity: string;
    description: string;
  }[];
  query: string;
  setQuery: (v: string) => void;
  matches: { source: string; section: string; excerpt: string }[];
  onSearch: () => void;
}) {
  return (
    <div className="content-grid">
      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Local policy retrieval</h2>
            <p>
              Keyword fallback with references to the source policy file and
              section
            </p>
          </div>
          <Badge value="offline capable" />
        </div>
        <div className="filters">
          <input
            className="input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search local policies"
            placeholder="Search policy language"
            onKeyDown={(e) => e.key === "Enter" && onSearch()}
          />
          <button className="btn" onClick={onSearch}>
            <Search size={14} /> Search policies
          </button>
        </div>
        <div className="panel-body" style={{ display: "grid", gap: 9 }}>
          {matches.map((item) => (
            <article className="finding-item" key={item.section}>
              <h3>{item.section}</h3>
              <p>{item.excerpt}</p>
              <div className="policy-ref">
                {item.source} · section reference
              </div>
            </article>
          ))}
          {!matches.length && (
            <div className="empty-state">
              Search local policy passages to view cited evidence.
            </div>
          )}
        </div>
      </div>
      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Deterministic rule catalogue</h2>
            <p>
              Editable project policies in backend/app/policies/governance.md
            </p>
          </div>
        </div>
        <div className="panel-body finding-list">
          {rules.map((rule) => (
            <article className="finding-item" key={rule.rule_id}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 10,
                }}
              >
                <span className="mono muted">{rule.rule_id}</span>
                <Badge value={rule.severity} />
              </div>
              <h3>{rule.title}</h3>
              <p>{rule.description}</p>
            </article>
          ))}
        </div>
      </div>
      <div className="notice">
        Thresholds and severity weights are project-specific and intended for
        reproducible capstone evaluation, not as an industry standard.
      </div>
    </div>
  );
}

function AuditView({
  events,
  filter,
  setFilter,
  onSearch,
}: {
  events: AuditEvent[];
  filter: string;
  setFilter: (v: string) => void;
  onSearch: () => void;
}) {
  const actions = [...new Set(events.map((event) => event.action))];
  return (
    <div className="panel">
      <div className="filters">
        <select
          className="select"
          aria-label="Audit action filter"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="">All audit actions</option>
          {actions.map((action) => (
            <option key={action}>{action}</option>
          ))}
        </select>
        <button className="btn" onClick={onSearch}>
          <Search size={14} /> Filter logs
        </button>
        <button className="btn" onClick={() => download("/audit/export.csv")}>
          <ArrowDownToLine size={14} /> Export CSV
        </button>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Action</th>
              <th>Object</th>
              <th>Reference</th>
              <th>Recorded details</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <tr key={event.event_id}>
                <td>{new Date(event.created_at).toLocaleString()}</td>
                <td>
                  <strong>{event.action.replaceAll("_", " ")}</strong>
                </td>
                <td>{event.object_type}</td>
                <td className="mono">{event.object_id ?? "—"}</td>
                <td className="muted">{JSON.stringify(event.details)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!events.length && (
          <div className="empty-state">No audit events recorded.</div>
        )}
      </div>
    </div>
  );
}

function ApprovalsView({
  approvals,
  onDecide,
  onApply,
  onOpen,
}: {
  approvals: Approval[];
  onDecide: (item: Approval, decision: "approve" | "reject") => void;
  onApply: (item: Approval) => void;
  onOpen: (id: string) => void;
}) {
  return (
    <div className="content-grid">
      {approvals.length ? (
        approvals.map((item) => (
          <div className="panel" key={item.approval_id}>
            <div className="approval-card">
              <div className="approval-top">
                <div>
                  <h3>
                    {item.change_type.replaceAll("_", " ")}{" "}
                    <span className="muted mono">
                      · {item.approval_id.slice(0, 8)}
                    </span>
                  </h3>
                  <button
                    className="text-button mono"
                    onClick={() => onOpen(item.agent_id)}
                  >
                    {item.agent_id}
                  </button>
                </div>
                <Badge value={item.status} />
              </div>
              <p>{item.rationale}</p>
              <div className="config-compare">
                <div className="config-box">
                  <small>Current configuration</small>
                  <code>
                    {JSON.stringify(item.current_configuration, null, 2)}
                  </code>
                </div>
                <div className="config-box">
                  <small>Proposed change</small>
                  <code>{JSON.stringify(item.proposed_change, null, 2)}</code>
                </div>
              </div>
              <div className="evidence">
                <b>Evidence:</b>{" "}
                {item.evidence.join(" · ") || "No evidence attached"}
              </div>
              {item.reviewer && (
                <p>
                  Reviewer: {item.reviewer} ·{" "}
                  {item.decision_at &&
                    new Date(item.decision_at).toLocaleString()}
                </p>
              )}
              <div className="approval-actions">
                {item.status === "pending" && (
                  <>
                    <button
                      className="btn success small"
                      onClick={() => onDecide(item, "approve")}
                    >
                      <Check size={13} /> Approve proposal
                    </button>
                    <button
                      className="btn danger small"
                      onClick={() => onDecide(item, "reject")}
                    >
                      <X size={13} /> Reject
                    </button>
                  </>
                )}
                {item.status === "approved" && (
                  <button
                    className="btn primary small"
                    onClick={() => onApply(item)}
                  >
                    <LockKeyhole size={13} /> Confirm & apply simulation
                  </button>
                )}
                {item.status === "applied" && (
                  <span className="badge applied">Applied in simulation</span>
                )}
                {item.status === "rejected" && (
                  <span className="muted" style={{ fontSize: 11 }}>
                    No change applied
                  </span>
                )}
              </div>
            </div>
          </div>
        ))
      ) : (
        <div className="panel empty-state">
          <ClipboardCheck
            size={25}
            style={{ margin: "0 auto 10px", color: "#9ebd66" }}
          />
          <div>No proposals in the queue.</div>
          <p>Open an evidence-backed finding and choose Propose remediation.</p>
        </div>
      )}
      <div className="notice">
        Approval and application are separate. Applying changes only a local
        synthetic record and requires browser confirmation.
      </div>
    </div>
  );
}

function ReportsView({
  findings,
  evaluation,
  onDownload,
}: {
  findings: Finding[];
  evaluation: Record<string, any> | null;
  onDownload: (path: string) => void;
}) {
  return (
    <div className="content-grid">
      <div className="grid-two">
        <div className="panel">
          <div className="panel-head">
            <div>
              <h2>Finding exports</h2>
              <p>Generated from current SQLite-backed governance findings</p>
            </div>
            <FileText size={17} color="#bfdc77" />
          </div>
          <div className="panel-body">
            <div className="definition-grid">
              <div>
                <small>Total findings</small>
                <strong>{findings.length}</strong>
              </div>
              <div>
                <small>Open findings</small>
                <strong>
                  {findings.filter((item) => item.status === "open").length}
                </strong>
              </div>
              <div>
                <small>Human approval flagged</small>
                <strong>
                  {findings.filter((item) => item.approval_required).length}
                </strong>
              </div>
              <div>
                <small>Sources</small>
                <strong>Synthetic inventory + policies</strong>
              </div>
            </div>
            <div
              style={{
                display: "flex",
                gap: 8,
                marginTop: 18,
                flexWrap: "wrap",
              }}
            >
              <button
                className="btn"
                onClick={() => onDownload("/reports/findings.csv")}
              >
                <ArrowDownToLine size={14} /> Export CSV
              </button>
              <button
                className="btn"
                onClick={() => onDownload("/reports/findings.json")}
              >
                <ArrowDownToLine size={14} /> Export JSON
              </button>
              <button
                className="btn"
                onClick={() => onDownload("/reports/findings.md")}
              >
                <FileText size={14} /> Readable report
              </button>
            </div>
          </div>
        </div>
        <div className="panel">
          <div className="panel-head">
            <div>
              <h2>Evaluation results</h2>
              <p>Metrics are populated by the reproducible evaluation script</p>
            </div>
            <Gauge size={17} color="#bfdc77" />
          </div>
          <div className="panel-body">
            {evaluation?.available ? (
              <div className="definition-grid">
                {Object.entries(evaluation.metrics ?? {}).map(
                  ([key, value]) => (
                    <div key={key}>
                      <small>{key.replaceAll("_", " ")}</small>
                      <strong>{String(value)}</strong>
                    </div>
                  ),
                )}
              </div>
            ) : (
              <>
                <div className="notice">
                  {evaluation?.message ??
                    "Evaluation has not run in this workspace."}
                </div>
                <p className="muted" style={{ fontSize: 11 }}>
                  No metric values are fabricated. Generate results with{" "}
                  <code>python scripts/run_evaluation.py</code>.
                </p>
              </>
            )}
          </div>
        </div>
      </div>
      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Method and limitations</h2>
            <p>Interpret findings as prioritization signals only</p>
          </div>
          <CircleHelp size={17} color="#aabb9b" />
        </div>
        <div className="panel-body policy-copy">
          Risk score = sum of matched-rule weights (low 5, medium 12, high 22,
          critical 32), capped at 100. Bands: low 0–14, medium 15–39, high
          40–69, critical 70–100. These are project-specific values, not a
          standard. Findings are calculated from deterministic policy rules; a
          local LLM may rewrite narrative only and cannot change findings or
          score. All records are synthetic; this evaluation does not establish
          production readiness.
        </div>
      </div>
    </div>
  );
}

function SettingsView() {
  const [health, setHealth] = useState<{
    status: string;
    version: string;
    ai_mode: string;
  } | null>(null);
  const [ready, setReady] = useState<{
    ready: boolean;
    agents: number;
    database: string;
  } | null>(null);
  useEffect(() => {
    void Promise.all([api.health(), api.ready()])
      .then(([h, r]) => {
        setHealth(h);
        setReady(r);
      })
      .catch(() => undefined);
  }, []);
  return (
    <div className="content-grid">
      <div className="settings-grid">
        <div className="panel">
          <div className="panel-head">
            <h2>Service health</h2>
            <Activity size={16} color="#b9d782" />
          </div>
          <div className="panel-body">
            <div className="setting-row">
              <span>API</span>
              <strong>{health?.status ?? "Checking"}</strong>
            </div>
            <div className="setting-row">
              <span>Version</span>
              <strong>{health?.version ?? "—"}</strong>
            </div>
            <div className="setting-row">
              <span>Readiness</span>
              <strong>{ready?.ready ? "Ready" : "Checking"}</strong>
            </div>
          </div>
        </div>
        <div className="panel">
          <div className="panel-head">
            <h2>Storage</h2>
            <Database size={16} color="#b9d782" />
          </div>
          <div className="panel-body">
            <div className="setting-row">
              <span>Database</span>
              <strong>{ready?.database ?? "—"}</strong>
            </div>
            <div className="setting-row">
              <span>Agent records</span>
              <strong>{ready?.agents ?? "—"}</strong>
            </div>
            <div className="setting-row">
              <span>Data type</span>
              <strong>Entirely synthetic</strong>
            </div>
          </div>
        </div>
        <div className="panel">
          <div className="panel-head">
            <h2>AI configuration</h2>
            <Sparkles size={16} color="#b9d782" />
          </div>
          <div className="panel-body">
            <div className="setting-row">
              <span>Review mode</span>
              <strong>
                {health?.ai_mode ? "Optional Ollama + fallback" : "Checking"}
              </strong>
            </div>
            <div className="setting-row">
              <span>Policy retrieval</span>
              <strong>Local keyword search</strong>
            </div>
            <div className="setting-row">
              <span>Credentials</span>
              <strong>None required</strong>
            </div>
          </div>
        </div>
      </div>
      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Safe configuration</h2>
            <p>Optional local inference only; no hosted API keys are needed</p>
          </div>
          <LockKeyhole size={16} color="#b9d782" />
        </div>
        <div className="panel-body policy-copy">
          To enable Ollama, set OLLAMA_URL to your local Ollama endpoint and
          OLLAMA_MODEL to an installed local model in your environment.
          SentinelAI sends only synthetic profile data to that endpoint. If
          Ollama is unreachable, the deterministic review workflow remains
          available and labels itself as fallback mode. Never point this demo at
          production agents, secrets, or external accounts.
        </div>
      </div>
      <div className="notice">
        Health checks expose status only. No secret values are stored or
        displayed.
      </div>
    </div>
  );
}
