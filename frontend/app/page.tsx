import {
  Activity,
  BarChart3,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  History,
  ShieldCheck,
  Upload
} from "lucide-react";
import { demoRun } from "@/lib/api";

const metrics = [
  { label: "Total Latest", value: demoRun.result.total_latest },
  { label: "Selected Ultimate", value: demoRun.result.total_ultimate },
  { label: "Total IBNR", value: demoRun.result.total_ibnr }
];

const auditEvents = [
  "Dataset uploaded: sample_triangle.csv",
  "Validation completed with no blocking warnings",
  "Chain ladder model run completed",
  "Default factors selected for review pack"
];

function currency(value: number) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
    style: "currency",
    currency: "USD"
  }).format(value);
}

export default function Home() {
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
            <p>Q4 reserving review</p>
            <h1>Commercial auto paid loss triangle</h1>
          </div>
          <button className="primaryButton">
            <FileSpreadsheet size={18} />
            Upload triangle
          </button>
        </header>

        <section className="metricGrid" aria-label="Reserve summary">
          {metrics.map((metric) => (
            <div className="metric" key={metric.label}>
              <span>{metric.label}</span>
              <strong>{currency(metric.value)}</strong>
            </div>
          ))}
        </section>

        <section className="contentGrid">
          <div className="panel wide" id="dashboard">
            <div className="panelHeader">
              <div>
                <span>Chain ladder</span>
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
                  {demoRun.originPeriods.map((origin, index) => (
                    <tr key={origin}>
                      <td>{origin}</td>
                      <td>{currency(demoRun.result.latest_diagonal[index])}</td>
                      <td>{currency(demoRun.result.ultimate_by_origin[index])}</td>
                      <td>{currency(demoRun.result.ibnr_by_origin[index])}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="panel" id="runs">
            <div className="panelHeader">
              <div>
                <span>Factors</span>
                <h2>Selected LDFs</h2>
              </div>
            </div>
            <div className="factorList">
              {demoRun.result.age_to_age_factors.map((factor, index) => (
                <div key={demoRun.developmentPeriods[index]}>
                  <span>
                    {demoRun.developmentPeriods[index]} to {demoRun.developmentPeriods[index + 1]}
                  </span>
                  <strong>{factor.toFixed(3)}</strong>
                </div>
              ))}
            </div>
          </div>

          <div className="panel" id="import">
            <div className="panelHeader">
              <div>
                <span>Import validation</span>
                <h2>Triangle checks</h2>
              </div>
            </div>
            <ul className="checkList">
              <li>Origin periods detected</li>
              <li>Development columns normalized</li>
              <li>Numeric values validated</li>
              <li>Missing tail cells accepted</li>
            </ul>
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
                <div key={event}>
                  <span />
                  <p>{event}</p>
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
              <button>
                <Download size={18} />
                Excel workbook
              </button>
              <button>
                <Download size={18} />
                PDF report
              </button>
            </div>
          </div>
        </section>
      </section>
    </main>
  );
}

