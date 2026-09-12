import React from "react";
import { useState } from "react";
import FileUpload from "./components/FileUpload";
import Chat from "./components/Chat";
import AnalysisResult from "./components/AnalysisResult";
import AnalysisErrorBoundary from "./components/AnalysisErrorBoundary";


function App() {

    const [dataset, setDataset] = useState(null);
    const [result, setResult] = useState(null);


    return (
        <div>

            <h1>
                Autonomous Data Analyst
            </h1>


            <FileUpload
                onUpload={(data) => {
                    setDataset(data);
                    setResult(null);
                }}
            />


            {dataset && (
                <div>

                    <p>
                        Dataset uploaded:
                        {" "}
                        {dataset.filename}
                    </p>

                    <Chat
                        datasetId={dataset.dataset_id}
                        onResult={setResult}
                    />

                </div>
            )}


            {result && (
                <AnalysisErrorBoundary onDismiss={() => setResult(null)}>
                    <AnalysisResult result={result} />
                </AnalysisErrorBoundary>
            )}

        </div>
    );
}


export default App;
