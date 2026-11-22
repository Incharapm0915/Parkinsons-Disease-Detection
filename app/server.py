"""Live Parkinson's voice screening server.

Browser sends the latest 3 s of microphone audio (16 kHz float32) to /predict every 1.5 s.
Every model found in ../models is run on the same window; the mean is the screening score.
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import torch
from flask import Flask, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from features import HOP, MIN_VOICED, SR, WIN, cmn_mel, cmn_mfcc, normalise, robust_cols, voiced_fraction, window_features  # noqa: E402
from train_dl import CNN, LSTM  # noqa: E402

MODELS = ROOT / "models"
COLS = robust_cols()
ML_NAMES = ["SVM", "RandomForest", "KNN", "LDA", "XGBoost"]
app = Flask(__name__, static_folder="static")

ml = {n: joblib.load(MODELS / f"{n}.joblib") for n in ML_NAMES if (MODELS / f"{n}.joblib").exists()}
dl = {}
for kind, cls in (("cnn", CNN), ("lstm", LSTM)):
    if (MODELS / f"{kind}.pt").exists():
        net = cls()
        net.load_state_dict(torch.load(MODELS / f"{kind}.pt", map_location="cpu"))
        net.eval()
        dl[kind] = net
lstm_norm = np.load(MODELS / "lstm_norm.npz") if (MODELS / "lstm_norm.npz").exists() else None
stats = json.load(open(MODELS / "features.json")) if (MODELS / "features.json").exists() else None
cfg = json.load(open(MODELS / "config.json")) if (MODELS / "config.json").exists() else {}
use = set(cfg.get("use", [*ml, *[k.upper() for k in dl]]))
print("loaded:", list(ml), list(dl), "using:", sorted(use))


def explain(tab, k=5):
    if not stats:
        return []
    x = tab
    hc, pdm, sd = np.array(stats["hc_mean"]), np.array(stats["pd_mean"]), np.array(stats["std"]) + 1e-9
    push = ((x - hc) / sd) * np.sign(pdm - hc)           # >0: this feature looks more like the PD group
    push = np.nan_to_num(push)
    top = np.argsort(-np.abs(push))[:k]
    return [{"feature": stats["features"][i], "value": float(x[i]), "towards": "PD" if push[i] > 0 else "healthy",
             "strength": float(min(abs(push[i]), 3) / 3)} for i in top]


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/models")
def models():
    return jsonify(sorted(use))


def score_window(w):
    """Run every loaded model on one normalised 3 s window. Returns (probs, ensemble score, robust feature vector)."""
    tab, mel, mf = window_features(w)
    tab = tab[COLS]
    probs = {n: float(m.predict_proba(tab[None])[0, 1]) for n, m in ml.items()}
    with torch.no_grad():
        if "cnn" in dl:
            probs["CNN"] = float(torch.sigmoid(dl["cnn"](torch.tensor(cmn_mel(mel))[None])).item())
        if "lstm" in dl and lstm_norm is not None:
            m = (cmn_mfcc(mf) - lstm_norm["mu"][0]) / lstm_norm["sd"][0]
            probs["LSTM"] = float(torch.sigmoid(dl["lstm"](torch.tensor(m, dtype=torch.float32)[None])).item())
    chosen = [p for n, p in probs.items() if n in use] or list(probs.values())
    return probs, float(np.mean(chosen)), tab


@app.post("/predict")
def predict():
    y = np.frombuffer(request.get_data(), dtype=np.float32)
    if len(y) < SR:
        return jsonify(status="too_short")
    y = y[-WIN:] if len(y) >= WIN else np.pad(y, (0, WIN - len(y)))
    if float(np.max(np.abs(y))) < 0.02:          # near-silent input: normalising would just amplify noise
        return jsonify(status="no_voice", voiced=0.0)
    w = normalise(y)
    vf = voiced_fraction(w)
    if vf < 0.3:
        return jsonify(status="no_voice", voiced=vf)
    probs, score, tab = score_window(w)
    return jsonify(status="ok", score=score, models=probs, used=sorted(use), voiced=vf, features=explain(tab))


MAX_FILE_S = 90


@app.post("/analyze")
def analyze():
    """Whole uploaded recording (16 kHz mono float32). Same windowing as training: normalise the file once,
    then 3 s windows every 1.5 s, keeping only windows with enough speech."""
    y = np.frombuffer(request.get_data(), dtype=np.float32)
    if len(y) < SR:
        return jsonify(status="too_short")
    y = y[:MAX_FILE_S * SR]
    if float(np.max(np.abs(y))) < 0.02:
        return jsonify(status="no_voice")
    y = normalise(y)
    if len(y) < WIN:
        y = np.pad(y, (0, WIN - len(y)))
    wins, tabs = [], []
    for s in range(0, len(y) - WIN + 1, HOP):
        w = y[s:s + WIN]
        if voiced_fraction(w) < MIN_VOICED:
            continue
        probs, score, tab = score_window(w)
        wins.append(dict(t=s / SR, score=score, models=probs))
        tabs.append(tab)
    if not wins:
        return jsonify(status="no_voice")
    names = wins[0]["models"].keys()
    return jsonify(status="ok", windows=wins, score=float(np.mean([x["score"] for x in wins])),
                   models={n: float(np.mean([x["models"][n] for x in wins])) for n in names}, used=sorted(use),
                   features=explain(np.mean(tabs, axis=0)), duration=len(y) / SR)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, threaded=True)
