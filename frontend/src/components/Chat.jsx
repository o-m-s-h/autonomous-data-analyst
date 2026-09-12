import { useState } from "react";
import axios from "axios";

function Chat({ datasetId, onResult }) {

    const [question, setQuestion] = useState("");
    const [loading, setLoading] = useState(false);
    const [includeVisuals, setIncludeVisuals] = useState(true);


    const askQuestion = async () => {

        if (!question.trim()) {
            return;
        }

        if (!datasetId) {
            alert("Upload a CSV first.");
            return;
        }

        setLoading(true);
        onResult(null);

        try {

            const response = await axios.post(
                "http://localhost:8000/analysis/ask",
                {
                    dataset_id: datasetId,
                    question: question,
                    include_visuals: includeVisuals,
                }
            );

            onResult(response.data);

        } catch (error) {

            console.error(error);

            alert(
                error.response?.data?.detail ||
                "Analysis failed."
            );

        } finally {

            setLoading(false);
        }
    };


    return (
        <div>

            <textarea
                value={question}
                onChange={(e) =>
                    setQuestion(e.target.value)
                }
                placeholder="Ask a question about your data..."
                rows={4}
            />

            <label style={{ display: "block", margin: "12px 0" }}>
                <input
                    type="checkbox"
                    checked={includeVisuals}
                    onChange={(event) => setIncludeVisuals(event.target.checked)}
                    disabled={loading}
                />
                {" "}Include charts when useful
            </label>

            <button
                onClick={askQuestion}
                disabled={loading}
            >
                {loading
                    ? "Analyzing..."
                    : "Ask"}
            </button>

            {loading && (
                <p role="status" aria-live="polite">
                    {includeVisuals ? "Analyzing your data and preparing useful visuals…" : "Analyzing your data…"}
                </p>
            )}

        </div>
    );
}

export default Chat;
