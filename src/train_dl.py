"""CNN (log-mel spectrogram) and BiLSTM (MFCC sequence) classifiers, speaker-independent 5-fold CV.

usage: python train_dl.py cnn|lstm
Uses the same speaker->fold map as train_ml.py. Early stopping is decided on held-out *training*
speakers, never on the test fold.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.model_selection import StratifiedGroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from train_ml import PROC, RES, MODELS, aggregate, report  # noqa: E402
from features import cmn_mel, cmn_mfcc  # noqa: E402

torch.set_num_threads(10)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
EPOCHS, BATCH, SEED = 30, 64, 42


class CNN(nn.Module):
    def __init__(self):
        super().__init__()
        def block(i, o):
            return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(), nn.MaxPool2d(2))
        self.f = nn.Sequential(block(1, 16), block(16, 32), block(32, 64), block(64, 64), nn.AdaptiveAvgPool2d(1), nn.Flatten())
        self.head = nn.Sequential(nn.Dropout(0.4), nn.Linear(64, 1))

    def forward(self, x):                      # x: (B, 64, 94)
        return self.head(self.f(x.unsqueeze(1))).squeeze(1)


class LSTM(nn.Module):
    def __init__(self, n_in=40):
        super().__init__()
        self.rnn = nn.LSTM(n_in, 64, num_layers=2, batch_first=True, bidirectional=True, dropout=0.3)
        self.head = nn.Sequential(nn.Dropout(0.4), nn.Linear(256, 1))

    def forward(self, x):                      # x: (B, 40, 94) -> (B, 94, 40)
        o, _ = self.rnn(x.transpose(1, 2))
        return self.head(torch.cat([o.mean(1), o.max(1).values], 1)).squeeze(1)


def augment(x, kind):
    x = x.clone()
    B, F, T = x.shape
    x = x + 0.05 * torch.randn_like(x)
    for i in range(B):
        f = np.random.randint(0, max(F // 8, 1)); f0 = np.random.randint(0, F - f)
        t = np.random.randint(0, T // 8); t0 = np.random.randint(0, T - t)
        x[i, f0:f0 + f] = 0
        x[i, :, t0:t0 + t] = 0
    if kind == "cnn":
        x = torch.stack([torch.roll(a, np.random.randint(-10, 10), dims=1) for a in x])
    return x


def predict(model, X, device="cpu"):
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(X), 256):
            out.append(torch.sigmoid(model(X[i:i + 256].to(DEVICE))).cpu().numpy())
    return np.concatenate(out)


def fit(kind, Xtr, ytr, Xva, yva, epochs=EPOCHS, fixed_epochs=False):
    torch.manual_seed(SEED); np.random.seed(SEED)
    model = (CNN() if kind == "cnn" else LSTM()).to(DEVICE)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-2)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=3e-3, total_steps=epochs * ((len(Xtr) + BATCH - 1) // BATCH))
    pw = torch.tensor((ytr == 0).sum() / max((ytr == 1).sum(), 1), dtype=torch.float32, device=DEVICE)
    lossf = nn.BCEWithLogitsLoss(pos_weight=pw)
    yt = torch.tensor(ytr, dtype=torch.float32, device=DEVICE)
    Xtr = Xtr.to(DEVICE)
    best, best_state, best_ep = 1e9, None, epochs
    for ep in range(epochs):
        model.train()
        perm = torch.randperm(len(Xtr), device=DEVICE)
        for i in range(0, len(perm), BATCH):
            idx = perm[i:i + BATCH]
            opt.zero_grad()
            loss = lossf(model(augment(Xtr[idx], kind)), yt[idx])
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step()
        if Xva is not None:
            p = predict(model, Xva)
            vl = float(-np.mean(yva * np.log(p + 1e-7) + (1 - yva) * np.log(1 - p + 1e-7)))
            if vl < best:
                best, best_ep = vl, ep + 1
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    if best_state is not None and not fixed_epochs:
        model.load_state_dict(best_state)
    return model.to(DEVICE), best_ep


def load(kind):
    X = np.load(PROC / ("mel.npy" if kind == "cnn" else "mfcc.npy")).astype(np.float32)
    return X


def normalise(Xtr, X, kind):
    if kind == "cnn":                          # per-frequency mean removal + scaling, per window
        return cmn_mel(X), None
    X, Xtr = cmn_mfcc(X), cmn_mfcc(Xtr)
    sd = Xtr.std(axis=(0, 2), keepdims=True) + 1e-5
    return X / sd, (np.zeros_like(sd), sd)


def main(kind):
    meta = pd.read_csv(PROC / "windows_meta.csv")
    fold_of = pd.read_csv(RES / "folds.csv").set_index("speaker").fold
    meta["fold"] = meta.speaker.map(fold_of).values
    y = meta.y.values
    X0 = load(kind)
    oof = np.zeros(len(y))
    t0 = time.time()
    eps = []
    for k in range(5):
        tr, te = np.where(meta.fold.values != k)[0], np.where(meta.fold.values == k)[0]
        sp = meta.iloc[tr].groupby("speaker").y.first()
        va_sp = set(next(StratifiedGroupKFold(6, shuffle=True, random_state=SEED).split(sp, sp.values, groups=sp.index))[1])
        va_sp = set(sp.index[list(va_sp)])
        is_va = meta.iloc[tr].speaker.isin(va_sp).values
        tr_fit, tr_val = tr[~is_va], tr[is_va]
        Xn, _ = normalise(X0[tr_fit], X0, kind)
        Xt = torch.tensor(Xn)
        model, ep = fit(kind, Xt[tr_fit], y[tr_fit], Xt[tr_val], y[tr_val].astype(np.float32))
        oof[te] = predict(model, Xt[te])
        eps.append(ep)
        print(f"{kind} fold {k} best_epoch={ep} {time.time() - t0:.0f}s", flush=True)
    res = pd.DataFrame(report(meta, oof, kind.upper()))
    res.to_csv(RES / f"{kind}_results.csv", index=False)
    pd.DataFrame({"p": oof, "speaker": meta.speaker, "path": meta.path, "y": y}).to_csv(RES / f"oof_{kind}.csv", index=False)
    print(res.round(3).to_string(index=False), flush=True)

    # final model on every speaker for the app (fixed epochs = median of the best epochs found in CV)
    Xn, stats = normalise(X0, X0, kind)
    model, _ = fit(kind, torch.tensor(Xn), y, None, None, epochs=int(np.median(eps)), fixed_epochs=True)
    MODELS.mkdir(exist_ok=True)
    torch.save({k: v.cpu() for k, v in model.state_dict().items()}, MODELS / f"{kind}.pt")
    if stats:
        np.savez(MODELS / f"{kind}_norm.npz", mu=stats[0], sd=stats[1])


if __name__ == "__main__":
    main(sys.argv[1])
