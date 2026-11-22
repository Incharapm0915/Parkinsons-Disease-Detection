"""Five classical models (SVM, Random Forest, KNN, LDA, XGBoost) on voice features.

Validation is speaker-independent: StratifiedGroupKFold keeps every speaker's windows in one fold.
Window predictions are averaged per speaker for the speaker-level score (the number to quote).
"""
import json
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from xgboost import XGBClassifier

sys.path.insert(0, str(Path(__file__).parent))
from features import robust_cols  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
PROC, RES, MODELS = ROOT / "data_processed", ROOT / "results", ROOT / "models"
SEED = 42


def make_models():
    pre = lambda: [SimpleImputer(strategy="median"), StandardScaler()]
    return {
        "SVM": make_pipeline(*pre(), SVC(C=3, kernel="rbf", gamma="scale", probability=True, class_weight="balanced", random_state=SEED)),
        "RandomForest": make_pipeline(SimpleImputer(strategy="median"), RandomForestClassifier(n_estimators=400, min_samples_leaf=3, max_features="sqrt", class_weight="balanced", n_jobs=-1, random_state=SEED)),
        "KNN": make_pipeline(*pre(), KNeighborsClassifier(n_neighbors=25, weights="distance")),
        "LDA": make_pipeline(*pre(), LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")),
        "XGBoost": make_pipeline(SimpleImputer(strategy="median"), XGBClassifier(n_estimators=400, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.5, eval_metric="logloss", n_jobs=8, random_state=SEED)),
    }


def score(y, p, thr=0.5):
    pred = (p >= thr).astype(int)
    return dict(acc=accuracy_score(y, pred), bal_acc=balanced_accuracy_score(y, pred), auc=roc_auc_score(y, p) if len(set(y)) > 1 else np.nan,
                f1=f1_score(y, pred), sens=recall_score(y, pred), spec=recall_score(y, pred, pos_label=0))


def aggregate(meta, p, key):
    d = meta.assign(p=p).groupby(key).agg(p=("p", "mean"), y=("y", "first"))
    return d.y.values, d.p.values


def report(meta, oof, name):
    rows = []
    for level, key in (("window", None), ("recording", "path"), ("speaker", "speaker")):
        y, p = (meta.y.values, oof) if key is None else aggregate(meta, oof, key)
        rows.append(dict(model=name, level=level, n=len(y), **score(y, p)))
    return rows


def folds_for(meta, n_splits=5):
    sp = meta.groupby("speaker").agg(y=("y", "first"), source=("source", "first"))
    strat = sp.y.astype(str) + sp.source
    sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    fold = pd.Series(-1, index=meta.index)
    for k, (_, te) in enumerate(sgkf.split(meta, meta.y.astype(str) + meta.source, groups=meta.speaker)):
        fold.iloc[te] = k
    return fold.values


def main():
    RES.mkdir(exist_ok=True), MODELS.mkdir(exist_ok=True)
    meta = pd.read_csv(PROC / "windows_meta.csv")
    cols = robust_cols()
    X = np.load(PROC / "tab.npy")[:, cols]
    y = meta.y.values
    meta["fold"] = folds_for(meta)
    meta[["speaker", "fold"]].drop_duplicates().to_csv(RES / "folds.csv", index=False)
    names = list(make_models()) + ["Ensemble"]
    oof = {n: np.zeros(len(y)) for n in names}
    for k in range(5):
        tr, te = meta.fold.values != k, meta.fold.values == k
        for n, m in make_models().items():
            m.fit(X[tr], y[tr])
            oof[n][te] = m.predict_proba(X[te])[:, 1]
        oof["Ensemble"][te] = np.mean([oof[n][te] for n in names[:-1]], axis=0)
        print("fold", k, "done", flush=True)
    rows = []
    for n in names:
        rows += report(meta, oof[n], n)
    res = pd.DataFrame(rows)
    res.to_csv(RES / "ml_results.csv", index=False)
    pd.DataFrame(oof).assign(speaker=meta.speaker, path=meta.path, y=y).to_csv(RES / "oof_ml.csv", index=False)
    print(res[res.level == "speaker"].round(3).to_string(index=False))
    print(res[res.level == "window"].round(3).to_string(index=False))

    # cross-corpus check: train on one source, test on the other
    cross = []
    for src_tr, src_te in (("italian", "kcl"), ("kcl", "italian")):
        tr, te = (meta.source == src_tr).values, (meta.source == src_te).values
        for n, m in make_models().items():
            m.fit(X[tr], y[tr])
            p = m.predict_proba(X[te])[:, 1]
            ys, ps = aggregate(meta[te], p, "speaker")
            cross.append(dict(train=src_tr, test=src_te, model=n, **score(ys, ps)))
    cross = pd.DataFrame(cross)
    cross.to_csv(RES / "ml_cross_corpus.csv", index=False)
    print(cross.round(3).to_string(index=False))

    # final models on all data for the app
    for n, m in make_models().items():
        m.fit(X, y)
        joblib.dump(m, MODELS / f"{n}.joblib")
    names_ = pd.read_csv(PROC / "feature_names.csv", header=None)[0].values[cols].tolist()
    hc, pd_ = np.nanmean(X[y == 0], axis=0), np.nanmean(X[y == 1], axis=0)
    json.dump({"cols": cols, "features": names_, "hc_mean": hc.tolist(), "pd_mean": pd_.tolist(),
               "std": np.nanstd(X, axis=0).tolist(), "median": np.nanmedian(X, axis=0).tolist()},
              open(MODELS / "features.json", "w"))


if __name__ == "__main__":
    main()
