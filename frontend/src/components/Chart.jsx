import { useState } from "react";
import Icon from "./Icon";

export default function Chart({ chart }) {
    const [failedImage, setFailedImage] = useState(null);
    const valid = typeof chart?.image === "string" && chart.image.startsWith("data:image/png;base64,");
    if (!valid || failedImage === chart.image) return <p className="inline-error" role="status">This chart couldn't be displayed. Your answer and supporting evidence are still available.</p>;
    return <figure className="chart-card panel"><div className="chart-card-header"><span><Icon name="chart" size={18} />{typeof chart.title === "string" ? chart.title : "Data visualization"}</span><a className="chart-download" href={chart.image} download={`${chart.id || "analysis-chart"}.png`}><Icon name="download" size={16} />Download PNG</a></div><img src={chart.image} alt={typeof chart.alt === "string" ? chart.alt : "Analysis chart"} onError={() => setFailedImage(chart.image)} /><figcaption>{typeof chart.caption === "string" ? chart.caption : ""}</figcaption></figure>;
}
