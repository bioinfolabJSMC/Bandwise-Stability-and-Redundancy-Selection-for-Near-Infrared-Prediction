"""Publication figures for the SPXY-partitioned, calibration-selected analysis.

Run after analysis.py has produced results/analysis. No models are retuned here.
Times New Roman is required; use --font-dir for a locally licensed font folder.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os

os.environ.setdefault("MPLBACKEND", "Agg")
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors, font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle
from PIL import Image
from sklearn.decomposition import PCA
from analysis import pret_pair

ROOT = Path(__file__).resolve().parent
ANA = ROOT / "results" / "analysis"
OUT = ROOT / "results" / "figures"
METHODS = ["Full", "UVE", "MC-UVE", "RT", "C-value", "BSRS"]
DISPLAY = {"Full": "Full spectrum", "UVE": "UVE rank", "MC-UVE": "MC-UVE rank",
           "RT": "RT", "C-value": "C-value adapted", "BSRS": "BSRS"}
PRETS = ["Raw", "MSC", "SNV", "CWT", "D1", "D2"]
BLUE = "#0000ff"
RED = "#ff0000"
ORANGE = "#e67e00"
GREEN = "#00a000"
GREY = "#333333"
PURPLE = "#ff00ff"
METHOD_COLORS = {"Full": "#000000", "UVE": BLUE, "MC-UVE": GREEN,
                 "RT": PURPLE, "C-value": ORANGE, "BSRS": RED}
UNIT = r"mg g$^{-1}$"
CAPTIONS = {
    "Figure_1": "Flowcharts of (a) the calibration and prediction procedure and (b) bandwise stability and redundancy selection (BSRS). The 84 spectra contain 141 variables. SPXY assigns 63 samples to calibration and 21 to prediction. Reliability is estimated from 100 subsamples; variable budgets and latent-variable counts are selected using fivefold calibration cross-validation.",
    "Figure_2": "Raw spectral data: (a) spectra of all 84 samples, each containing 141 measured variables, and (b) reference C21 steroidal glycoside equivalent contents by sample index. Colors distinguish spectra; A.U. denotes the recorded optical response.",
    "Figure_3": "Characteristics of the SPXY partition: (a) reference-content distributions, (b) density histograms, (c) principal-component scores and (d) reference-content ranges and means for the calibration (n = 63) and prediction (n = 21) sets. PCA is fitted to calibration spectra and used only to display the frozen partition; SPXY uses the normalized Euclidean spectral and reference-content distances across all 141 raw spectral variables.",
    "Figure_4": "Full-spectrum PLS under six preprocessing conditions. Blue bars show fivefold calibration RMSECV and red bars show prediction RMSEP; the green star identifies the preprocessing selected using calibration RMSECV. LV denotes the selected number of latent variables.",
    "Figure_5": "Performance and retained variable counts for full-spectrum PLS, UVE rank, MC-UVE rank, RT, adapted C-value and BSRS: (a) fivefold calibration RMSECV (open squares) and prediction RMSEP (circles), and (b) selected variable counts. The green star marks the minimum-calibration-RMSECV method. UVE and MC-UVE use cross-validated reliability-rank prefixes; the C-value random design is explicitly adapted.",
    "Figure_6": "Reference and predicted C21 steroidal glycoside equivalent contents for full-spectrum PLS, MC-UVE rank and BSRS (columns). Panels (a-c) show calibration fits (n = 63), and panels (d-f) show prediction results (n = 21). Blue circles show predicted versus reference contents; red lines are descriptive linear fits, and black dashed lines indicate identity.",
    "Figure_7": "Wavelength positions retained by UVE (blue), MC-UVE (green), RT (magenta), adapted C-value (orange) and BSRS (red). Counts are shown in parentheses; the black line is the normalized mean raw calibration spectrum. Selected positions for derivative and CWT models refer to their uniform working grid.",
    "Figure_S1": "Calibration spectra under (a) raw, (b) MSC, (c) SNV, (d) CWT, (e) first-derivative and (f) second-derivative preprocessing. Thin blue curves represent individual samples and black curves their means. MSC references use calibration samples; derivatives and CWT use uniform wavelength grids. Vertical scales retain the units of each transformation.",
    "Figure_S2": "Prediction residuals for the calibration-selected {best_method} model: (a) residuals versus reference content and (b) residual distribution for the 21 prediction samples. Black lines indicate zero error and red dashed lines indicate mean bias.",
    "Figure_S3": "BSRS diagnostics: (a) log coefficient reliability, (b) sign consistency, (c) the five-variable local mean of sign-weighted log reliability and (d) fivefold selection frequency. Red points mark selected variables. Reliability uses 100 subsamples containing 80% of calibration samples without replacement; selection frequency describes consistency across calibration folds.",
    "Figure_S4": "BSRS component ablations with separately optimized variable budgets and latent-variable counts. Blue bars show fivefold calibration RMSECV and red bars show prediction RMSEP. Each ablation omits sign weighting, local smoothing or redundancy penalization.",
}


def configure_fonts(font_dir=None):
    """Fail explicitly if the requested family is unavailable."""
    candidates = []
    if font_dir:
        folder = Path(font_dir).expanduser().resolve()
        if not folder.is_dir():
            raise FileNotFoundError(f"Font folder does not exist: {folder}")
        candidates.extend(folder.glob("*.ttf"))
        candidates.extend(folder.glob("*.otf"))
    windows_fonts = Path("C:/Windows/Fonts")
    candidates.extend(windows_fonts / name for name in
                      ["times.ttf", "timesbd.ttf", "timesi.ttf", "timesbi.ttf"])
    for path in candidates:
        if path.is_file():
            font_manager.fontManager.addfont(str(path))
    font_paths = {}
    for label, style, weight in [("regular", "normal", "normal"),
                                 ("bold", "normal", "bold"),
                                 ("italic", "italic", "normal")]:
        properties = font_manager.FontProperties(family="Times New Roman", style=style,
                                                  weight=weight)
        try:
            path = Path(font_manager.findfont(properties, fallback_to_default=False))
        except ValueError as exc:
            raise RuntimeError("Times New Roman is required for publication figures. "
                               "Install the licensed font or pass --font-dir FONT_FOLDER. "
                               "No substitute font will be used.") from exc
        if not path.is_file() or font_manager.FontProperties(fname=str(path)).get_name() != "Times New Roman":
            raise RuntimeError(f"Times New Roman {label} could not be verified: {path}")
        font_paths[label] = str(path)
    plt.rcParams.update({
        "font.family": "Times New Roman", "font.size": 12, "axes.labelsize": 13,
        "axes.titlesize": 13, "xtick.labelsize": 10.5, "ytick.labelsize": 10.5,
        "legend.fontsize": 9, "axes.linewidth": 1.0, "lines.linewidth": .9,
        "savefig.dpi": 300, "figure.dpi": 120, "mathtext.fontset": "custom",
        "mathtext.rm": "Times New Roman", "mathtext.it": "Times New Roman:italic",
        "mathtext.bf": "Times New Roman:bold", "svg.fonttype": "none",
        "pdf.fonttype": 42, "axes.spines.top": True, "axes.spines.right": True,
        "axes.edgecolor": "black", "axes.facecolor": "white", "figure.facecolor": "white",
        "xtick.direction": "in", "ytick.direction": "in",
        "xtick.top": True, "ytick.right": True,
        "xtick.minor.visible": True, "ytick.minor.visible": True,
        "legend.handlelength": 1.5, "legend.handletextpad": .4,
        "legend.labelspacing": .25, "legend.borderaxespad": .6,
        "axes.unicode_minus": False,
    })
    return font_paths


def style(ax):
    for spine in ax.spines.values():
        spine.set_visible(True); spine.set_color("black"); spine.set_linewidth(1.0)
    ax.minorticks_on()
    ax.tick_params(which="major", direction="in", length=4, width=.8, top=True, right=True)
    ax.tick_params(which="minor", direction="in", length=2.2, width=.6, top=True, right=True)
    ax.grid(False, which="both", axis="both")
    ax.set_facecolor("white")


def panel(ax, letter, title):
    # The panel meaning is described in the caption, as in the reference layout.
    ax.text(.025, .975, f"({letter})", transform=ax.transAxes,
            va="top", ha="left", fontsize=12, color="black", zorder=10)


class FigureBuilder:
    def __init__(self):
        required = ["clean_data.npz", "variable_selection.csv", "preprocessing.csv",
                    "predictions.csv", "split_summary.csv", "selection_details.json",
                    "ablation.csv", "run_summary.json"]
        missing = [name for name in required if not (ANA / name).is_file()]
        if missing:
            raise FileNotFoundError("Analysis must finish before plotting; missing: " + ", ".join(missing))
        self.hashes = {name: hashlib.sha256((ANA / name).read_bytes()).hexdigest() for name in required}
        self.data = np.load(ANA / "clean_data.npz")
        self.y, self.cal, self.test = [self.data[key] for key in ["y", "cal", "test"]]
        self.x, self.w = self.data["X"], self.data["w"]
        if self.x.shape != (len(self.y), 141) or len(self.w) != 141 or not np.all(np.diff(self.w) > 0):
            raise ValueError("Spectral data must contain exactly 141 variables at strictly ascending wavelengths.")
        if len(self.cal) != 63 or len(self.test) != 21 or np.intersect1d(self.cal, self.test).size:
            raise ValueError("The SPXY partition must contain 63 calibration and 21 prediction samples.")
        self.perf = pd.read_csv(ANA / "variable_selection.csv")
        if set(self.perf.method) != set(METHODS) or len(self.perf) != len(METHODS):
            raise ValueError("The method table must contain exactly the six configured comparison methods.")
        self.perf = self.perf.set_index("method").loc[METHODS].reset_index()
        self.pre = pd.read_csv(ANA / "preprocessing.csv").set_index("pretreatment").loc[PRETS].reset_index()
        self.pred = pd.read_csv(ANA / "predictions.csv")
        self.split = pd.read_csv(ANA / "split_summary.csv")
        if len(self.split) != 2 or set(self.split["set"]) != {"Calibration", "Prediction"}:
            raise ValueError("The split summary must describe only the calibration and prediction sets.")
        self.details = json.loads((ANA / "selection_details.json").read_text(encoding="utf-8"))
        self.ablation = pd.read_csv(ANA / "ablation.csv")
        self.run = json.loads((ANA / "run_summary.json").read_text(encoding="utf-8"))
        selected_method = self.run["calibration_selected_method"]
        selected_pre = self.run["chosen_preprocessing"]
        self.best = self.perf.set_index("method", drop=False).loc[selected_method]
        self.chosen_pre = self.pre.set_index("pretreatment", drop=False).loc[selected_pre]
        if self.best.RMSECV > self.perf.RMSECV.min() + 1e-10:
            raise ValueError("The selected method must minimize calibration RMSECV.")
        if self.chosen_pre.RMSECV > self.pre.RMSECV.min() + 1e-10:
            raise ValueError("The selected preprocessing must minimize calibration RMSECV.")
        self.captions = []
        self.quality = []
        OUT.mkdir(parents=True, exist_ok=True)

    def save(self, fig, stem, label, caption, svg=False):
        caption = CAPTIONS.get(stem, caption).format(best_method=DISPLAY[self.best["method"]])
        for extension in ["png", "tiff"]:
            kwargs = {"pil_kwargs": {"compression": "tiff_lzw"}} if extension == "tiff" else {}
            fig.savefig(OUT / f"{stem}.{extension}", dpi=300, facecolor="white", **kwargs)
        if svg:
            fig.savefig(OUT / f"{stem}.svg", facecolor="white")
        record = {"stem": stem, "figure_label": label, "caption": caption,
                  "png": f"{stem}.png", "tiff": f"{stem}.tiff", "dpi": 300,
                  "font": "Times New Roman", "dimensions_inches": list(fig.get_size_inches())}
        dimensions = []
        for extension in ["png", "tiff"]:
            path = OUT / f"{stem}.{extension}"
            with Image.open(path) as im:
                dpi = im.info.get("dpi")
                if not dpi or any(abs(float(value) - 300) > .05 for value in dpi):
                    raise RuntimeError(f"300 dpi metadata verification failed: {path}")
                dimensions.append(im.size)
                self.quality.append({"file": path.name, "pixels": list(im.size),
                                     "dpi": [float(value) for value in dpi], "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        if dimensions[0] != dimensions[1]:
            raise RuntimeError(f"PNG and TIFF dimensions differ for {stem}")
        self.captions.append(record)
        plt.close(fig)
        print("Saved", label, stem, flush=True)

    def workflow(self):
        fig, axs = plt.subplots(1, 2, figsize=(8.6, 7.0), gridspec_kw={"width_ratios": [1, 1.1]})
        for ax in axs:
            ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        def box(ax, x, y, w, h, text, color="#e2edf8", terminal=False):
            if terminal:
                ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=.005,rounding_size=.035",
                                           linewidth=.8, edgecolor="black", facecolor="white"))
            else:
                ax.add_patch(Rectangle((x, y), w, h, linewidth=.8, edgecolor="black", facecolor=color))
            ax.text(x+w/2, y+h/2, text, ha="center", va="center", fontsize=11, linespacing=1.25)
        def arrow(ax, start, end):
            ax.add_patch(FancyArrowPatch(start, end, arrowstyle="->", mutation_scale=10,
                                        color="black", lw=.8))
        def sequence(ax, nodes, x, width):
            for position, height, text in nodes:
                box(ax, x, position, width, height, text)
            for first, second in zip(nodes, nodes[1:]):
                arrow(ax, (.5, first[0]), (.5, second[0]+second[1]))
        axs[0].text(.02, .99, "(a)", fontsize=12, va="top")
        nodes = [(.835, .12, f"Raw spectra and reference content\n{len(self.y)} samples; 141 measured variables"),
                 (.655, .12, f"SPXY sample partition (75:25)\n{len(self.cal)} calibration; {len(self.test)} prediction"),
                 (.46, .13, "Fivefold calibration tuning\nPreprocessing, variable subset and LV"),
                 (.245, .13, "Refit using calibration samples\nFreeze preprocessing and model"),
                 (.04, .13, "Held-out prediction\nRMSEP, R² and bias")]
        sequence(axs[0], nodes, .09, .82)
        ax = axs[1]; ax.text(.02, .99, "(b)", fontsize=12, va="top")
        for y, h, text in [(.855, .10, "100 subsamples (80%, no replacement)\nPLS coefficient vectors"),
                           (.715, .10, "Coefficient reliability $r_j$\nand sign consistency $s_j$"),
                           (.575, .10, r"$q_j=\log(1+r_j)s_j$" + "\n" +
                            r"$\bar{q}_j=$ five-point local mean of $q_j$"),
                           (.455, .08, "Initialize unranked variables")]:
            box(ax, .23, y, .70, h, text)
        for first, second in [(.855, .815), (.715, .675), (.575, .535), (.455, .44)]:
            arrow(ax, (.58, first), (.58, second))
        ax.add_patch(Polygon([[.58, .44], [.80, .38], [.58, .32], [.36, .38]],
                             closed=True, edgecolor="black", facecolor="white", lw=.8))
        ax.text(.58, .38, "Variables left?", ha="center", va="center", fontsize=10.5)
        box(ax, .23, .185, .70, .095,
            r"Choose max $\bar{q}_j/(1+2d_j^2)$" + "\n" +
            r"Update $d_j$: max $|$correlation$|$" + "\nwith selected variables")
        arrow(ax, (.58, .32), (.58, .28)); ax.text(.61, .302, "Yes", fontsize=10)
        ax.plot([.93, .985, .985], [.2325, .2325, .38], c="black", lw=.8)
        arrow(ax, (.985, .38), (.80, .38))
        ax.plot([.36, .09, .09, .58], [.38, .38, .15, .15], c="black", lw=.8)
        ax.text(.18, .39, "No", fontsize=10)
        arrow(ax, (.58, .15), (.58, .12))
        box(ax, .17, .02, .81, .10, "Complete ranking: tune prefix budget and LV\nby fivefold calibration CV")
        fig.subplots_adjust(left=.03, right=.98, top=.98, bottom=.025, wspace=.16)
        self.save(fig, "Figure_1", "Figure 1",
            CAPTIONS["Figure_1"], svg=True)

    def raw_spectra(self):
        fig, axs = plt.subplots(1, 2, figsize=(9, 4.1), gridspec_kw={"width_ratios": [1.25, 1]})
        ax = axs[0]; cmap = plt.get_cmap("turbo")
        for j, row in enumerate(self.x):
            ax.plot(self.w, row, color=cmap(j/max(len(self.x)-1, 1)), lw=.55, alpha=.85)
        ax.set_xlabel("Wavelength (nm)"); ax.set_ylabel("Recorded spectral response (A.U.)")
        panel(ax, "a", f"{self.x.shape[1]} measured spectral variables"); style(ax); ax.margins(x=.01)
        ax = axs[1]; ax.scatter(np.arange(len(self.y))+1, self.y, s=18,
                              edgecolors=BLUE, facecolors="none", linewidths=.8)
        ax.set_xlabel("Sample index"); ax.set_ylabel(f"Reference content ({UNIT})")
        panel(ax, "b", "Reference response"); style(ax)
        fig.subplots_adjust(left=.09, right=.98, bottom=.16, top=.965, wspace=.35)
        self.save(fig, "Figure_2", "Figure 2",
            CAPTIONS["Figure_2"])

    def sample_split(self):
        fig, axs = plt.subplots(2, 2, figsize=(9, 6.7))
        ax = axs[0, 0]
        for position, ids, color, label in [(0, self.cal, BLUE, "Calibration"), (1, self.test, RED, "Prediction")]:
            ax.boxplot(self.y[ids], positions=[position], widths=.5, showfliers=False,
                       boxprops={"color": "black", "linewidth": .8},
                       whiskerprops={"color": "black", "linewidth": .8},
                       capprops={"color": "black", "linewidth": .8},
                       medianprops={"color": RED, "linewidth": 1})
            # Deterministic offsets are visual only and do not change sample membership.
            ax.scatter(position+np.linspace(-.15, .15, len(ids)), self.y[ids], s=15,
                       edgecolors=color, facecolors="none", linewidths=.7)
        ax.set_xticks([0, 1], [f"Calibration\n(n = {len(self.cal)})", f"Prediction\n(n = {len(self.test)})"])
        ax.set_ylabel(f"Reference content ({UNIT})"); panel(ax, "a", "SPXY partition"); style(ax)
        ax = axs[0, 1]; bins = np.linspace(self.y.min()-1, self.y.max()+1, 10)
        ax.hist(self.y[self.cal], bins=bins, density=True, color=BLUE, alpha=.55, label="Calibration")
        ax.hist(self.y[self.test], bins=bins, density=True, color=RED, alpha=.4, label="Prediction")
        ax.set_xlabel(f"Reference content ({UNIT})"); ax.set_ylabel("Probability density")
        ax.legend(frameon=False, fontsize=9.5); panel(ax, "b", "Reference distributions"); style(ax)
        ax = axs[1, 0]; pca = PCA(n_components=5, svd_solver="full").fit(self.x[self.cal])
        scores = pca.transform(self.x)
        for ids, color, marker, label in [(self.cal, BLUE, "o", "Calibration"), (self.test, RED, "^", "Prediction")]:
            ax.scatter(scores[ids, 0], scores[ids, 1], c=color, marker=marker, s=27, alpha=.75, label=label)
        variance = pca.explained_variance_ratio_*100
        ax.set_xlabel(f"PC1 ({variance[0]:.1f}%)"); ax.set_ylabel(f"PC2 ({variance[1]:.1f}%)")
        ax.text(.03, .04, f"Five PCs: {variance.sum():.1f}% variance", transform=ax.transAxes, va="bottom", fontsize=9)
        ax.legend(frameon=False, fontsize=9.5); panel(ax, "c", "PCA fitted on calibration samples"); style(ax)
        ax = axs[1, 1]
        for j, (role, color) in enumerate([("Calibration", BLUE), ("Prediction", RED)]):
            row = self.split.loc[self.split["set"] == role].iloc[0]
            ax.plot([row["min"], row["max"]], [j, j], c=color, lw=2)
            ax.scatter(row["mean"], j, c=color, s=36, zorder=3)
        ax.set_yticks([0, 1], ["Calibration", "Prediction"])
        ax.set_ylim(1.6, -.6); ax.set_xlabel(f"Reference range and mean ({UNIT})")
        panel(ax, "d", "SPXY subset ranges"); style(ax)
        fig.subplots_adjust(left=.095, right=.98, top=.935, bottom=.095, hspace=.50, wspace=.45)
        self.save(fig, "Figure_3", "Figure 3",
            CAPTIONS["Figure_3"])

    def preprocessing_performance(self):
        fig, ax = plt.subplots(figsize=(8.7, 4.7)); pos = np.arange(len(PRETS))
        ax.bar(pos-.18, self.pre.RMSECV, width=.34, color=BLUE, alpha=.82, label="Calibration tuning RMSECV")
        ax.bar(pos+.18, self.pre.RMSEP, width=.34, color=RED, alpha=.8, label="Held-out RMSEP")
        selected = PRETS.index(self.chosen_pre.pretreatment)
        maximum = float(self.pre[["RMSECV", "RMSEP"]].to_numpy().max())
        ax.scatter(selected-.18, self.chosen_pre.RMSECV+maximum*.06, c=GREEN, marker="*", s=90, zorder=4)
        for j, row in self.pre.iterrows():
            ax.text(j, -.095, f"LV = {int(row.LV)}", ha="center", transform=ax.get_xaxis_transform(), fontsize=10)
        ax.set_xticks(pos, PRETS); ax.set_ylim(0, maximum*1.23); ax.set_ylabel(f"Error ({UNIT})")
        ax.legend(frameon=False, loc="upper right", fontsize=10); style(ax)
        fig.subplots_adjust(left=.10, right=.98, top=.89, bottom=.18)
        self.save(fig, "Figure_4", "Figure 4",
            CAPTIONS["Figure_4"])

    def selector_performance(self):
        fig, axs = plt.subplots(1, 2, figsize=(9.2, 4.9), gridspec_kw={"width_ratios": [1.35, 1]})
        positions = np.arange(len(METHODS)); ax = axs[0]
        vals = self.perf.RMSEP.to_numpy()
        for j, method in enumerate(METHODS):
            color = METHOD_COLORS[method]
            ax.scatter(vals[j], j+.10, c=color, s=38, zorder=3)
            ax.scatter(self.perf.iloc[j].RMSECV, j-.10, edgecolors=color, marker="s", facecolors="none", s=36, zorder=3)
        ax.scatter(self.best.RMSECV, METHODS.index(self.best["method"])-.10, c=GREEN, marker="*", s=105, zorder=4)
        ax.set_yticks(positions, [DISPLAY[m] for m in METHODS]); ax.invert_yaxis()
        ax.set_ylim(len(METHODS)-.5, -.85)
        ax.set_xlabel(f"Error ({UNIT})"); panel(ax, "a", "Calibration tuning and held-out errors"); style(ax)
        ax.scatter([], [], marker="s", facecolors="none", edgecolors=BLUE, label="Tuning RMSECV")
        ax.scatter([], [], c=BLUE, label="Prediction RMSEP")
        handles, legend_labels = ax.get_legend_handles_labels()
        ax = axs[1]; counts = self.perf.variables.to_numpy()
        ax.barh(positions, counts, color=[METHOD_COLORS[m] for m in METHODS], alpha=.85,
                edgecolor="black", linewidth=.5)
        ax.set_yticks(positions, [DISPLAY[m] for m in METHODS]); ax.invert_yaxis()
        ax.set_ylim(len(METHODS)-.5, -.85)
        for j, count in enumerate(counts): ax.text(count+max(counts)*.025, j, str(int(count)), va="center", fontsize=10.5)
        ax.set_xlim(0, max(counts)*1.18); ax.set_xlabel("Final selected variable count")
        panel(ax, "b", "Model sparsity"); style(ax)
        fig.legend(handles, legend_labels, frameon=False, loc="upper center",
                   bbox_to_anchor=(.54, .995), ncol=2, fontsize=10)
        fig.subplots_adjust(left=.16, right=.98, top=.82, bottom=.13, wspace=.62)
        self.save(fig, "Figure_5", "Figure 5",
            CAPTIONS["Figure_5"])

    def observed_predicted(self):
        fig, axs = plt.subplots(2, 3, figsize=(9.5, 6.5)); methods = ["Full", "MC-UVE", "BSRS"]
        values = self.pred[self.pred.method.isin(methods) & self.pred["set"].isin(["Calibration", "Prediction"])]
        minimum = min(values.reference.min(), values.predicted.min()); maximum = max(values.reference.max(), values.predicted.max())
        margin = (maximum-minimum)*.06; lim = [minimum-margin, maximum+margin]
        descriptive_fits = []
        for r, role in enumerate(["Calibration", "Prediction"]):
            for c, method in enumerate(methods):
                ax = axs[r, c]; row = self.perf[self.perf.method == method].iloc[0]
                table = self.pred[(self.pred.method == method) & (self.pred["set"] == role)]
                ax.scatter(table.reference, table.predicted, s=20, edgecolors=BLUE,
                           facecolors="none", linewidths=.9, label="Samples")
                # Display-only OLS through already saved points; never changes PLS models or predictions.
                slope, intercept = np.polyfit(table.reference.to_numpy(), table.predicted.to_numpy(), 1)
                line_x = np.array([table.reference.min(), table.reference.max()])
                ax.plot(line_x, slope*line_x+intercept, color=RED, lw=.85, label="Fitted line")
                ax.plot(lim, lim, "--", color="black", lw=.55, label="Identity")
                ax.set_xlim(lim); ax.set_ylim(lim); ax.set_aspect("equal", adjustable="box")
                if r == 1: ax.set_xlabel(f"Reference ({UNIT})", fontsize=16)
                if c == 0: ax.set_ylabel(f"Predicted ({UNIT})", fontsize=16)
                letter = "abcdef"[r*3+c]
                measure = (f"R²$_c$ = {row.R2c:.3f}\nRMSEC = {row.RMSEC:.2f}" if r == 0 else
                           f"R²$_p$ = {row.R2p:.3f}\nRMSEP = {row.RMSEP:.2f}")
                ax.text(.06, .965, f"({letter}) {measure}", transform=ax.transAxes,
                        va="top", fontsize=14, linespacing=1.1)
                style(ax)
                ax.tick_params(axis="both", which="major", labelsize=14)
                if r == 0: ax.set_title(DISPLAY[method], fontsize=14, pad=7)
                descriptive_fits.append({"method": method, "set": role,
                    "slope": float(slope), "intercept": float(intercept),
                    "purpose": "display only; fit of saved predictions against reference, not a calibration model"})
        axs[1, 2].legend(frameon=False, loc="lower right", fontsize=13)
        (OUT / "display_only_regression_lines.json").write_text(json.dumps(descriptive_fits, indent=2), encoding="utf-8")
        fig.subplots_adjust(left=.095, right=.985, top=.94, bottom=.12, wspace=.30, hspace=.30)
        self.save(fig, "Figure_6", "Figure 6",
            CAPTIONS["Figure_6"])

    def selected_wavelengths(self):
        fig, ax = plt.subplots(figsize=(9, 4.8)); mean = self.x[self.cal].mean(0)
        normalized = (mean-mean.min()) / max(float(mean.max()-mean.min()), 1e-14)
        ax.plot(self.w, normalized*.75+5, color="black", lw=.9)
        labels = []
        for position, method in enumerate(METHODS[1:]):
            record = self.details[method]; selected = np.asarray(record["selected_wavelengths_nm"])
            position = 4-position
            ax.vlines(selected, position-.15, position+.15, color=METHOD_COLORS[method], lw=1.0)
            labels.append(f"{DISPLAY[method]} ({len(selected)})")
        ax.set_yticks([5.4]+list(range(4, -1, -1)), ["Calibration mean"]+labels)
        ax.set_ylim(-.5, 6.1); ax.set_xlabel("Wavelength (nm)"); ax.margins(x=.01)
        style(ax)
        fig.subplots_adjust(left=.22, right=.98, top=.89, bottom=.13)
        self.save(fig, "Figure_7", "Figure 7",
            CAPTIONS["Figure_7"])

    def preprocessing_spectra(self):
        fig, axs = plt.subplots(3, 2, figsize=(9, 7.1)); grid = np.linspace(self.w.min(), self.w.max(), len(self.w))
        labels = {"Raw": "Recorded response (A.U.)", "MSC": "MSC response (A.U.)", "SNV": "SNV response (dimensionless)",
                  "CWT": "CWT coefficients (A.U.)", "D1": r"First derivative (A.U. nm$^{-1}$)", "D2": r"Second derivative (A.U. nm$^{-2}$)"}
        for letter, treatment, ax in zip("abcdef", PRETS, axs.flat):
            transformed, _ = pret_pair(self.x[self.cal], self.x[self.test], self.w, treatment)
            axis = self.w if treatment in ["Raw", "MSC", "SNV"] else grid
            for row in transformed: ax.plot(axis, row, c=BLUE, alpha=.3, lw=.5)
            ax.plot(axis, transformed.mean(0), c="black", lw=1.0, label="Calibration mean")
            panel(ax, letter, treatment); style(ax); ax.set_xlabel("Wavelength (nm)")
            ax.set_ylabel(labels[treatment], fontsize=11.5); ax.margins(x=.01)
            ax.ticklabel_format(axis="y", style="sci", scilimits=(-3, 3))
        axs[0, 0].legend(frameon=False, fontsize=9, loc="lower right")
        fig.subplots_adjust(left=.095, right=.98, top=.95, bottom=.065, hspace=.50, wspace=.32)
        self.save(fig, "Figure_S1", "Figure S1",
            CAPTIONS["Figure_S1"])

    def residuals(self):
        method = self.best["method"]
        table = self.pred[(self.pred.method == method) & (self.pred["set"] == "Prediction")]
        errors = table.error.to_numpy(); bias = errors.mean(); sd = errors.std(ddof=1)
        fig, axs = plt.subplots(1, 2, figsize=(9, 4.3)); ax = axs[0]
        ax.axhline(0, c="black", lw=.8); ax.axhline(bias, c=RED, lw=.9, ls="--")
        ax.scatter(table.reference, errors, edgecolors=BLUE, facecolors="none", marker="o", s=25, linewidths=.8)
        ax.set_xlabel(f"Reference content ({UNIT})"); ax.set_ylabel(f"Prediction − reference ({UNIT})")
        extent = max(float(np.max(abs(errors))), abs(bias), 1e-9)*1.16
        ax.set_ylim(-extent, extent); panel(ax, "a", f"{DISPLAY[method]}"); style(ax)
        ax = axs[1]; ax.hist(errors, bins=7, color=BLUE, alpha=.4, edgecolor="black", linewidth=.5)
        ax.axvline(0, c="black", lw=.8); ax.axvline(bias, c=RED, ls="--", lw=.9)
        ax.text(.04, .87, f"Bias = {bias:+.2f} {UNIT}\nSD = {sd:.2f} {UNIT}",
                transform=ax.transAxes, va="top", fontsize=10, bbox={"facecolor": "white", "edgecolor": "none", "pad": 2})
        ax.set_xlabel(f"Prediction residual ({UNIT})"); ax.set_ylabel("Sample count")
        panel(ax, "b", "Held-out residual distribution"); style(ax)
        fig.subplots_adjust(left=.10, right=.98, top=.86, bottom=.16, wspace=.35)
        self.save(fig, "Figure_S2", "Figure S2",
            CAPTIONS["Figure_S2"])

    def bsrs_diagnostics(self):
        record = self.details["BSRS"]; detail = record["detail"]
        axis = np.asarray(record["selection_grid_nm"]); selected = np.asarray(record["selected_indices_zero_based"], dtype=int)
        scores = np.asarray(record["scores"]); reliability = np.asarray(detail["reliability"])
        sign = np.asarray(detail["sign_consistency"]); frequency = np.asarray(record["fold_selection_frequency"])
        fig, axs = plt.subplots(2, 2, figsize=(9, 6.0))
        for ax, letter, title, values, ylabel, color in [
            (axs[0, 0], "a", "Coefficient reliability", np.log1p(reliability), r"$\log(1+r_j)$", BLUE),
            (axs[0, 1], "b", "Coefficient sign consistency", sign, r"Sign consistency $s_j$", GREEN),
            (axs[1, 0], "c", "BSRS local stability score", scores, r"Local weighted score $\bar{q}_j$", BLUE)]:
            ax.plot(axis, values, c=BLUE, lw=.85); ax.scatter(axis[selected], values[selected], c=RED, s=17, zorder=3)
            ax.set_xlabel("Wavelength (nm)"); ax.set_ylabel(ylabel); panel(ax, letter, title); style(ax); ax.margins(x=.01)
        axs[0, 1].set_ylim(-.03, 1.17)
        ax = axs[1, 1]; ax.vlines(axis, 0, frequency, color=RED, lw=.9)
        ax.set_ylim(-.03, 1.17); ax.set_xlabel("Wavelength (nm)"); ax.set_ylabel("Fivefold selection frequency")
        panel(ax, "d", "Descriptive fold selection consistency"); style(ax); ax.margins(x=.01)
        fig.subplots_adjust(left=.095, right=.98, top=.94, bottom=.095, hspace=.48, wspace=.37)
        self.save(fig, "Figure_S3", "Figure S3",
            CAPTIONS["Figure_S3"])

    def ablations(self):
        variants = ["BSRS-nosign", "BSRS-nosmooth", "BSRS-noredund"]
        base = self.perf[self.perf.method == "BSRS"].iloc[0]
        ab = self.ablation.set_index("variant").loc[variants]
        cv = np.r_[base.RMSECV, ab.RMSECV]; held = np.r_[base.RMSEP, ab.RMSEP]
        fig, ax = plt.subplots(figsize=(8.4, 4.6)); positions = np.arange(4)
        ax.bar(positions-.18, cv, width=.34, color=BLUE, alpha=.82, label="Calibration tuning RMSECV")
        ax.bar(positions+.18, held, width=.34, color=RED, alpha=.8, label="Held-out RMSEP")
        ax.set_xticks(positions, ["BSRS", "No sign\nweighting", "No local\nsmoothing", "No redundancy\npenalty"])
        ax.set_ylim(0, max(float(cv.max()), float(held.max()))*1.23); ax.set_ylabel(f"Error ({UNIT})")
        ax.legend(frameon=False, loc="upper right", fontsize=10); style(ax)
        fig.subplots_adjust(left=.10, right=.98, top=.89, bottom=.18)
        self.save(fig, "Figure_S4", "Figure S4",
            CAPTIONS["Figure_S4"])

    def finish(self, font_paths):
        (OUT / "figure_captions.json").write_text(json.dumps(self.captions, indent=2, ensure_ascii=False), encoding="utf-8")
        (OUT / "Figure_captions.txt").write_text("\n\n".join(row["figure_label"]+". "+row["caption"] for row in self.captions), encoding="utf-8")
        policy = {"partition": "SPXY", "selection_criterion": "minimum calibration tuning RMSECV",
                  "method": str(self.best["method"]), "pretreatment": str(self.best.pretreatment),
                  "RMSECV": float(self.best.RMSECV), "RMSEP": float(self.best.RMSEP),
                  "observed_predicted_models": ["Full", "MC-UVE", "BSRS"],
                  "input_result_sha256": self.hashes}
        (OUT / "figure_selection_policy.json").write_text(json.dumps(policy, indent=2), encoding="utf-8")
        (OUT / "figure_quality_checks.json").write_text(json.dumps({"font_paths": font_paths,
            "number_of_figures": len(self.captions), "files": self.quality}, indent=2), encoding="utf-8")
        print(f"Completed {len(self.captions)} publication figures in {OUT}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font-dir", help="Folder containing licensed Times New Roman font files")
    args = parser.parse_args()
    font_paths = configure_fonts(args.font_dir)
    builder = FigureBuilder()
    for method in [builder.workflow, builder.raw_spectra, builder.sample_split,
                   builder.preprocessing_performance, builder.selector_performance,
                   builder.observed_predicted, builder.selected_wavelengths,
                   builder.preprocessing_spectra, builder.residuals, builder.bsrs_diagnostics,
                   builder.ablations]:
        method()
    builder.finish(font_paths)


if __name__ == "__main__":
    main()
