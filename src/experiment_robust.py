"""Which feature subsets survive a change of microphone/corpus?
For each subset: speaker-independent CV inside the pooled data, train-on-A/test-on-B in both directions,
and false-alarm rate on 40 unseen healthy LibriSpeech speakers."""
import os
import sys
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from features import feature_names, load_audio, window_features, windows  # noqa: E402
from train_ml import PROC, RES, ROOT, SEED, aggregate, make_models, score  # noqa: E402

LIBRI = PROC / "libri_tab.npy"
if not LIBRI.exists():
    T, spk = [], []
    base = ROOT / "datasets/librispeech_test_clean/LibriSpeech/test-clean"
    for s in sorted(base.iterdir()):
        for f in sorted(s.rglob("*.flac"))[:6]:
            for w in windows(load_audio(str(f))):
                T.append(window_features(w)[0]); spk.append(s.name)
    np.save(LIBRI, np.array(T)); pd.Series(spk).to_csv(PROC / "libri_spk.csv", index=False, header=False)
XL = np.load(LIBRI)
spk_l = pd.read_csv(PROC / "libri_spk.csv", header=None)[0].values

meta = pd.read_csv(PROC / "windows_meta.csv")
X = np.load(PROC / "tab.npy")
names = np.array(feature_names())
fold = meta.speaker.map(pd.read_csv(RES / "folds.csv").set_index("speaker").fold).values
y = meta.y.values

praat = np.array([i for i, n in enumerate(names) if not n.startswith(("mfcc", "dmfcc")) and "_mean" not in n and "_std" not in n and not n.startswith("contrast")])
dyn = np.array([i for i, n in enumerate(names) if n.endswith("_std")])
subsets = {
    "all (baseline)": np.arange(len(names)),
    "praat voice-quality only": praat,
    "praat + dynamics (std features)": np.union1d(praat, dyn),
}
rows = []
for sname, cols in subsets.items():
    Xs, XLs = X[:, cols], XL[:, cols]
    oof = {n: np.zeros(len(y)) for n in make_models()}
    for k in range(5):
        tr, te = fold != k, fold == k
        for n, m in make_models().items():
            m.fit(Xs[tr], y[tr]); oof[n][te] = m.predict_proba(Xs[te])[:, 1]
    for n, m in make_models().items():
        ys, ps = aggregate(meta, oof[n], "speaker")
        r = dict(subset=sname, model=n, n_feat=len(cols), cv_bal_acc=score(ys, ps)["bal_acc"], cv_auc=score(ys, ps)["auc"])
        for a, b in (("italian", "kcl"), ("kcl", "italian")):
            tr, te = (meta.source == a).values, (meta.source == b).values
            m.fit(Xs[tr], y[tr]); p = m.predict_proba(Xs[te])[:, 1]
            ys2, ps2 = aggregate(meta[te], p, "speaker")
            r[f"{a}->{b}_auc"] = score(ys2, ps2)["auc"]
        m.fit(Xs, y)
        pl = pd.Series(m.predict_proba(XLs)[:, 1]).groupby(spk_l).mean()
        r["libri_false_alarm"] = float((pl >= .5).mean())
        rows.append(r); print(r, flush=True)
res = pd.DataFrame(rows)
res.to_csv(RES / "robustness_experiment.csv", index=False)
print(res.groupby("subset")[[c for c in res.columns if c not in ("subset", "model", "n_feat")]].mean().round(3).to_string())
