import Chart from "./Chart";
import { answerText } from "../answerText";

function formatValue(value) {
    if (value === null || value === undefined) return "Not available";
    if (typeof value === "number") {
        if (value !== 0 && Math.abs(value) < 0.0001) return value.toExponential(2);
        return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
    }
    return String(value);
}

function EvidenceTable({ rows }) {
    if (!rows.length) return <p>No matching rows were found.</p>;
    const columns = Object.keys(rows[0]);
    return (
        <div style={{ overflowX: "auto" }}>
            <table style={{ borderCollapse: "collapse", width: "100%" }}>
                <thead>
                    <tr>{columns.map((column) => (
                        <th key={column} scope="col" style={cellStyle}>
                            {column.replaceAll("_", " ")}
                        </th>
                    ))}</tr>
                </thead>
                <tbody>
                    {rows.map((row, index) => (
                        <tr key={index}>{columns.map((column) => (
                            <td key={column} style={cellStyle}>{formatValue(row[column])}</td>
                        ))}</tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

const cellStyle = {
    padding: "10px 12px",
    borderBottom: "1px solid #dce2e8",
    textAlign: "left",
};

function AnalysisResult({ result }) {
    if (!result) return null;
    const evidence = result.evidence ?? (result.sql ? [{
        hypothesis: "Supporting data", sql: result.sql, rows: result.result ?? [],
    }] : []);
    const paragraphs = (answerText(result.explanation) || "No answer was returned. Please try again.")
        .split(/\n\s*\n/).filter(Boolean);
    const charts = result.charts ?? [];
    const chartFailed = evidence.some((item) => item.tool === "plot_chart" && item.error);
    // Only single-row SQL summaries qualify. Statistical coefficients/p-values
    // need their context and must not become headline metrics automatically.
    const summary = [...evidence].reverse().find((item) =>
        item.tool === "run_sql" && !item.error && !item.truncated && item.rows?.length === 1
    );
    const numberCards = summary && Object.values(summary.rows[0]).every((value) =>
        typeof value === "number" && Number.isFinite(value)
    ) && Object.keys(summary.rows[0]).length <= 4 ? Object.entries(summary.rows[0]) : [];

    return (
        <section aria-label="Analysis answer" style={{ maxWidth: 900, marginTop: 28 }}>
            <h2>Your answer</h2>
            <div style={{ lineHeight: 1.7, fontSize: 17 }}>
                {paragraphs.map((paragraph, index) => (
                    <p key={index} style={{
                        whiteSpace: "pre-wrap",
                        fontWeight: index === 0 ? 600 : 400,
                    }}>{paragraph}</p>
                ))}
            </div>
            {charts.length > 0 ? (
                <section aria-label="Charts">
                    <h3>Your data at a glance</h3>
                    {charts.map((chart, index) => <Chart key={chart.id || index} chart={chart} />)}
                </section>
            ) : numberCards.length > 0 ? (
                <section aria-label="Key numbers">
                    <h3>Key numbers</h3>
                    <dl style={{ display: "flex", flexWrap: "wrap", gap: 16, margin: "16px 0" }}>
                        {numberCards.map(([label, value]) => (
                            <div key={label} style={{ flex: "1 1 160px", padding: 20, borderRadius: 12, background: "#eff6ff", border: "1px solid #bfdbfe" }}>
                                <dt style={{ color: "#334155" }}>{label.replaceAll("_", " ")}</dt>
                                <dd style={{ margin: "8px 0 0", fontSize: 30, fontWeight: 650, color: "#1e3a8a", overflowWrap: "anywhere" }}>{formatValue(value)}</dd>
                            </div>
                        ))}
                    </dl>
                    <p style={{ color: "#596675", fontSize: 13 }}>From: {summary.hypothesis || "the selected data"}</p>
                </section>
            ) : null}
            {chartFailed && charts.length === 0 && (
                <p role="status">A chart could not be generated for this answer. You can still explore the available supporting data below.</p>
            )}
            {result.metrics && (
                <p style={{ color: "#596675", fontSize: 13 }}>
                    Completed in {result.metrics.elapsed_seconds}s
                </p>
            )}
            {evidence.length > 0 && (
                <details style={{ marginTop: 20 }}>
                    <summary style={{ cursor: "pointer" }}>Explore supporting data</summary>
                    {evidence.map((item, index) => (
                        <section key={index} style={{ marginTop: 20 }}>
                            <h3>{item.hypothesis || `Data check ${index + 1}`}</h3>
                            {item.error ? (
                                <p>This check could not be completed. It does not provide evidence.</p>
                            ) : (
                                <>
                                    {item.chart ? (
                                        <p>{item.chart.caption} The chart is shown above.</p>
                                    ) : item.truncated && !item.rows?.length ? (
                                        <p>The result is too large to display in this preview.</p>
                                    ) : (
                                        <EvidenceTable rows={item.rows ?? []} />
                                    )}
                                    {item.truncated && (
                                        <p>Showing {item.rows?.length ?? 0} of {item.row_count} result rows.
                                            This preview does not show the complete result.</p>
                                    )}
                                    {item.method && (
                                        <p>
                                            Used {item.rows_used} of {item.input_rows} selected records.
                                            {item.rows_excluded > 0 && ` Excluded ${item.rows_excluded} records with missing or invalid values.`}
                                            {item.r_squared != null && ` Model fit (R-squared): ${formatValue(item.r_squared)}.`}
                                        </p>
                                    )}
                                    {item.caveats?.length > 0 && (
                                        <details style={{ marginTop: 10 }}>
                                            <summary>How to interpret this check</summary>
                                            <ul>{item.caveats.map((caveat, i) => <li key={i}>{caveat}</li>)}</ul>
                                        </details>
                                    )}
                                </>
                            )}
                            <details style={{ marginTop: 10 }}>
                                <summary style={{ cursor: "pointer" }}>Technical details</summary>
                                {item.method && <p>Method: {item.method}</p>}
                                {item.parameters && Object.keys(item.parameters).length > 0 && (
                                    <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(item.parameters, null, 2)}</pre>
                                )}
                                <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
                                    {item.sql}
                                </pre>
                                {item.error && <pre style={{ whiteSpace: "pre-wrap" }}>{item.error}</pre>}
                            </details>
                        </section>
                    ))}
                </details>
            )}
        </section>
    );
}

export default AnalysisResult;
