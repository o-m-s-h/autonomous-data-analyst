import { useRef, useState } from "react";
import { api, errorMessage } from "../api";
import Icon from "./Icon";

const starters = [
    { label: "Give me the big picture", detail: "A summary of what stands out", icon: "layers", question: "Summarize this dataset and highlight the most useful patterns, with a relevant chart." },
    { label: "Explore a trend", detail: "See how the numbers change", icon: "chart", question: "If this dataset has a date column, show how its main numeric measures change over time. Otherwise, explain which trends can be explored." },
    { label: "Find the unexpected", detail: "Spot unusual values or patterns", icon: "search", question: "Identify unusual values or patterns in this dataset. Explain what stands out, with supporting numbers and a useful chart." },
];

export default function Chat({ datasetId, disabled, onResult, onStart, onBusy }) {
    const [question, setQuestion] = useState("");
    const [includeVisuals, setIncludeVisuals] = useState(true);
    const [error, setError] = useState("");
    const textarea = useRef(null);
    const inFlight = useRef(false);

    async function ask(event) {
        event.preventDefault();
        if (!datasetId || disabled || inFlight.current || !question.trim()) return;
        inFlight.current = true; setError(""); onStart(question.trim()); onBusy(true);
        try {
            const response = await api.post("/analysis/ask", { dataset_id: datasetId, question: question.trim(), include_visuals: includeVisuals });
            onResult(response.data);
        } catch (err) { setError(errorMessage(err, "Something went wrong with this analysis. Please try again.")); }
        finally { inFlight.current = false; onBusy(false); }
    }

    return <section className="question-section" aria-label="Ask your data">
        <form className="composer panel" onSubmit={ask}>
            <label htmlFor="question" className="composer-label"><Icon name="spark" size={18} />What would you like to understand?</label>
            <textarea id="question" ref={textarea} value={question} maxLength={4000} disabled={!datasetId || disabled} onChange={(event) => setQuestion(event.target.value)} placeholder={datasetId ? "For example, which region is driving the most sales?" : "Upload a dataset to start exploring…"} rows={3} onKeyDown={(event) => { if ((event.ctrlKey || event.metaKey) && event.key === "Enter") { event.preventDefault(); event.currentTarget.form.requestSubmit(); } }} />
            <div className="composer-actions"><label className="visual-option"><input type="checkbox" checked={includeVisuals} onChange={(event) => setIncludeVisuals(event.target.checked)} disabled={disabled} /><Icon name="chart" size={16} />Include useful charts</label><div className="submit-group"><span className="keyboard-hint">Ctrl / ⌘ + Enter</span><button className="primary-button" disabled={!datasetId || disabled || !question.trim()} type="submit">Explore data<Icon name="arrow" size={17} /></button></div></div>
        </form>
        {error && <p className="inline-error panel-error" role="alert">{error}</p>}
        <div className="starter-grid">{starters.map((starter) => <button key={starter.label} className="starter-card" disabled={!datasetId || disabled} onClick={() => { setQuestion(starter.question); textarea.current?.focus(); }}><Icon name={starter.icon} size={19} /><span><strong>{starter.label}</strong><small>{starter.detail}</small></span><span className="starter-arrow">↗</span></button>)}</div>
    </section>;
}
