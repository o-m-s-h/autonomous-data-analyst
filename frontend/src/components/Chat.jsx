import { useState } from "react";
import axios from "axios";

function Chat({ datasetId, onResult }) {

    const [question, setQuestion] = useState("");
    const [loading, setLoading] = useState(false);


    const askQuestion = async () => {

        if (!question.trim()) {
            return;
        }

        if (!datasetId) {
            alert("Upload a CSV first.");
            return;
        }

        setLoading(true);

        try {

            const response = await axios.post(
                "http://localhost:8000/analysis/ask",
                {
                    dataset_id: datasetId,
                    question: question
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

            <button
                onClick={askQuestion}
                disabled={loading}
            >
                {loading
                    ? "Analyzing..."
                    : "Ask"}
            </button>

        </div>
    );
}

export default Chat;