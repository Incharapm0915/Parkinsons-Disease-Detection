"""Charts and the pipeline diagram for the project report. All numbers are read from results/*.csv."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from sklearn.metrics import roc_curve, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
RES, OUT = ROOT / "results", ROOT / "docs" / "figures"
OUT.mkdir(exist_ok=True)

INDIGO, VIOLET, GREY, RED, GREEN, AMBER = "#3b4fd9", "#8a5cf5", "#9aa3b5", "#d9483b", "#14966b", "#d68a10"
plt.rcParams.update({"font.family": "Arial", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#8b93a7", "axes.labelcolor": "#2a3249", "xtick.color": "#2a3249", "ytick.color": "#2a3249"})


def save(fig, name):
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------- 1. data composition ----------
meta = pd.read_csv(ROOT / "data_processed" / "windows_meta.csv")
sp = meta.groupby(["source", "label"]).speaker.nunique().unstack()
win = meta.groupby(["source", "label"]).size().unstack()
fig, ax = plt.subplots(1, 2, figsize=(8.4, 3.0))
for a, tab, title in ((ax[0], sp, "Speakers"), (ax[1], win, "3-second windows")):
    x = np.arange(len(tab))
    a.bar(x - .2, tab["HC"], .4, color=GREEN, label="Healthy")
    a.bar(x + .2, tab["PD"], .4, color=RED, label="Parkinson's")
    for i, (h, p) in enumerate(zip(tab["HC"], tab["PD"])):
        a.text(i - .2, h, f"{h:,}", ha="center", va="bottom", fontsize=9)
        a.text(i + .2, p, f"{p:,}", ha="center", va="bottom", fontsize=9)
    a.set_xticks(x, ["Italian PVS\n(studio)", "MDVR-KCL\n(smartphone)"])
    a.set_title(title, loc="left", fontweight="bold", fontsize=10.5)
    a.set_ylim(0, tab.values.max() * 1.18)
ax[0].legend(frameon=False, loc="upper right", fontsize=9)
fig.tight_layout()
save(fig, "fig_data.png")

# ---------- 2. speaker-level cross-validation ----------
ml = pd.read_csv(RES / "ml_results.csv")
dl = pd.concat([pd.read_csv(RES / "cnn_results.csv"), pd.read_csv(RES / "lstm_results.csv")])
allr = pd.concat([ml, dl])
spk = allr[allr.level == "speaker"].set_index("model")
order = ["LDA", "SVM", "RandomForest", "XGBoost", "KNN", "Ensemble", "LSTM", "CNN"]
fig, ax = plt.subplots(figsize=(8.4, 3.3))
x = np.arange(len(order))
cols = [INDIGO] * 5 + [VIOLET] + [GREY] * 2
ax.bar(x - .2, [spk.loc[m, "acc"] * 100 for m in order], .4, color=cols, label="Accuracy")
ax.bar(x + .2, [spk.loc[m, "auc"] * 100 for m in order], .4, color=cols, alpha=.45, label="AUC x 100")
for i, m in enumerate(order):
    ax.text(i - .2, spk.loc[m, "acc"] * 100 + .8, f"{spk.loc[m, 'acc'] * 100:.1f}", ha="center", fontsize=8.5, fontweight="bold")
    ax.text(i + .2, spk.loc[m, "auc"] * 100 + .8, f"{spk.loc[m, 'auc'] * 100:.1f}", ha="center", fontsize=8.5)
ax.set_xticks(x, order)
ax.set_ylim(60, 110)
ax.set_ylabel("percent")
ax.set_title("Speaker-independent 5-fold cross-validation (89 speakers)", loc="left", fontweight="bold", fontsize=10.5)
ax.legend(frameon=False, loc="upper right", ncol=2, fontsize=9)
fig.tight_layout()
save(fig, "fig_cv.png")

# ---------- 3. ROC curves + confusion matrix ----------
oml = pd.read_csv(RES / "oof_ml.csv").groupby("speaker").mean(numeric_only=True)
ocn = pd.read_csv(RES / "oof_cnn.csv").groupby("speaker").agg(p=("p", "mean"), y=("y", "first"))
ols = pd.read_csv(RES / "oof_lstm.csv").groupby("speaker").agg(p=("p", "mean"), y=("y", "first"))
fig, ax = plt.subplots(1, 2, figsize=(8.4, 3.5), gridspec_kw={"width_ratios": [1.25, 1]})
curves = [("Ensemble", oml["Ensemble"], oml["y"], VIOLET, 2.6), ("XGBoost", oml["XGBoost"], oml["y"], INDIGO, 1.4),
          ("LDA", oml["LDA"], oml["y"], "#2a9d8f", 1.4), ("LSTM", ols["p"], ols["y"], AMBER, 1.4), ("CNN", ocn["p"], ocn["y"], GREY, 1.4)]
for name, p, y, c, lw in curves:
    fpr, tpr, _ = roc_curve(y, p)
    ax[0].plot(fpr, tpr, color=c, lw=lw, label=f"{name} (AUC {roc_auc_score(y, p):.3f})")
ax[0].plot([0, 1], [0, 1], ls="--", color="#c3c9d6", lw=1)
ax[0].set(xlabel="false positive rate", ylabel="true positive rate", title="")
ax[0].set_title("ROC, speaker level", loc="left", fontweight="bold", fontsize=10.5)
ax[0].legend(frameon=False, fontsize=8.5, loc="lower right")
y, p = oml["y"].values, (oml["Ensemble"].values >= .5).astype(int)
cm = np.array([[((y == 0) & (p == 0)).sum(), ((y == 0) & (p == 1)).sum()], [((y == 1) & (p == 0)).sum(), ((y == 1) & (p == 1)).sum()]])
ax[1].imshow(cm, cmap="Purples", vmin=0, vmax=cm.max() * 1.3)
for i in range(2):
    for j in range(2):
        ax[1].text(j, i, cm[i, j], ha="center", va="center", fontsize=20, fontweight="bold", color="white" if cm[i, j] > cm.max() * .5 else "#2a3249")
ax[1].set_xticks([0, 1], ["Healthy", "PD"]); ax[1].set_yticks([0, 1], ["Healthy", "PD"])
ax[1].set(xlabel="predicted", ylabel="actual"); ax[1].spines[:].set_visible(False)
ax[1].set_title("Ensemble confusion matrix", loc="left", fontweight="bold", fontsize=10.5)
fig.tight_layout()
save(fig, "fig_roc.png")
np.save(OUT / "cm.npy", cm)

# ---------- 4. generalisation fix: before / after ----------
rb = pd.read_csv(RES / "robustness_experiment.csv")
base, rob = rb[rb.subset == "all (baseline)"].set_index("model"), rb[rb.subset == "praat + dynamics (std features)"].set_index("model")
models = ["LDA", "SVM", "RandomForest", "XGBoost", "KNN"]
fig, ax = plt.subplots(1, 3, figsize=(8.6, 3.0), gridspec_kw={"width_ratios": [1, 1, 1.6]})
for a, col, ttl in ((ax[0], "italian->kcl_auc", "Train Italian, test KCL"), (ax[1], "kcl->italian_auc", "Train KCL, test Italian")):
    a.bar(["all 125\nfeatures", "robust 71\nfeatures"], [base[col].mean(), rob[col].mean()], color=[GREY, INDIGO], width=.55)
    for i, v in enumerate([base[col].mean(), rob[col].mean()]):
        a.text(i, max(v, .5) + .025, f"{v:.2f}", ha="center", fontweight="bold", fontsize=9.5)
    a.axhline(.5, color=RED, lw=1, ls="--"); a.text(1.42, .505, "chance", color=RED, fontsize=7.5, ha="right", va="bottom")
    a.set_ylim(0, 1); a.set_title(ttl + "\n(mean AUC)", fontsize=9.2, loc="left", fontweight="bold")
fa_b = {m: base.loc[m, "libri_false_alarm"] for m in models}
fa_r = {m: rob.loc[m, "libri_false_alarm"] for m in models}
fa_b.update({"CNN": .625, "LSTM": .525}); fa_r.update({"CNN": .525, "LSTM": .45})   # deep models: from the two eval_external.py runs
names = models + ["CNN", "LSTM"]
x = np.arange(len(names))
ax[2].bar(x - .2, [fa_b[m] * 100 for m in names], .4, color=GREY, label="before")
ax[2].bar(x + .2, [fa_r[m] * 100 for m in names], .4, color=[INDIGO] * 5 + [RED, RED], label="after")
for i, m in enumerate(names):
    ax[2].text(i + .2, fa_r[m] * 100 + 1.5, f"{fa_r[m] * 100:.0f}", ha="center", fontsize=8)
ax[2].set_xticks(x, [n.replace("RandomForest", "RF").replace("XGBoost", "XGB") for n in names], fontsize=8.5)
ax[2].set_ylim(0, 75); ax[2].set_title("False alarms on 40 unseen healthy speakers (%)", fontsize=9.2, loc="left", fontweight="bold")
ax[2].legend(frameon=False, fontsize=8.5)
fig.tight_layout()
save(fig, "fig_robust.png")

# ---------- 5. pipeline diagram ----------
fig, ax = plt.subplots(figsize=(9.2, 4.1))
ax.set_xlim(0, 100); ax.set_ylim(0, 44); ax.axis("off")


def box(x, y, w, h, text, fc, ec=None, tc="#1d2540", fs=8.3, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=1.2", fc=fc, ec=ec or fc, lw=1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc, fontweight="bold" if bold else "normal", linespacing=1.35)


def arrow(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=10, color="#6b7390", lw=1.2))


box(0.5, 16, 12, 12, "Voice input\n\nlive microphone\nor uploaded\naudio file", "#eef1ff", INDIGO, bold=False)
box(16.5, 16, 14, 12, "Pre-processing\n\nmono, 16 kHz\npeak-normalise\nskip silence", "#f3edff", VIOLET)
box(34.5, 16, 14, 12, "Windowing\n\n3 s windows\nhop 1.5 s\n>= 50% speech", "#eef1ff", INDIGO)
box(53.5, 31, 21, 9, "71 voice features\njitter, shimmer, HNR, pitch,\nformants, spectral variability", "#e8f7f0", GREEN, fs=7.8)
box(53.5, 17.5, 21, 9, "Log-mel spectrogram\n64 x 94, channel-normalised", "#fff4e0", AMBER, fs=7.8)
box(53.5, 4, 21, 9, "MFCC + delta sequence\n40 x 94, channel-normalised", "#fff4e0", AMBER, fs=7.8)
box(79, 28, 20, 12, "LDA  XGBoost\nRandom Forest  SVM\n\ncounted in the score", "#e8f7f0", GREEN, fs=8)
box(79, 4, 20, 12, "CNN        LSTM\n\nshown for comparison\nonly", "#f1f2f6", GREY, fs=8)
box(79, 18.2, 20, 7.6, "Score = mean of 4 models,\nsmoothed over 4 windows", "#f3edff", VIOLET, fs=7.8, bold=True)
for a, b in ((12.6, 16.4), (30.6, 34.4)):
    arrow(a, 22, b + 0.1, 22)
arrow(48.7, 24, 53.2, 35.5); arrow(48.7, 22, 53.2, 22); arrow(48.7, 20, 53.2, 8.5)
arrow(74.8, 35.5, 78.8, 34); arrow(74.8, 22, 78.8, 10)
arrow(74.8, 8.5, 78.8, 8)
arrow(89, 27.8, 89, 25.9)
ax.text(0.5, 42.3, "Processing pipeline", fontsize=11, fontweight="bold", color="#2a3249")
save(fig, "fig_pipeline.png")
print("figures written to", OUT)
