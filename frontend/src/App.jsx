import React from "react";
import { useState } from "react";
import FileUpload from "./components/FileUpload";
import Chat from "./components/Chat";
import AnalysisResult from "./components/AnalysisResult";


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


            <AnalysisResult
                result={result}
            />

        </div>
    );
}


export default App;