"""Export the v2.1.0 holdout figures used by the README."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ROOT / "artifacts" / "evaluation_metrics.json"
OUTPUT_DIR = ROOT / "docs" / "model-release-v2.1.0"


def main():
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    if metrics["model_version"] != "tf-phase2-drive-2.1.0":
        raise ValueError("Holdout metrics do not match the v2.1.0 release.")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        "font.size": 10,
        "axes.titlesize": 13,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })

    overall = pd.DataFrame(metrics["validation"]).T
    fig, axis = plt.subplots(figsize=(8, 4.5))
    overall.mul(100).plot.bar(ax=axis, color=["#087f75", "#a5c943"], width=0.72)
    axis.set(
        ylabel="Percent",
        xlabel="",
        ylim=(0, 108),
    )
    axis.set_xticklabels(
        ["Primary category", "Secondary category", "Urgency"], rotation=0
    )
    axis.grid(axis="y", alpha=0.2)
    axis.get_legend().remove()
    fig.suptitle("TensorForge 2.1.0 — held-out scores", y=0.98)
    fig.legend(
        ["Accuracy", "Macro-F1"],
        frameon=False,
        ncol=2,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.91),
    )
    for container in axis.containers:
        axis.bar_label(container, fmt="%.1f%%", padding=2, fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.84))
    fig.savefig(OUTPUT_DIR / "holdout-scores.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    labels = metrics["category_confusion_matrix"]["labels"]
    matrix = np.asarray(
        metrics["category_confusion_matrix"]["rows_actual_columns_predicted"]
    )
    fig, axis = plt.subplots(figsize=(11, 8), constrained_layout=True)
    image = axis.imshow(matrix, cmap="YlGnBu")
    axis.set(
        title="Primary category — held-out confusion matrix",
        xlabel="Predicted category",
        ylabel="Actual category",
        xticks=range(len(labels)),
        yticks=range(len(labels)),
    )
    axis.set_xticklabels(labels, rotation=55, ha="right")
    axis.set_yticklabels(labels)
    for row in range(len(labels)):
        for column in range(len(labels)):
            if matrix[row, column]:
                color = "white" if matrix[row, column] > matrix.max() * 0.58 else "#17332d"
                axis.text(
                    column,
                    row,
                    str(matrix[row, column]),
                    ha="center",
                    va="center",
                    fontsize=8,
                    color=color,
                )
    fig.colorbar(image, ax=axis, label="Ticket count")
    fig.savefig(OUTPUT_DIR / "category-confusion.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    language = pd.DataFrame(metrics["category_by_language"]).T.sort_index()
    fig, axis = plt.subplots(figsize=(8, 4.4), constrained_layout=True)
    language[["accuracy", "macro_f1"]].mul(100).plot.bar(
        ax=axis, color=["#087f75", "#a5c943"], width=0.76
    )
    axis.set(
        title="Primary category — held-out results by language",
        ylabel="Percent",
        xlabel="",
        ylim=(0, 106),
    )
    axis.set_xticklabels(language.index, rotation=0)
    axis.legend(["Accuracy", "Macro-F1"], frameon=False, ncol=2, loc="upper left")
    axis.grid(axis="y", alpha=0.2)
    fig.savefig(OUTPUT_DIR / "language-scores.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    index = {label: position for position, label in enumerate(labels)}
    pair_labels = ["lost_item", "delivery_delay"]
    pair_matrix = np.asarray([
        [matrix[index[actual], index[predicted]] for predicted in pair_labels]
        for actual in pair_labels
    ])
    fig, axis = plt.subplots(figsize=(6.5, 3.8), constrained_layout=True)
    image = axis.imshow(pair_matrix, cmap="YlGnBu", vmin=0, vmax=max(1, pair_matrix.max()))
    axis.set(
        title="Lost property vs delivery delay — held-out tickets",
        xticks=range(2),
        yticks=range(2),
        xticklabels=["Lost property", "Delivery delay"],
        yticklabels=["Lost property", "Delivery delay"],
        xlabel="Predicted",
        ylabel="Actual",
    )
    for row in range(2):
        for column in range(2):
            color = "white" if pair_matrix[row, column] > 0.58 * pair_matrix.max() else "#17332d"
            axis.text(
                column,
                row,
                str(pair_matrix[row, column]),
                ha="center",
                va="center",
                fontsize=14,
                color=color,
            )
    fig.colorbar(image, ax=axis, label="Ticket count")
    fig.savefig(OUTPUT_DIR / "delay-lost-confusion.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    print("Exported v2.1.0 README visuals to {}".format(OUTPUT_DIR))


if __name__ == "__main__":
    main()
