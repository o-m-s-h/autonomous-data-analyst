import { useState } from "react";

function Chart({ chart }) {
    const [failedImage, setFailedImage] = useState(null);
    const validImage = chart?.image?.startsWith("data:image/png;base64,");
    if (!validImage || failedImage === chart.image) {
        return <p role="status">This chart could not be displayed. The answer and supporting data are still available.</p>;
    }
    return (
        <figure style={{ margin: "24px 0", padding: 16, border: "1px solid #dce2e8", borderRadius: 12 }}>
            <img
                src={chart.image}
                alt={chart.alt || chart.title}
                onError={() => setFailedImage(chart.image)}
                style={{ display: "block", width: "100%", height: "auto" }}
            />
            <figcaption style={{ lineHeight: 1.6, color: "#596675" }}>
                {chart.caption}
                {" "}
                <a href={chart.image} download={`${chart.id || "analysis-chart"}.png`}>
                    Download chart
                </a>
            </figcaption>
        </figure>
    );
}

export default Chart;
