"""Extract features for every 3 s window of every recording. Young healthy controls are excluded:
they are ~40 years younger than the PD group, so separating them from PD mostly measures age."""
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "NUMBA_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from features import feature_names, load_audio, window_features, windows  # noqa: E402
from manifest import ROOT, build_manifest  # noqa: E402

OUT = ROOT / "data_processed"


def process(row):
    tabs, mels, mfs = [], [], []
    try:
        y = load_audio(row["path"])
        for w in windows(y):
            t, m, f = window_features(w)
            tabs.append(t), mels.append(m), mfs.append(f)
    except Exception as e:
        print("SKIP", row["path"], e, flush=True)
    return row["path"], tabs, mels, mfs


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    df = build_manifest()
    df = df[df.age_group != "young"].reset_index(drop=True)
    rows = df.to_dict("records")
    meta, T, M, F = [], [], [], []
    t0 = time.time()
    with ProcessPoolExecutor(6) as ex:
        for i, (path, tabs, mels, mfs) in enumerate(ex.map(process, rows, chunksize=2)):
            r = rows[i]
            for k in range(len(tabs)):
                meta.append({**{c: r[c] for c in ("speaker", "label", "y", "source", "task")}, "path": path, "win": k})
            T += tabs
            M += mels
            F += mfs
            if i % 50 == 0:
                print(f"{i}/{len(rows)} files, {len(meta)} windows, {time.time() - t0:.0f}s", flush=True)
    pd.DataFrame(meta).to_csv(OUT / "windows_meta.csv", index=False)
    np.save(OUT / "tab.npy", np.array(T, dtype=np.float32))
    np.save(OUT / "mel.npy", np.array(M, dtype=np.float16))
    np.save(OUT / "mfcc.npy", np.array(F, dtype=np.float16))
    pd.Series(feature_names()).to_csv(OUT / "feature_names.csv", index=False, header=False)
    print("done", len(meta), "windows", f"{time.time() - t0:.0f}s", flush=True)
