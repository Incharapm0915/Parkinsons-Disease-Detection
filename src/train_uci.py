"""Same five models on the UCI 470 tabular set (756 recordings, 252 subjects, 750+ features).
Subject-independent: all 3 recordings of a person stay in one fold."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from train_ml import RES, ROOT, SEED, make_models, score  # noqa: E402

RES.mkdir(exist_ok=True)
df = pd.read_csv(ROOT / "datasets/uci_470_pd_classification/pd_speech_features.csv", header=1)
y, groups = df["class"].values, df["id"].values
X = df.drop(columns=["id", "class"]).values.astype(np.float32)
names = list(make_models())
oof = {n: np.zeros(len(y)) for n in names + ["Ensemble"]}
for tr, te in StratifiedGroupKFold(5, shuffle=True, random_state=SEED).split(X, y, groups):
    for n, m in make_models().items():
        m.fit(X[tr], y[tr])
        oof[n][te] = m.predict_proba(X[te])[:, 1]
    oof["Ensemble"][te] = np.mean([oof[n][te] for n in names], axis=0)
rows = []
for n, p in oof.items():
    d = pd.DataFrame({"g": groups, "y": y, "p": p}).groupby("g").agg(y=("y", "first"), p=("p", "mean"))
    rows.append(dict(model=n, level="subject", **score(d.y.values, d.p.values)))
    rows.append(dict(model=n, level="recording", **score(y, p)))
res = pd.DataFrame(rows)
res.to_csv(RES / "uci470_results.csv", index=False)
print(res.round(3).to_string(index=False))
