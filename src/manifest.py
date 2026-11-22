"""Build a table of every usable recording: path, label, speaker, source dataset, task."""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets"
ITA = DATA / "italian_pvs_audio" / "italian_parkinson"
KCL = DATA / "mdvr_kcl_audio" / "26-29_09_2017_KCL"

ITA_GROUPS = {
    "22 Elderly Healthy Control": ("HC", "elderly"),
    "28 People with Parkinson's disease": ("PD", "elderly"),
    "15 Young Healthy Control": ("HC", "young"),
}
ITA_TASKS = {
    "B": "read_text", "FB": "read_phrases", "PR": "read_phrases", "D": "syllables",
    "VA": "vowel_a", "VE": "vowel_e", "VI": "vowel_i", "VO": "vowel_o", "VU": "vowel_u",
}


def italian_task(stem):
    m = re.match(r"([A-Z]+)\d", stem)
    return ITA_TASKS.get(m.group(1), "other") if m else "other"


def build_manifest():
    rows = []
    for folder, (label, age) in ITA_GROUPS.items():
        for wav in (ITA / folder).rglob("*.wav"):
            speaker = wav.parent.relative_to(ITA / folder).as_posix()
            rows.append(dict(path=str(wav), label=label, speaker=f"it_{label}_{speaker}", source="italian",
                             task=italian_task(wav.stem), age_group=age))
    for wav in KCL.rglob("*.wav"):
        label = "PD" if wav.parent.name == "PD" else "HC"
        task = "read_text" if wav.parent.parent.name == "ReadText" else "dialogue"
        rows.append(dict(path=str(wav), label=label, speaker=f"kcl_{wav.stem.split('_')[0]}", source="kcl",
                         task=task, age_group="elderly"))
    df = pd.DataFrame(rows)
    df["y"] = (df.label == "PD").astype(int)
    return df


if __name__ == "__main__":
    df = build_manifest()
    print(df.groupby(["source", "age_group", "label"]).agg(files=("path", "size"), speakers=("speaker", "nunique")))
    print(df.task.value_counts())
    clash = df.groupby("speaker").label.nunique()
    print("speakers with conflicting labels:", int((clash > 1).sum()))
