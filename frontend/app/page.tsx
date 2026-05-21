"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Activity,
  BarChart3,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  History,
  Loader2,
  Play,
  ShieldCheck,
  Upload
} from "lucide-react";
import {
  AuditEvent,
  Dataset,
  ModelRun,
  Project,
  TriangleDetail,
  createExport,
  createProject,
  createRun,
  getTriangle,
  listProjectAuditEvents,
  listProjectDatasets,
  listProjectRuns,
  listProjects,
  uploadDataset
} from "@/lib/api";

const methodLabels: Record<string, string> = {
  chain_ladder: "Chain Ladder",
  bornhuetter_ferguson: "Bornhuetter-Ferguson",
  cape_cod: "Cape Cod"
};

const sampleExposureValues =
  "12059, 12868, 13382, 14118, 14926, 15882, 16838, 17794, 18897, 20000, 21103, 22279, 23529, 24926, 26324";

function currency(value: number) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
    style: "currency",
    currency: "USD"
  }).format(value);
}

function parseNumberList(value: string) {
  const trimmed = value.trim();
  if (!trimmed) {
    return undefined;
  }
  return trimmed
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isFinite(item));
}

function formatCell(value: number | null) {
  if (value === null) {
    return "";
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

export default function Home() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [activeDataset, setActiveDataset] = useState<Dataset | null>(null);
  const [triangle, setTriangle] = useState<TriangleDetail | null>(null);
  const [runs, setRuns] = useState<ModelRun[]>([]);
  const [activeRun, setActiveRun] = useState<ModelRun | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [projectName, setProjectName] = useState("Q4 reserving review");
  const [valueType, setValueType] = useState("paid");
  const [triangleBasis, setTriangleBasis] = useState("cumulative");
  const [method, setMethod] = useState("chain_ladder");
  const [selectedFactors, setSelectedFactors] = useState("");
  const [exposureValues, setExposureValues] = useState(sampleExposureValues);
  const [expectedLossRatio, setExpectedLossRatio] = useState("0.72");
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState("Ready");
  const [error, setError] = useState<string | null>(null);
  const [exportPath, setExportPath] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const metrics = useMemo(
    () => [
      { label: "Total Latest", value: activeRun?.result.total_latest ?? 0 },
      { label: "Selected Ultimate", value: activeRun?.result.total_ultimate ?? 0 },
      { label: "Total IBNR", value: activeRun?.result.total_ibnr ?? 0 }
    ],
    [activeRun]
  );

  async function refreshProject(project: Project) {
    const [projectDatasets, projectRuns, projectAuditEvents] = await Promise.all([
      listProjectDatasets(project.id),
      listProjectRuns(project.id),
      listProjectAuditEvents(project.id)
    ]);
    setDatasets(projectDatasets);
    setRuns(projectRuns);
    setAuditEvents(projectAuditEvents);
    const nextDataset = projectDatasets[0] ?? null;
    const nextRun = projectRuns[projectRuns.length - 1] ?? null;
    setActiveDataset(nextDataset);
    setActiveRun(nextRun);
    setTriangle(nextDataset ? await getTriangle(nextDataset.id) : null);
  }

  useEffect(() => {
    async function load() {
      try {
        const loadedProjects = await listProjects();
        setProjects(loadedProjects);
        const firstProject = loadedProjects[0] ?? null;
        setActiveProject(firstProject);
        if (firstProject) {
          await refreshProject(firstProject);
        }
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Could not load projects");
      }
    }
    void load();
  }, []);

  async function handleCreateProject(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const project = await createProject(projectName);
      setProjects((current) => [project, ...current]);
      setActiveProject(project);
      setDatasets([]);
      setRuns([]);
      setAuditEvents([]);
      setActiveDataset(null);
      setActiveRun(null);
      setTriangle(null);
      setStatus("Project created");
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Could not create project");
    } finally {
      setBusy(false);
    }
  }

  async function handleUpload(event: FormEvent) {
    event.preventDefault();
    if (!activeProject || !file) {
      setError("Create/select a project and choose a triangle file first.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const dataset = await uploadDataset(activeProject.id, file, valueType, triangleBasis);
      const detail = await getTriangle(dataset.id);
      setDatasets((current) => [dataset, ...current]);
      setActiveDataset(dataset);
      setTriangle(detail);
      setStatus("Triangle uploaded and validated");
      await refreshProject(activeProject);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Could not upload dataset");
    } finally {
      setBusy(false);
    }
  }

  async function handleLoadSample() {
    setBusy(true);
    setError(null);
    try {
      let project = activeProject;
      if (!project) {
        project = await createProject(projectName || "Commercial auto sample");
        setProjects((current) => [project as Project, ...current]);
        setActiveProject(project);
      }

      const response = await fetch("/samples/commercial_auto_paid_triangle_2010_2024.csv");
      if (!response.ok) {
        throw new Error("Could not load the bundled sample triangle");
      }
      const blob = await response.blob();
      const sampleFile = new File([blob], "commercial_auto_paid_triangle_2010_2024.csv", {
        type: "text/csv"
      });
      const dataset = await uploadDataset(project.id, sampleFile, "paid", "cumulative");
      const detail = await getTriangle(dataset.id);
      setDatasets((current) => [dataset, ...current]);
      setActiveDataset(dataset);
      setTriangle(detail);
      setExposureValues(sampleExposureValues);
      setValueType("paid");
      setTriangleBasis("cumulative");
      setStatus("Sample commercial auto triangle loaded");
      await refreshProject(project);
    } catch (sampleError) {
      setError(sampleError instanceof Error ? sampleError.message : "Could not load sample triangle");
    } finally {
      setBusy(false);
    }
  }

  async function handleRun(event: FormEvent) {
    event.preventDefault();
    if (!activeDataset || !activeProject) {
      setError("Upload a triangle before running a method.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const payload = {
        method,
        assumption_name: `${methodLabels[method]} selection`,
        selected_factors: parseNumberList(selectedFactors),
        exposure_values: method === "chain_ladder" ? undefined : parseNumberList(exposureValues),
        expected_loss_ratio:
          method === "bornhuetter_ferguson" ? Number(expectedLossRatio) : undefined
      };
      const run = await createRun(activeDataset.id, payload);
      setRuns((current) => [...current, run]);
      setActiveRun(run);
      setStatus(`${methodLabels[method]} run completed`);
      await refreshProject(activeProject);
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Could not run reserving method");
    } finally {
      setBusy(false);
    }
  }

  async function handleExport(exportType: "excel" | "pdf") {
    if (!activeRun) {
      setError("Run a method before exporting.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const exportJob = await createExport(activeRun.id, exportType);
      setExportPath(exportJob.file_path);
      setStatus(`${exportType.toUpperCase()} export created`);
      if (activeProject) {
        await refreshProject(activeProject);
      }
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : "Could not create export");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brandMark">R</div>
          <div>
            <strong>ReserveDesk</strong>
            <span>P&C workbench</span>
          </div>
        </div>

        <nav className="nav" aria-label="Main navigation">
          <a className="active" href="#dashboard">
            <BarChart3 size={18} /> Dashboard
          </a>
          <a href="#import">
            <Upload size={18} /> Import
          </a>
          <a href="#runs">
            <Activity size={18} /> Model runs
          </a>
          <a href="#governance">
            <ShieldCheck size={18} /> Governance
          </a>
          <a href="#exports">
            <Download size={18} /> Exports
          </a>
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p>{activeProject ? activeProject.name : "No active project"}</p>
            <h1>{activeDataset ? activeDataset.filename : "Reserve analysis workbench"}</h1>
          </div>
          <div className="statusPill">
            {busy ? <Loader2 className="spin" size={16} /> : <CheckCircle2 size={16} />}
            {status}
          </div>
        </header>

        {error && <div className="alert">{error}</div>}

        <section className="metricGrid" aria-label="Reserve summary">
          {metrics.map((metric) => (
            <div className="metric" key={metric.label}>
              <span>{metric.label}</span>
              <strong>{currency(metric.value)}</strong>
            </div>
          ))}
        </section>

        <section className="contentGrid">
          <div className="panel" id="import">
            <div className="panelHeader">
              <div>
                <span>Setup</span>
                <h2>Project and upload</h2>
              </div>
              <FileSpreadsheet size={22} />
            </div>

            <form className="formGrid" onSubmit={handleCreateProject}>
              <label>
                Project
                <input value={projectName} onChange={(event) => setProjectName(event.target.value)} />
              </label>
              <button className="primaryButton" disabled={busy || !projectName.trim()} type="submit">
                Create project
              </button>
            </form>

            <form className="formGrid" onSubmit={handleUpload}>
              <label>
                Active project
                <select
                  value={activeProject?.id ?? ""}
                  onChange={async (event) => {
                    const project = projects.find((item) => item.id === event.target.value) ?? null;
                    setActiveProject(project);
                    if (project) {
                      await refreshProject(project);
                    }
                  }}
                >
                  <option value="">Select project</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Value type
                <select value={valueType} onChange={(event) => setValueType(event.target.value)}>
                  <option value="paid">Paid</option>
                  <option value="incurred">Incurred</option>
                  <option value="reported_claim_count">Reported claim count</option>
                  <option value="earned_premium">Earned premium</option>
                </select>
              </label>
              <label>
                Basis
                <select value={triangleBasis} onChange={(event) => setTriangleBasis(event.target.value)}>
                  <option value="cumulative">Cumulative</option>
                  <option value="incremental">Incremental</option>
                </select>
              </label>
              <label>
                Triangle file
                <input
                  accept=".csv,.xlsx,.xls"
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                  type="file"
                />
              </label>
              <button className="primaryButton" disabled={busy || !activeProject || !file} type="submit">
                <Upload size={18} />
                Upload triangle
              </button>
              <button className="secondaryButton" disabled={busy} onClick={() => void handleLoadSample()} type="button">
                Use bundled sample
              </button>
            </form>
          </div>

          <div className="panel" id="runs">
            <div className="panelHeader">
              <div>
                <span>Methods</span>
                <h2>Run reserving model</h2>
              </div>
              <Play size={22} />
            </div>
            <form className="formGrid" onSubmit={handleRun}>
              <label>
                Method
                <select value={method} onChange={(event) => setMethod(event.target.value)}>
                  <option value="chain_ladder">Chain Ladder</option>
                  <option value="bornhuetter_ferguson">Bornhuetter-Ferguson</option>
                  <option value="cape_cod">Cape Cod</option>
                </select>
              </label>
              <label>
                Selected LDFs
                <input value={selectedFactors} onChange={(event) => setSelectedFactors(event.target.value)} />
              </label>
              {method !== "chain_ladder" && (
                <label>
                  Exposure values
                  <input value={exposureValues} onChange={(event) => setExposureValues(event.target.value)} />
                </label>
              )}
              {method === "bornhuetter_ferguson" && (
                <label>
                  Expected loss ratio
                  <input value={expectedLossRatio} onChange={(event) => setExpectedLossRatio(event.target.value)} />
                </label>
              )}
              <button className="primaryButton" disabled={busy || !activeDataset} type="submit">
                <Activity size={18} />
                Run method
              </button>
            </form>
          </div>

          <div className="panel wide" id="dashboard">
            <div className="panelHeader">
              <div>
                <span>{activeRun ? methodLabels[activeRun.method] : "No run yet"}</span>
                <h2>Ultimate and IBNR by origin period</h2>
              </div>
              <CheckCircle2 className="successIcon" size={22} />
            </div>
            <div className="tableWrap">
              <table>
                <thead>
                  <tr>
                    <th>Origin</th>
                    <th>Latest</th>
                    <th>Ultimate</th>
                    <th>IBNR</th>
                  </tr>
                </thead>
                <tbody>
                  {(triangle?.origin_periods ?? []).map((origin, index) => (
                    <tr key={origin}>
                      <td>{origin}</td>
                      <td>{currency(activeRun?.result.latest_diagonal[index] ?? 0)}</td>
                      <td>{currency(activeRun?.result.ultimate_by_origin[index] ?? 0)}</td>
                      <td>{currency(activeRun?.result.ibnr_by_origin[index] ?? 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="panel">
            <div className="panelHeader">
              <div>
                <span>Factors</span>
                <h2>Selected LDFs</h2>
              </div>
            </div>
            <div className="factorList">
              {(activeRun?.result.age_to_age_factors ?? []).map((factor, index) => (
                <div key={`${factor}-${index}`}>
                  <span>
                    {triangle?.development_periods[index]} to {triangle?.development_periods[index + 1]}
                  </span>
                  <strong>{factor.toFixed(3)}</strong>
                </div>
              ))}
            </div>
          </div>

          <div className="panel wide">
            <div className="panelHeader">
              <div>
                <span>{triangle?.triangle_basis ?? "Triangle"}</span>
                <h2>Source upload vs normalized cumulative</h2>
              </div>
            </div>
            <div className="tableWrap splitTables">
              {[
                ["Source", triangle?.source_values],
                ["Normalized", triangle?.values]
              ].map(([label, values]) => (
                <div key={label as string}>
                  <strong>{label as string}</strong>
                  <table>
                    <thead>
                      <tr>
                        <th>Origin</th>
                        {(triangle?.development_periods ?? []).map((period) => (
                          <th key={period}>{period}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {((values as (number | null)[][] | undefined) ?? []).map((row, rowIndex) => (
                        <tr key={`${label}-${triangle?.origin_periods[rowIndex]}`}>
                          <td>{triangle?.origin_periods[rowIndex]}</td>
                          {row.map((value, columnIndex) => (
                            <td key={columnIndex}>{formatCell(value)}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          </div>

          <div className="panel" id="exports">
            <div className="panelHeader">
              <div>
                <span>Exports</span>
                <h2>Report pack</h2>
              </div>
            </div>
            <div className="exportActions">
              <button disabled={busy || !activeRun} onClick={() => void handleExport("excel")} type="button">
                <Download size={18} />
                Excel workbook
              </button>
              <button disabled={busy || !activeRun} onClick={() => void handleExport("pdf")} type="button">
                <Download size={18} />
                PDF report
              </button>
              {exportPath && <p className="mutedText">Created: {exportPath}</p>}
            </div>
          </div>

          <div className="panel wide" id="governance">
            <div className="panelHeader">
              <div>
                <span>Audit trail</span>
                <h2>Review history</h2>
              </div>
              <History size={22} />
            </div>
            <div className="timeline">
              {auditEvents.map((event) => (
                <div key={event.id}>
                  <span />
                  <p>
                    {event.event_type} - {event.entity_type}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </section>
    </main>
  );
}
