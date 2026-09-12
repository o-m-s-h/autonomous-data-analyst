import { useState } from "react";
import FileUpload from "./components/FileUpload";
import Chat from "./components/Chat";
import AnalysisResult from "./components/AnalysisResult";
import AnalysisErrorBoundary from "./components/AnalysisErrorBoundary";
import Icon from "./components/Icon";

export default function App() {
    const [dataset, setDataset] = useState(null);
    const [result, setResult] = useState(null);
    const [busy, setBusy] = useState(false);
    const [analyzing, setAnalyzing] = useState(false);
    const [history, setHistory] = useState([]);
    const [activeId, setActiveId] = useState(null);
    const [activeQuestion, setActiveQuestion] = useState("");

    function receiveResult(answer) {
        const entry = { id: Date.now(), answer };
        setResult(answer);
        setActiveId(entry.id);
        setHistory((previous) => [entry, ...previous].slice(0, 8));
    }

    return (
        <div className="app-shell">
            <a className="skip-link" href="#workspace">Skip to workspace</a>
            <aside className="sidebar" aria-label="Workspace sidebar">
                <a href="#workspace" className="brand"><span className="brand-mark"><Icon name="layers" size={25} /></span><span>Fieldwork<span className="brand-caption">YOUR DATA, UNDERSTOOD</span></span></a>
                <div className="workspace-label">WORKSPACE</div>
                <div className="nav-current"><Icon name="chart" /> Data analyst <span className="version-tag">V4</span></div>
                <div className="sidebar-section-title">Your dataset <span>01</span></div>
                <FileUpload dataset={dataset} disabled={busy} onBusy={setBusy} onUpload={(data) => {
                    setDataset(data); setResult(null); setHistory([]); setActiveId(null);
                }} />
                <div className="sidebar-section-title history-title">Recent questions <span>{history.length.toString().padStart(2, "0")}</span></div>
                <nav className="history-list" aria-label="Recent questions">
                    {history.length ? history.map((entry) => <button key={entry.id} disabled={busy} className={activeId === entry.id ? "history-item selected" : "history-item"} onClick={() => { setResult(entry.answer); setActiveId(entry.id); }}><Icon name="clock" size={16} /><span>{entry.answer.question}</span></button>) : <p className="sidebar-hint">Your investigations will appear here as you explore.</p>}
                </nav>
                <div className="sidebar-footer"><span className="small-logo"><Icon size={17} /></span><div>A little curiosity goes a long way.<small>Ask. Investigate. Understand.</small></div></div>
            </aside>

            <div className="main-shell">
                <header className="topbar"><div><span className="breadcrumb">Workspace</span><span className="breadcrumb-slash">/</span><strong>Data analyst</strong></div><span className="session-badge"><span className="status-dot" />{dataset ? "Dataset connected" : "Ready to explore"}</span></header>
                <main id="workspace" className="workspace">
                    <section className="page-intro"><div><div className="eyebrow">A CLEARER VIEW OF YOUR DATA</div><h1>From rows to <em>revelations.</em></h1><p>Bring your data. Ask a question. Find the story behind the numbers.</p></div><span className="intro-emblem" aria-hidden="true"><Icon name="spark" size={45} /></span></section>
                    <div className="context-strip"><span><Icon name="file" size={17} />{dataset ? dataset.filename : "No dataset selected"}</span><span>{dataset ? "Ready for your questions" : "Upload a CSV to get started"}<span className={dataset ? "status-dot" : "status-dot idle"} /></span></div>
                    <Chat key={dataset?.dataset_id || "empty"} datasetId={dataset?.dataset_id} disabled={busy} onStart={(question) => { setResult(null); setActiveId(null); setActiveQuestion(question); }} onBusy={(value) => { setBusy(value); setAnalyzing(value); }} onResult={receiveResult} />
                    {analyzing && <section className="analysis-loading panel" role="status" aria-live="polite"><span className="loading-orb"><Icon name="spark" size={26} /></span><div><div className="eyebrow">INVESTIGATION IN PROGRESS</div><h2>Following the evidence…</h2><p>{activeQuestion}</p><p className="muted">Checking your data and preparing the answer. This may take a moment.</p></div><div className="skeleton-lines" aria-hidden="true"><span /><span /><span /></div></section>}
                    {result && <AnalysisErrorBoundary key={activeId} onDismiss={() => setResult(null)}><AnalysisResult result={result} /></AnalysisErrorBoundary>}
                    {!result && !analyzing && <section className="empty-state"><div className="empty-visual" aria-hidden="true"><div className="mini-sheet"><span /><span /><span /><span /></div><span className="visual-connector" /><span className="visual-spark"><Icon name="spark" size={26} /></span><span className="visual-connector" /><div className="mini-bars"><i /><i /><i /><i /></div></div><h2>A good question changes the picture.</h2><p>{dataset ? "Choose a starting point above, or ask something of your own." : "Start with your own CSV, or load the sample dataset in the sidebar."}</p><div className="capability-row"><span><Icon name="search" size={16} />Find patterns</span><span><Icon name="chart" size={16} />See the story</span><span><Icon name="check" size={16} />Explore the evidence</span></div></section>}
                    <footer className="workspace-footer"><span>Fieldwork · Autonomous Data Analyst</span><span>Built for questions worth asking.</span></footer>
                </main>
            </div>
        </div>
    );
}
