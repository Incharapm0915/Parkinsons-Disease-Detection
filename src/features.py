"""Audio -> fixed 3 s windows -> hand-crafted voice features, log-mel image and MFCC sequence.

The same code is used for training and for the live microphone app so both see identical inputs.
"""
import warnings

import librosa
import numpy as np
import parselmouth
from parselmouth.praat import call

warnings.filterwarnings("ignore")

SR = 16000
WIN = 3 * SR
HOP = int(1.5 * SR)
N_MELS = 64
N_MFCC = 20
HOP_LEN = 512          # 3 s -> 94 frames
MIN_VOICED = 0.5       # share of 25 ms frames that must be above the silence threshold


def load_audio(path):
    y, _ = librosa.load(path, sr=SR, mono=True)
    return normalise(y)


def normalise(y):
    y = y - np.mean(y)
    peak = np.max(np.abs(y)) + 1e-9
    return (y / peak).astype(np.float32)


def voiced_fraction(w):
    rms = librosa.feature.rms(y=w, frame_length=400, hop_length=160)[0]
    thr = max(0.02, 0.1 * np.max(rms))
    return float(np.mean(rms > thr))


def windows(y):
    """Yield 3 s windows that contain enough speech. Short clips are zero-padded to one window."""
    if len(y) < WIN:
        y = np.pad(y, (0, WIN - len(y)))
    for s in range(0, len(y) - WIN + 1, HOP):
        w = y[s:s + WIN]
        if voiced_fraction(w) >= MIN_VOICED:
            yield w


PRAAT_NAMES = ["f0_mean", "f0_std", "f0_min", "f0_max", "voiced_ratio", "jitter_local", "jitter_rap",
               "jitter_ppq5", "jitter_ddp", "shimmer_local", "shimmer_db", "shimmer_apq3", "shimmer_apq5",
               "shimmer_apq11", "shimmer_dda", "hnr", "f1", "f2", "f3"]


def praat_features(w):
    out = dict.fromkeys(PRAAT_NAMES, np.nan)
    try:
        snd = parselmouth.Sound(w.astype(np.float64), sampling_frequency=SR)
        pitch = snd.to_pitch(pitch_floor=75, pitch_ceiling=500)
        f0 = pitch.selected_array["frequency"]
        v = f0[f0 > 0]
        out["voiced_ratio"] = len(v) / max(len(f0), 1)
        if len(v) > 10:
            out.update(f0_mean=v.mean(), f0_std=v.std(), f0_min=v.min(), f0_max=v.max())
            pp = call(snd, "To PointProcess (periodic, cc)", 75, 500)
            args = (0, 0, 0.0001, 0.02, 1.3)
            out["jitter_local"] = call(pp, "Get jitter (local)", *args)
            out["jitter_rap"] = call(pp, "Get jitter (rap)", *args)
            out["jitter_ppq5"] = call(pp, "Get jitter (ppq5)", *args)
            out["jitter_ddp"] = call(pp, "Get jitter (ddp)", *args)
            sargs = (0, 0, 0.0001, 0.02, 1.3, 1.6)
            out["shimmer_local"] = call([snd, pp], "Get shimmer (local)", *sargs)
            out["shimmer_db"] = call([snd, pp], "Get shimmer (local_dB)", *sargs)
            out["shimmer_apq3"] = call([snd, pp], "Get shimmer (apq3)", *sargs)
            out["shimmer_apq5"] = call([snd, pp], "Get shimmer (apq5)", *sargs)
            out["shimmer_apq11"] = call([snd, pp], "Get shimmer (apq11)", *sargs)
            out["shimmer_dda"] = call([snd, pp], "Get shimmer (dda)", *sargs)
            hnr = call(snd.to_harmonicity_cc(), "Get mean", 0, 0)
            out["hnr"] = hnr
            formant = snd.to_formant_burg(max_number_of_formants=5, maximum_formant=5500)
            for i in (1, 2, 3):
                out[f"f{i}"] = call(formant, "Get mean", i, 0, 0, "hertz")
    except Exception:
        pass
    return np.array([out[k] for k in PRAAT_NAMES], dtype=np.float64)


def mfcc_seq(w):
    m = librosa.feature.mfcc(y=w, sr=SR, n_mfcc=N_MFCC, hop_length=HOP_LEN, n_fft=1024)
    d = librosa.feature.delta(m)
    return np.vstack([m, d]).astype(np.float32)        # (40, 94)


def logmel(w):
    s = librosa.feature.melspectrogram(y=w, sr=SR, n_fft=1024, hop_length=HOP_LEN, n_mels=N_MELS, fmax=8000)
    return librosa.power_to_db(s, ref=np.max).astype(np.float32)   # (64, 94)


def spectral_features(w, mf):
    cent = librosa.feature.spectral_centroid(y=w, sr=SR, hop_length=HOP_LEN)[0]
    bw = librosa.feature.spectral_bandwidth(y=w, sr=SR, hop_length=HOP_LEN)[0]
    roll = librosa.feature.spectral_rolloff(y=w, sr=SR, hop_length=HOP_LEN)[0]
    flat = librosa.feature.spectral_flatness(y=w, hop_length=HOP_LEN)[0]
    zcr = librosa.feature.zero_crossing_rate(w, hop_length=HOP_LEN)[0]
    rms = librosa.feature.rms(y=w, hop_length=HOP_LEN)[0]
    contrast = librosa.feature.spectral_contrast(y=w, sr=SR, hop_length=HOP_LEN)
    stats = lambda a: np.hstack([a.mean(axis=-1), a.std(axis=-1)])
    return np.hstack([stats(mf), stats(np.vstack([cent, bw, roll, flat, zcr, rms])), stats(contrast)])


def feature_names():
    names = []
    for s in ("mean", "std"):
        names += [f"mfcc{i}_{s}" for i in range(N_MFCC)] + [f"dmfcc{i}_{s}" for i in range(N_MFCC)]
    sp = ["centroid", "bandwidth", "rolloff", "flatness", "zcr", "rms"]
    names += [f"{b}_mean" for b in sp] + [f"{b}_std" for b in sp]
    names += [f"contrast{i}_mean" for i in range(7)] + [f"contrast{i}_std" for i in range(7)]
    return PRAAT_NAMES + names


def robust_cols():
    """Columns that survived the cross-corpus / unseen-speaker test (see experiment_robust.py):
    Praat voice-quality measures and the variability (std) statistics. Absolute spectral level
    features (MFCC means etc.) mostly encode the microphone and are dropped."""
    names = feature_names()
    praat = [i for i, n in enumerate(names) if not n.startswith(("mfcc", "dmfcc", "contrast")) and "_mean" not in n and "_std" not in n]
    dyn = [i for i, n in enumerate(names) if n.endswith("_std")]
    return sorted(set(praat) | set(dyn))


def cmn_mel(mel):
    """Remove the fixed per-frequency level (microphone/room response), then scale."""
    x = mel - mel.mean(axis=-1, keepdims=True)
    return x / (x.std(axis=(-2, -1), keepdims=True) + 1e-5)


def cmn_mfcc(mf):
    return mf - mf.mean(axis=-1, keepdims=True)


def window_features(w):
    """Return (tabular vector, log-mel, mfcc sequence) for one 3 s window."""
    mf = mfcc_seq(w)
    tab = np.hstack([praat_features(w), spectral_features(w, mf)])
    return tab.astype(np.float32), logmel(w), mf
