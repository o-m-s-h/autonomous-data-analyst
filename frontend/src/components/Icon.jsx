const paths = {
    spark: "m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z",
    upload: "M12 16V3m-5 5 5-5 5 5M4 15v5h16v-5",
    file: "M14 2H5v20h14V7Zm0 0v5h5M8 12h8m-8 4h8",
    arrow: "M4 12h16m-6-6 6 6-6 6",
    chart: "M4 3v17h17M8 15v-4m5 4V6m5 9V9",
    check: "m5 12 4 4L19 6",
    clock: "M12 8v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
    download: "M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4",
    search: "M21 21l-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0",
    layers: "m12 3 10 5-10 5L2 8Zm-10 9 10 5 10-5M2 16l10 5 10-5",
};
export default function Icon({ name = "spark", size = 20 }) {
    return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] || paths.spark} /></svg>;
}
