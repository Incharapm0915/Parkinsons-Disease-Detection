#!/bin/bash
# Full pipeline after extraction: ML (5 models) -> CNN -> LSTM -> external false-alarm check. GPU venv used for torch.
cd "$(dirname "$0")"
PY=.venv_gpu/Scripts/python.exe
$PY src/train_ml.py && $PY src/train_dl.py cnn && $PY src/train_dl.py lstm && $PY src/eval_external.py
