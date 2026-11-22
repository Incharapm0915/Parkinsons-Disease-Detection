"""External specificity check: LibriSpeech test-clean (40 healthy English speakers, never used in training).
Every speaker is healthy, so any PD prediction is a false alarm."""
import os
import sys
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[_v] = "1"

import joblib  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from features import cmn_mel, cmn_mfcc, load_audio, robust_cols, window_features, windows  # noqa: E402
from train_dl import CNN, LSTM  # noqa: E402
from train_ml import MODELS, RES, ROOT  # noqa: E402

PER_SPEAKER = 6
files = []
for spk in sorted((ROOT / "datasets/librispeech_test_clean/LibriSpeech/test-clean").iterdir()):
    files += sorted(spk.rglob("*.flac"))[:PER_SPEAKER]

rows, T, M, F = [], [], [], []
for f in files:
    for w in windows(load_audio(str(f))):
        t, m, mf = window_features(w)
        T.append(t), M.append(m), F.append(mf)
        rows.append(f.parts[-3])
X, M, F = np.array(T), np.array(M), np.array(F)
speaker = np.array(rows)
print(len(files), "files,", len(X), "windows,", len(set(speaker)), "speakers")

probs = {}
for p in sorted(MODELS.glob("*.joblib")):
    probs[p.stem] = joblib.load(p).predict_proba(X[:, robust_cols()])[:, 1]
with torch.no_grad():
    if (MODELS / "cnn.pt").exists():
        net = CNN(); net.load_state_dict(torch.load(MODELS / "cnn.pt")); net.eval()
        Mn = cmn_mel(M)
        probs["CNN"] = torch.sigmoid(net(torch.tensor(Mn, dtype=torch.float32))).numpy()
    if (MODELS / "lstm.pt").exists():
        net = LSTM(); net.load_state_dict(torch.load(MODELS / "lstm.pt")); net.eval()
        n = np.load(MODELS / "lstm_norm.npz")
        probs["LSTM"] = torch.sigmoid(net(torch.tensor((cmn_mfcc(F) - n["mu"]) / n["sd"], dtype=torch.float32))).numpy()
probs["Ensemble"] = np.mean(list(probs.values()), axis=0)

out = []
for name, p in probs.items():
    spk = pd.Series(p).groupby(speaker).mean()
    out.append(dict(model=name, window_false_alarm=float((p >= .5).mean()), speaker_false_alarm=float((spk >= .5).mean()),
                    mean_score=float(p.mean())))
res = pd.DataFrame(out)
res.to_csv(RES / "external_librispeech.csv", index=False)
print(res.round(3).to_string(index=False))
