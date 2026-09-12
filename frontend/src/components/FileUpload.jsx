import { useRef, useState } from "react";
import { api, errorMessage } from "../api";
import Icon from "./Icon";

export default function FileUpload({ onUpload, dataset, disabled, onBusy }) {
    const input = useRef(null);
    const inFlight = useRef(false);
    const [loading, setLoading] = useState(false);
    const [dragging, setDragging] = useState(false);
    const [error, setError] = useState("");

    async function upload(file) {
        if (!file || disabled || inFlight.current) return;
        setError("");
        if (!file.name.toLowerCase().endsWith(".csv")) { setError("Please choose a CSV file."); return; }
        if (file.size === 0) { setError("This file is empty. Choose a CSV with some data."); return; }
        inFlight.current = true; setLoading(true); onBusy(true);
        try {
            const data = new FormData();
            // The backend checks a lowercase extension.
            data.append("file", file, file.name.replace(/\.csv$/i, ".csv"));
            const response = await api.post("/upload/", data);
            onUpload({ ...response.data, size: file.size });
        } catch (err) { setError(errorMessage(err, "The upload failed. Please try again.")); }
        finally { inFlight.current = false; setLoading(false); onBusy(false); if (input.current) input.current.value = ""; }
    }

    async function loadSample() {
        if (disabled || inFlight.current) return;
        setError("");
        try {
            const response = await fetch(`${import.meta.env.BASE_URL}demo-sales.csv`);
            if (!response.ok) throw new Error("Sample unavailable");
            const text = await response.text();
            await upload(new File([text], "demo-sales.csv", { type: "text/csv" }));
        } catch { setError("The sample could not be loaded. You can still upload your own CSV."); }
    }

    return <div className="upload-section">
        {dataset && <div className="dataset-card"><span className="file-icon"><Icon name="file" /></span><div><strong title={dataset.filename}>{dataset.filename}</strong><small>{dataset.size ? `${Math.max(1, Math.round(dataset.size / 1024))} KB · ` : ""}CSV dataset</small></div><Icon name="check" size={16} /></div>}
        <input ref={input} type="file" accept=".csv,text/csv" className="visually-hidden" tabIndex={-1} aria-label="Choose a CSV file" onChange={(event) => upload(event.target.files?.[0])} disabled={disabled || loading} />
        <button className={`upload-zone ${dragging ? "dragging" : ""}`} disabled={disabled || loading} onClick={() => input.current?.click()} onDragOver={(event) => { event.preventDefault(); if (!disabled) setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); if (!disabled) upload(event.dataTransfer.files?.[0]); }}>
            <span className="upload-icon"><Icon name="upload" size={22} /></span>
            <strong>{loading ? "Uploading your data…" : dataset ? "Replace dataset" : "Drop your CSV here"}</strong>
            <span>{loading ? "Getting everything ready" : "or click to browse files"}</span>
        </button>
        {error && <p role="alert" className="inline-error">{error}</p>}
        <button className="sample-button" disabled={disabled || loading} onClick={loadSample}><Icon name="spark" size={15} />Try a sample dataset<Icon name="arrow" size={15} /></button>
        <p className="sample-note">Sample: fictional monthly sales by region.</p>
    </div>;
}
