"""Headless Matplotlib charts returned in memory, with no generated files."""
import base64
from io import BytesIO
from threading import Lock

import pandas as pd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from app.tools.python_tool import load_frame, prepare_frame, json_result

_PLOT_LOCK = Lock()  # Matplotlib rendering is not thread-safe across API requests.
CHART_KINDS = {"bar", "line", "scatter", "histogram", "box"}


def create_chart(file_path, sql, kind, x, y="", title=""):
    if kind not in CHART_KINDS:
        raise ValueError(f"Choose a supported chart: {', '.join(sorted(CHART_KINDS))}.")
    frame = load_frame(file_path, sql)
    columns = [x] if kind == "histogram" else [x, y]
    if len(columns) == 2 and x == y:
        raise ValueError("Choose distinct x and y columns.")
    numeric = [x] if kind == "histogram" else ([x, y] if kind == "scatter" else [y])
    if kind == "line" and x in frame and pd.api.types.is_numeric_dtype(frame[x]):
        numeric = [x, y]
    clean, excluded = prepare_frame(frame, columns, numeric)
    if kind == "line":
        if not pd.api.types.is_numeric_dtype(clean[x]):
            clean[x] = pd.to_datetime(clean[x], errors="coerce", utc=True)
        clean = clean.dropna(subset=[x])
        excluded = len(frame) - len(clean)
        if clean.empty or clean[x].duplicated().any():
            raise ValueError("Line charts need unique numeric/date x values. Aggregate to one row per x in SQL.")
        clean = clean.sort_values(x)
    if kind in {"line", "scatter"} and len(clean) > 5000:
        raise ValueError("This chart exceeds 5000 points. Use a meaningful aggregate or explicitly described sample in SQL.")
    if kind == "bar" and (len(clean) > 40 or clean[x].duplicated().any()):
        raise ValueError("Bar charts need at most 40 rows, one per category. Aggregate and order in SQL.")
    if kind == "box" and clean[x].nunique() > 12:
        raise ValueError("Box plots support at most 12 groups. Select meaningful groups in SQL.")
    title = (title.strip() or f"{y + ' by ' if y else ''}{x}")[:120]
    notes = [f"Based on {len(clean):,} rows returned by the chart query."]
    if excluded:
        notes.append(f"Excluded {excluded:,} rows with missing or invalid chart values.")
    summary = {
        column: {"minimum": clean[column].min(), "maximum": clean[column].max()}
        for column in numeric
    }
    with _PLOT_LOCK:
        figure = Figure(figsize=(9, 4.8), layout="constrained")
        FigureCanvasAgg(figure)
        ax = figure.subplots()
        if kind == "histogram":
            ax.hist(clean[x], bins=30, color="#2563eb", edgecolor="white")
            ax.set_ylabel("Number of records")
        elif kind == "scatter":
            ax.scatter(clean[x], clean[y], s=18, alpha=0.5, color="#2563eb")
        elif kind == "line":
            ax.plot(clean[x], clean[y], color="#2563eb", linewidth=2)
            ax.tick_params(axis="x", labelrotation=30)
        elif kind == "bar":
            positions = range(len(clean))
            ax.bar(positions, clean[y], color="#2563eb")
            ax.set_xticks(list(positions))
            ax.set_xticklabels([str(v)[:60] for v in clean[x]], rotation=40, ha="right")
            # Include zero even when some values are negative.
            low, high = ax.get_ylim()
            ax.set_ylim(min(0, low), max(0, high))
        else:
            groups = list(clean[x].unique())
            ax.boxplot([clean.loc[clean[x] == group, y] for group in groups])
            ax.set_xticks(list(range(1, len(groups) + 1)))
            ax.set_xticklabels([str(v)[:60] for v in groups], rotation=30, ha="right")
        ax.set_title(title, loc="left", fontsize=14, pad=14, parse_math=False)
        ax.set_xlabel(x[:100], parse_math=False)
        if kind != "histogram":
            ax.set_ylabel(y[:100], parse_math=False)
        ax.grid(axis="y", alpha=0.2)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        with BytesIO() as buffer:
            figure.savefig(buffer, format="png", dpi=120)
            image = base64.b64encode(buffer.getvalue()).decode("ascii")
        figure.clear()
    caption = " ".join(notes)
    return json_result({
        "chart": {
            "kind": kind, "title": title, "x": x, "y": y,
            "caption": caption, "alt": f"{kind.capitalize()} chart: {title}. {caption}",
            "image": "data:image/png;base64," + image,
        },
        "rows_used": len(clean), "rows_excluded": excluded,
        "summary": summary,
    })
