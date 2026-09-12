import { useState } from "react";
import Chart from "./Chart";
import Icon from "./Icon";
import { answerText } from "../answerText";

const isRecord = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const records = (value) => Array.isArray(value) ? value.filter(isRecord) : [];
const text = (value) => typeof value === "string" ? value : "";
function formatValue(value) {
    if (value == null) return "Not available";
    if (typeof value === "number") {
        if (!Number.isFinite(value)) return "Not available";
        if (value !== 0 && Math.abs(value) < 0.0001) return value.toExponential(2);
        return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
    }
    return typeof value === "object" ? JSON.stringify(value) : String(value);
}
function EvidenceTable({ rows }) {
    const data = records(rows);
    if (!data.length) return <p className="muted">No matching rows were returned.</p>;
    const columns = Object.keys(data[0]);
    return <div className="table-scroll" tabIndex={0} role="region" aria-label="Query result table"><table><thead><tr>{columns.map((column) => <th key={column} scope="col">{column.replaceAll("_", " ")}</th>)}</tr></thead><tbody>{data.map((row, index) => <tr key={index}>{columns.map((column) => <td key={column}>{formatValue(row[column])}</td>)}</tr>)}</tbody></table></div>;
}

export default function AnalysisResult({ result }) {
    const [view, setView] = useState("overview");
    const [copyStatus, setCopyStatus] = useState("");
    if (!result) return null;
    const explanation = answerText(result.explanation) || "No answer was returned. Please try again.";
    const evidence = records(result.evidence ?? (result.sql ? [{ hypothesis: "Supporting data", sql: result.sql, rows: result.result }] : []));
    const charts = records(result.charts);
    const summary = [...evidence].reverse().find((item) => item.tool === "run_sql" && !item.error && !item.truncated && records(item.rows).length === 1);
    const row = summary ? records(summary.rows)[0] : null;
    const metrics = row && Object.keys(row).length <= 4 && Object.values(row).every((value) => typeof value === "number" && Number.isFinite(value)) ? Object.entries(row) : [];
    const chartFailed = evidence.some((item) => item.tool === "plot_chart" && item.error);
    async function copyAnswer() {
        try { await navigator.clipboard.writeText(explanation); setCopyStatus("Answer copied"); }
        catch { setCopyStatus("Couldn't copy. Select the answer text to copy it."); }
    }

    return <section className="results-section" aria-label="Analysis results">
        <div className="results-heading"><div><div className="eyebrow">THE FINDINGS</div><h2>A little more clarity.</h2></div><div className="result-meta">{Number.isFinite(result.metrics?.elapsed_seconds) && <span><Icon name="clock" size={14} />{result.metrics.elapsed_seconds}s</span>}<span className="complete-badge"><Icon name="check" size={14} />Analysis complete</span></div></div>
        <div className="result-switcher" role="group" aria-label="Result view"><button aria-pressed={view === "overview"} className={view === "overview" ? "active" : ""} onClick={() => setView("overview")}>Overview</button><button aria-pressed={view === "evidence"} className={view === "evidence" ? "active" : ""} onClick={() => setView("evidence")}>Supporting evidence <span>{evidence.length}</span></button></div>
        {view === "overview" ? <>
            <article className="answer-card panel"><div className="answer-topline"><span className="answer-identity"><span className="answer-mark"><Icon name="spark" size={18} /></span>FIELDWORK ANALYST</span><button className="text-button" onClick={copyAnswer}>Copy answer</button></div><h3 className="asked-question">{text(result.question)}</h3><div className="answer-prose">{explanation.split(/\n\s*\n/).filter(Boolean).map((paragraph, index) => <p key={index}>{paragraph}</p>)}</div>{copyStatus && <p className="muted" role="status">{copyStatus}</p>}</article>
            {metrics.length > 0 && <section className="key-numbers" aria-label="Key numbers"><dl className="metric-grid">{metrics.map(([label, value]) => <div className="metric-card" key={label}><dt>{label.replaceAll("_", " ")}</dt><dd>{formatValue(value)}</dd><span className="metric-rule" /></div>)}</dl><p className="source-note">Source: {text(summary.hypothesis) || "selected data"}</p></section>}
            {charts.length > 0 && <section className="chart-section" aria-label="Charts"><div className="section-heading"><h3>Your data, in perspective.</h3><span>{charts.length} visual{charts.length > 1 ? "s" : ""}</span></div>{charts.map((chart, index) => <Chart key={chart.id || index} chart={chart} />)}</section>}
            {chartFailed && !charts.length && <p className="inline-error" role="status">A chart couldn't be generated. The answer and supporting evidence are still available.</p>}
        </> : <div className="evidence-list">{evidence.length === 0 && <div className="panel empty-evidence"><p>No supporting checks were returned for this answer.</p></div>}{evidence.map((item, index) => <article className="evidence-card panel" key={index}><div className="evidence-heading"><span className="check-index">{String(index + 1).padStart(2, "0")}</span><h3>{text(item.hypothesis) || "Data check"}</h3><span className={item.error ? "check-status error" : "check-status"}>{item.error ? "Not completed" : item.cached ? "Reused result" : "Completed"}</span></div>
            {item.error ? <p className="inline-error">This check could not be completed and does not provide evidence.</p> : <>
                {item.chart ? <p className="muted">{text(item.chart.caption)} View the chart in Overview.</p> : item.truncated && !records(item.rows).length ? <p className="muted">The result is too large for this preview.</p> : <EvidenceTable rows={item.rows} />}
                {item.truncated && <p className="source-note">Showing {records(item.rows).length} of {formatValue(item.row_count)} rows. This is a partial preview.</p>}
                {item.method && <p className="source-note">Used {formatValue(item.rows_used)} of {formatValue(item.input_rows)} records. {item.rows_excluded > 0 ? `Excluded ${formatValue(item.rows_excluded)} missing or invalid records.` : ""}{item.r_squared != null ? ` Model fit (R-squared): ${formatValue(item.r_squared)}.` : ""}</p>}
                {Array.isArray(item.caveats) && item.caveats.length > 0 && <details className="technical-details"><summary>How to interpret this check</summary><ul>{item.caveats.map((caveat, i) => <li key={i}>{formatValue(caveat)}</li>)}</ul></details>}
            </>}
            <details className="technical-details"><summary>Technical details & SQL</summary>{item.method && <p>Method: {text(item.method)}</p>}{item.parameters && <pre>{JSON.stringify(item.parameters, null, 2)}</pre>}<pre>{text(item.sql)}</pre>{item.error && <pre>{formatValue(item.error)}</pre>}</details>
        </article>)}</div>}
    </section>;
}
