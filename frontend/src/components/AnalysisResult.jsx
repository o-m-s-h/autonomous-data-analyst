function formatValue(value) {
    if (value === null || value === undefined) return "Not available";
    if (typeof value === "number") {
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
    const paragraphs = (result.explanation || "No answer was returned. Please try again.")
        .split(/\n\s*\n/).filter(Boolean);

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
                                    {item.truncated && !item.rows?.length ? (
                                        <p>The result is too large to display in this preview.</p>
                                    ) : (
                                        <EvidenceTable rows={item.rows ?? []} />
                                    )}
                                    {item.truncated && (
                                        <p>Showing {item.rows?.length ?? 0} of {item.row_count} result rows.
                                            This preview does not show the complete result.</p>
                                    )}
                                </>
                            )}
                            <details style={{ marginTop: 10 }}>
                                <summary style={{ cursor: "pointer" }}>Technical details (SQL)</summary>
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
