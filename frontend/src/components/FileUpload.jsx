import { useState } from "react";
import axios from "axios";

function FileUpload({ onUpload }) {

    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(false);

    const uploadFile = async () => {

        if (!file) {
            alert("Please select a CSV file.");
            return;
        }

        const formData = new FormData();

        formData.append("file", file);

        setLoading(true);

        try {

            const response = await axios.post(
                "http://localhost:8000/upload/",
                formData
            );

            onUpload(response.data);

        } catch (error) {

            console.error(error);

            alert(
                error.response?.data?.detail ||
                "Upload failed."
            );

        } finally {

            setLoading(false);
        }
    };


    return (
        <div>

            <input
                type="file"
                accept=".csv"
                onChange={(e) =>
                    setFile(e.target.files[0])
                }
            />

            <button
                onClick={uploadFile}
                disabled={loading}
            >
                {loading ? "Uploading..." : "Upload CSV"}
            </button>

        </div>
    );
}

export default FileUpload;