"""Builds docs/VoiceScreen_Complete_Code.pdf: project structure, explanation and the full source of every file.
Source files are read from disk at build time, so the listings can never drift from the code."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Flowable, Frame, Image, PageBreak, PageTemplate, Paragraph, Preformatted, Spacer, Table, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "VoiceScreen_Complete_Code.pdf"
FIG = ROOT / "docs" / "figures"
W = "C:/Windows/Fonts/"
for n, f in (("Arial", "arial.ttf"), ("Arial-Bold", "arialbd.ttf"), ("Arial-Italic", "ariali.ttf"), ("Arial-BoldItalic", "arialbi.ttf"), ("Mono", "consola.ttf"), ("Mono-Bold", "consolab.ttf")):
    pdfmetrics.registerFont(TTFont(n, W + f))
pdfmetrics.registerFont(TTFont("Indic", W + "Nirmala.ttc", subfontIndex=0))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic", boldItalic="Arial-BoldItalic")
pdfmetrics.registerFontFamily("Mono", normal="Mono", bold="Mono-Bold", italic="Mono", boldItalic="Mono-Bold")
MONO_CMAP = pdfmetrics.getFont("Mono").face.charToGlyph

INDIGO, VIOLET = colors.HexColor("#3b4fd9"), colors.HexColor("#8a5cf5")
INK, MUTE, LINE, TINT = colors.HexColor("#1d2540"), colors.HexColor("#5b6882"), colors.HexColor("#d9deea"), colors.HexColor("#f2f4fd")
CODEBG, GUTTER = colors.HexColor("#f7f8fb"), colors.HexColor("#a3abbd")

S = {
    "body": ParagraphStyle("body", fontName="Arial", fontSize=9.6, leading=14.2, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=5),
    "h1": ParagraphStyle("h1", fontName="Arial-Bold", fontSize=17, leading=21, textColor=INDIGO, spaceBefore=2, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName="Arial-Bold", fontSize=11.6, leading=15, textColor=INK, spaceBefore=9, spaceAfter=4),
    "cell": ParagraphStyle("cell", fontName="Arial", fontSize=8.5, leading=11, textColor=INK),
    "cellm": ParagraphStyle("cellm", fontName="Mono", fontSize=7.8, leading=10.4, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Arial-Bold", fontSize=8.5, leading=11, textColor=colors.white),
    "bul": ParagraphStyle("bul", fontName="Arial", fontSize=9.4, leading=13.4, textColor=INK, leftIndent=14, firstLineIndent=-10, spaceAfter=2.5),
    "tree": ParagraphStyle("tree", fontName="Mono", fontSize=8.4, leading=11.4, textColor=INK),
}


def P(t, s="body"):
    return Paragraph(t, S[s])


def H1(t):
    return Paragraph(t, S["h1"])


def H2(t):
    return Paragraph(t, S["h2"])


def bullets(items):
    return [Paragraph("•&nbsp;&nbsp;" + i, S["bul"]) for i in items]


def table(rows, widths, mono_first=False):
    data = [[Paragraph(c, S["cellb"]) for c in rows[0]]]
    for r in rows[1:]:
        data.append([Paragraph(c, S["cellm"] if (mono_first and j == 0) else S["cell"]) for j, c in enumerate(r)])
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), INDIGO), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, TINT]), ("LINEBELOW", (0, 0), (-1, -1), .4, LINE),
                           ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5)]))
    return t


# ---------------------------------------------------------------- code listing flowable
CODE_PT, CODE_LEAD, GUT_W, MAXW = 7.3, 9.1, 26, A4[0] - 3.4 * cm - 26 - 8


def runs(line):
    """Split a line into (font, text) runs: Consolas where it has the glyph, Nirmala UI (Devanagari/Kannada) otherwise."""
    out = []
    for ch in line:
        f = "Mono" if ord(ch) in MONO_CMAP or ch == " " else "Indic"
        if out and out[-1][0] == f:
            out[-1][1] += ch
        else:
            out.append([f, ch])
    return out


def wrap(line):
    """Greedy character wrap to the printable width; continuation rows are indented and flagged."""
    rows, cur, w = [], [], 0.0
    ind = len(line) - len(line.lstrip(" "))
    for ch in line:
        cw = pdfmetrics.stringWidth(ch, "Mono" if (ord(ch) in MONO_CMAP or ch == " ") else "Indic", CODE_PT)
        if w + cw > MAXW - (0 if not rows else 8 * 4.0) and cur:
            rows.append("".join(cur)); cur, w = [" " * (ind + 4)], pdfmetrics.stringWidth(" ", "Mono", CODE_PT) * (ind + 4)
        cur.append(ch); w += cw
    rows.append("".join(cur))
    return rows


class Code(Flowable):
    """A run of pre-wrapped rows [(lineno or None, text)]. Splits between rows so listings flow across pages."""

    def __init__(self, rows):
        super().__init__()
        self.rows = rows

    def wrap(self, aw, ah):
        self.width, self.height = aw, len(self.rows) * CODE_LEAD + 8
        return self.width, self.height

    def split(self, aw, ah):
        n = int((ah - 8) // CODE_LEAD)
        if n >= len(self.rows):
            return [self]
        if n < 6:
            return []
        return [Code(self.rows[:n]), Code(self.rows[n:])]

    def draw(self):
        c, h = self.canv, self.height
        c.setFillColor(CODEBG); c.rect(0, 0, self.width, h, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#e9ecf5")); c.rect(0, 0, GUT_W, h, stroke=0, fill=1)
        y = h - 4 - CODE_LEAD + 2.4
        for no, text in self.rows:
            if no is not None:
                c.setFillColor(GUTTER); c.setFont("Mono", CODE_PT); c.drawRightString(GUT_W - 4, y, str(no))
            x = GUT_W + 5
            for f, t in runs(text):
                c.setFillColor(INK); c.setFont(f, CODE_PT); c.drawString(x, y, t); x += pdfmetrics.stringWidth(t, f, CODE_PT)
            y -= CODE_LEAD


def listing(path):
    text = Path(path).read_text(encoding="utf8").replace("\t", "    ").rstrip("\n")
    rows = []
    for i, line in enumerate(text.split("\n"), 1):
        for k, seg in enumerate(wrap(line)):
            rows.append((i if k == 0 else None, seg))
    return Code(rows), len(text.split("\n"))


# ---------------------------------------------------------------- document
class Doc(BaseDocTemplate):
    def afterFlowable(self, fl):
        if isinstance(fl, Paragraph) and fl.style.name in ("h1",):
            self.notify("TOCEntry", (0, fl.getPlainText(), self.page))


def footer(c, d):
    c.saveState(); c.setFont("Arial", 8); c.setFillColor(MUTE)
    c.drawString(1.7 * cm, 1.1 * cm, "VoiceScreen · complete source code and explanation")
    c.drawRightString(A4[0] - 1.7 * cm, 1.1 * cm, "Page %d" % d.page)
    c.setStrokeColor(LINE); c.line(1.7 * cm, 1.5 * cm, A4[0] - 1.7 * cm, 1.5 * cm); c.restoreState()


def cover(c, d):
    Wd, Ht = A4
    c.saveState(); c.setFillColor(INDIGO); c.rect(0, Ht * .45, Wd, Ht * .55, stroke=0, fill=1)
    c.setFillColor(VIOLET); c.setFillAlpha(.5)
    p = c.beginPath(); p.moveTo(Wd * .55, Ht); p.lineTo(Wd, Ht); p.lineTo(Wd, Ht * .45); p.lineTo(Wd * .78, Ht * .45); p.close()
    c.drawPath(p, stroke=0, fill=1); c.setFillAlpha(1)
    c.setFillColor(colors.white); c.setFont("Arial-Bold", 36); c.drawString(2 * cm, Ht - 7.5 * cm, "VoiceScreen")
    c.setFont("Arial", 15); c.drawString(2 * cm, Ht - 9 * cm, "Complete Source Code, Project Structure")
    c.drawString(2 * cm, Ht - 9.8 * cm, "and Explanation")
    c.setFont("Arial", 11); c.drawString(2 * cm, Ht - 11.4 * cm, "AI-Based Real-Time Voice Analysis System for the Early Detection of Parkinson's Disease")
    c.setFillColor(INK); c.setFont("Arial", 10.5)
    for i, t in enumerate(["Jain Institute of Technology, Davangere  ·  Department of Information Science and Engineering",
                           "Guide: Dr. H S Saraswathi, HOD ISE",
                           "Every source file in the project is reproduced in full, with line numbers, after a plain-language explanation.",
                           "A screening aid for research and education. It is not a medical diagnosis."]):
        c.drawString(2 * cm, Ht * .45 - (1.5 + i * .75) * cm, t)
    c.restoreState()


# ---------------------------------------------------------------- content
FILES = [
    # (path, title, what it is, how it works bullets, function table rows, run note)
    ("src/manifest.py", "Recording manifest",
     "Walks the two raw audio corpora and produces one table with a row per recording: file path, label (HC/PD), speaker id, source corpus, speech task and age group. Everything downstream (feature extraction, cross-validation folds) is driven by this table.",
     ["The Italian Parkinson's Voice and Speech set is organised in folders per group (22 elderly healthy, 28 PD, 15 young healthy); the folder name gives the label and the sub-folder gives the speaker.",
      "The KCL (mobile-phone) set stores PD and HC in separate folders; the speaker id is the number at the start of each file name.",
      "Speaker ids are prefixed with the corpus and label (<font name='Mono'>it_PD_…</font>, <font name='Mono'>kcl_…</font>) so that two corpora can never collide, and so that all windows of one person can later be kept in one cross-validation fold.",
      "Italian file names such as <font name='Mono'>VA1.wav</font> or <font name='Mono'>B2.wav</font> encode the task (sustained vowel, reading, syllable repetition). <font name='Mono'>italian_task()</font> maps the letter prefix to a task name.",
      "Young healthy controls are tagged <font name='Mono'>age_group='young'</font> so extraction can drop them (they are about 40 years younger than the PD group, which would let a model learn age instead of disease)."],
     [("italian_task(stem)", "Maps a file-name stem like VA1 to a task label."), ("build_manifest()", "Returns the full DataFrame including the numeric target y (1 = PD)."),
      ("__main__", "Prints counts per source/age/label and checks no speaker has two labels.")],
     "python src/manifest.py"),
    ("src/features.py", "Audio processing and feature extraction",
     "The heart of the signal-processing side. It converts a waveform into fixed 3-second windows and computes three representations of each window: a vector of hand-crafted voice features (for the classical models), a log-mel spectrogram image (for the CNN) and an MFCC sequence (for the LSTM). The live app imports this same file, so training and real-time inference see identical inputs.",
     ["<b>Constants</b>: 16 kHz sample rate, 3 s window (48 000 samples), 1.5 s hop (50 % overlap), 64 mel bands, 20 MFCCs, hop length 512 so a window has 94 frames.",
      "<b>normalise</b> removes the DC offset and scales to peak 1, so loudness differences between recordings do not matter.",
      "<b>voiced_fraction / windows</b>: the share of 25 ms frames above a silence threshold. Windows with less than 50 % speech are skipped, so silence is never scored. Short clips are zero-padded to one window.",
      "<b>praat_features</b> uses Praat (via parselmouth) to measure the clinical voice-quality markers: F0 statistics, jitter (5 variants, cycle-to-cycle pitch instability), shimmer (6 variants, cycle-to-cycle loudness instability), harmonics-to-noise ratio and formants F1–F3. Any failure returns NaN for that window rather than crashing.",
      "<b>mfcc_seq / logmel / spectral_features</b> use librosa: MFCCs with deltas, a dB log-mel spectrogram, and statistics (mean and standard deviation over time) of centroid, bandwidth, roll-off, flatness, zero-crossing rate, RMS and spectral contrast.",
      "<b>robust_cols</b> selects the 71 channel-robust features (Praat voice quality plus every “_std” variability feature). Absolute spectral levels mostly encode which microphone was used, so they are dropped. This was the fix for the model flagging healthy unseen speakers (see the report).",
      "<b>cmn_mel / cmn_mfcc</b> subtract each frequency band's average over time (cepstral-mean-style normalisation) to remove the fixed microphone/room response before the CNN and LSTM."],
     [("load_audio(path)", "Loads any audio file at 16 kHz mono and normalises it."), ("normalise(y)", "DC removal and peak scaling."),
      ("voiced_fraction(w)", "Share of frames above the silence threshold."), ("windows(y)", "Generator of 3 s windows with enough speech."),
      ("praat_features(w)", "19 Praat measures (F0, jitter, shimmer, HNR, formants)."), ("mfcc_seq(w)", "20 MFCCs + 20 deltas, shape (40, 94)."),
      ("logmel(w)", "Log-mel spectrogram, shape (64, 94)."), ("spectral_features(w, mf)", "Mean/std statistics of MFCC and spectral descriptors."),
      ("feature_names()", "Column names, in the same order as the feature vector."), ("robust_cols()", "Indices of the 71 channel-robust features."),
      ("cmn_mel / cmn_mfcc", "Per-band mean removal for the deep models."), ("window_features(w)", "Returns (tabular vector, log-mel, MFCC sequence).")],
     "Imported by every other module; not run directly."),
    ("src/extract.py", "Batch feature extraction",
     "Runs the feature code over every usable recording in parallel and caches the result as NumPy arrays, so model training never has to touch audio again.",
     ["Uses a <font name='Mono'>ProcessPoolExecutor</font> with 6 workers. Thread-count environment variables are forced to 1 <i>before</i> importing NumPy, because Praat, librosa and BLAS each spawn threads and oversubscription crashed the pool.",
      "<font name='Mono'>process()</font> loads a file, iterates its windows and returns the three feature sets; any error is printed as SKIP and the file is ignored.",
      "Young healthy controls are filtered out here.",
      "Outputs in <font name='Mono'>data_processed/</font>: <font name='Mono'>tab.npy</font> (windows × 207 features), <font name='Mono'>mel.npy</font> and <font name='Mono'>mfcc.npy</font> (float16 to halve disk size), <font name='Mono'>windows_meta.csv</font> (speaker, label, source, task, path, window index) and <font name='Mono'>feature_names.csv</font>.",
      "Result: 8 655 windows from 89 speakers (45 PD, 44 HC)."],
     [("process(row)", "Features for one recording; returns lists of tab/mel/mfcc arrays."), ("__main__", "Builds the manifest, runs the pool, saves arrays and metadata.")],
     "python src/extract.py"),
    ("src/train_ml.py", "Classical machine-learning models",
     "Trains and evaluates the five classical models (SVM, Random Forest, KNN, LDA, XGBoost) with speaker-independent cross-validation, runs a cross-corpus test, and saves the final models used by the app.",
     ["<b>make_models()</b> returns a fresh pipeline per model: median imputation for NaNs, standard scaling where the model needs it, then the classifier. SVM: RBF, C = 3, balanced class weights. Random Forest: 400 trees, min leaf 3. KNN: k = 25, distance-weighted. LDA: least-squares solver with automatic shrinkage. XGBoost: 400 trees, depth 4, learning rate 0.05, 80 % row and 50 % column sampling.",
      "<b>folds_for()</b> uses <font name='Mono'>StratifiedGroupKFold</font> (5 folds, seed 42) with the speaker as the group. All windows of one person land in one fold, so a model is never tested on a voice it has seen. The fold map is saved to <font name='Mono'>results/folds.csv</font> and reused by the deep-learning scripts for a fair comparison.",
      "<b>report()</b> scores at three levels: window, recording (mean of window probabilities per file) and speaker (mean per person). The speaker level is the headline number.",
      "The Ensemble is the plain average of the five models' probabilities.",
      "<b>Cross-corpus</b>: train on Italian and test on KCL, and the reverse. This exposes dependence on recording conditions.",
      "<b>Final fit</b>: each model is refit on all data and saved to <font name='Mono'>models/*.joblib</font>. <font name='Mono'>features.json</font> stores the selected column indices, feature names, healthy and PD means, standard deviations and medians, which the app uses to explain a score."],
     [("make_models()", "Dictionary of the five untrained pipelines."), ("score(y, p, thr)", "Accuracy, balanced accuracy, AUC, F1, sensitivity, specificity."),
      ("aggregate(meta, p, key)", "Averages window probabilities per recording or speaker."), ("report(meta, oof, name)", "Rows for window/recording/speaker levels."),
      ("folds_for(meta)", "Speaker-grouped stratified fold labels."), ("main()", "CV, cross-corpus test, final fit and saving.")],
     "python src/train_ml.py"),
    ("src/train_dl.py", "Deep-learning models (CNN and BiLSTM)",
     "Trains a 2-D CNN on log-mel spectrograms and a bidirectional LSTM on MFCC sequences, with the same speaker-independent folds as the classical models. Runs on the GPU when CUDA is available.",
     ["<b>CNN</b>: four blocks of Conv-BatchNorm-ReLU-MaxPool with 16, 32, 64 and 64 filters, global average pooling, dropout 0.4, one output logit. Input is the (64 × 94) log-mel image.",
      "<b>LSTM</b>: two bidirectional layers with 64 hidden units; the output sequence is summarised by concatenating its mean and max over time, then dropout and a linear layer. Input is the (40 × 94) MFCC+delta sequence transposed to time-major.",
      "<b>augment()</b>: Gaussian noise plus SpecAugment-style random frequency and time masking; the CNN also gets a random circular frequency shift.",
      "<b>fit()</b>: AdamW with a OneCycle learning-rate schedule (max 3e-3), 30 epochs, batch 64, gradient clipping at 1.0 and a positive-class weight for the class imbalance. The best epoch is chosen on <i>validation speakers held out from the training folds</i>, never on the test fold.",
      "<b>normalise()</b>: the CNN input gets per-band mean removal and scaling per window; the LSTM input gets mean removal and a global per-feature standard deviation (saved in <font name='Mono'>lstm_norm.npz</font> for the app).",
      "After cross-validation a final model is trained on every speaker for the median best epoch count and saved as <font name='Mono'>cnn.pt</font> / <font name='Mono'>lstm.pt</font>."],
     [("CNN, LSTM", "The two network classes."), ("augment(x, kind)", "Training-time augmentation."), ("predict(model, X)", "Batched sigmoid probabilities."),
      ("fit(...)", "Training loop with validation-based epoch selection."), ("load(kind)", "Loads mel.npy or mfcc.npy."), ("normalise(Xtr, X, kind)", "Channel normalisation."),
      ("main(kind)", "5-fold CV, saving OOF predictions and the final model.")],
     "python src/train_dl.py cnn   |   python src/train_dl.py lstm"),
    ("src/train_uci.py", "UCI benchmark",
     "Applies the same five models to the UCI “Parkinson's Disease Classification” tabular set (756 recordings, 252 subjects, 750+ pre-computed features) as an independent benchmark. All three recordings of a subject stay in one fold.",
     ["Reads <font name='Mono'>pd_speech_features.csv</font> (header on the second row), drops id and class from the features.",
      "Reuses <font name='Mono'>make_models()</font> and <font name='Mono'>score()</font> from <font name='Mono'>train_ml.py</font>.",
      "Reports both recording-level and subject-level metrics to <font name='Mono'>results/uci470_results.csv</font>."],
     [("module body", "Loads data, runs grouped CV, writes the results table.")], "python src/train_uci.py"),
    ("src/experiment_robust.py", "Robust-feature experiment",
     "The experiment that diagnosed and fixed the microphone problem. For three feature subsets it measures speaker-independent CV, train-on-A/test-on-B in both directions, and the false-alarm rate on 40 unseen healthy LibriSpeech speakers.",
     ["Subsets: all 207 features (baseline), Praat voice quality only, and Praat plus all “_std” dynamics (the 71 features finally used).",
      "LibriSpeech features are extracted once and cached to <font name='Mono'>libri_tab.npy</font>.",
      "Findings: with all features CV was high but about half of unseen healthy speakers were flagged; the robust subset cut false alarms sharply at similar CV accuracy. Results go to <font name='Mono'>results/robustness_experiment.csv</font>."],
     [("module body", "Loops over subsets × models, writes the table and a per-subset summary.")], "python src/experiment_robust.py"),
    ("src/eval_external.py", "External false-alarm check",
     "Runs every saved model (five classical, CNN, LSTM and their ensemble) on LibriSpeech test-clean: 40 healthy English speakers, 6 files each, never used in training. Because every speaker is healthy, any “PD” prediction is a false alarm.",
     ["Uses exactly the same windowing, feature extraction and per-model preprocessing as the app.",
      "Writes window-level and speaker-level false-alarm rates and the mean score to <font name='Mono'>results/external_librispeech.csv</font>.",
      "This is the test that showed the deep models do not generalise across microphones, which is why the live ensemble uses only LDA, XGBoost, Random Forest and SVM."],
     [("module body", "Loads models, scores LibriSpeech, tabulates false alarms.")], "python src/eval_external.py"),
    ("run_training.sh", "Training pipeline script",
     "One command that runs everything after extraction, in order: classical models, then CNN, then LSTM, then the external check. It uses the CUDA virtual environment so the deep models train on the GPU.",
     ["The <font name='Mono'>&amp;&amp;</font> chain stops at the first failing step."], [("script", "Runs train_ml, train_dl cnn, train_dl lstm, eval_external.")], "bash run_training.sh"),
    ("models/config.json", "Live-ensemble configuration",
     "Tells the server which models contribute to the displayed score. CNN, LSTM and KNN are still computed and shown on screen for comparison, but they are not averaged into the score because of their false-alarm rates on unseen speakers.",
     ["Edit the <font name='Mono'>use</font> list to change the ensemble; restart the server."], [("use", "Model names included in the score.")], ""),
    ("app/server.py", "Flask inference server",
     "Loads every saved model once at start-up and exposes the real-time API. The browser never runs a model; it only sends audio.",
     ["<b>Start-up</b>: loads <font name='Mono'>*.joblib</font> models, the CNN/LSTM weights, the LSTM normalisation statistics, feature statistics and the config.",
      "<b>score_window(w)</b>: extracts features once for a normalised 3 s window, runs all models (CNN/LSTM with their own preprocessing), and averages only the models listed in <font name='Mono'>use</font>.",
      "<b>explain()</b>: for each of the 71 features computes how many standard deviations the value is from the healthy mean, signed so that positive means “moves towards the PD mean”. The five largest are returned with direction and strength, which the UI shows as plain-language reasons.",
      "<b>POST /predict</b> (live microphone): takes the latest 3 s of float32 audio. A raw peak below 0.02 is rejected as silence <i>before</i> normalising, otherwise normalisation would amplify noise into a fake signal; windows with under 30 % voiced frames are also rejected.",
      "<b>POST /analyze</b> (uploaded file): up to 90 s; normalises the whole file once, then slides 3 s windows every 1.5 s exactly as in training, scoring only windows with at least 50 % speech. Returns per-window scores, per-model means, the overall mean, explanations and duration.",
      "<b>GET /models</b> lists the models in use; <b>GET /</b> serves the web page. Runs on 127.0.0.1:5000."],
     [("explain(tab, k)", "Top-k features pushing towards PD or healthy."), ("score_window(w)", "All model probabilities + ensemble score."),
      ("index()", "Serves index.html."), ("models()", "JSON list of models in use."), ("predict()", "Live endpoint."), ("analyze()", "File-upload endpoint.")],
     "python app/server.py   then open http://127.0.0.1:5000"),
    ("app/static/index.html", "Browser user interface",
     "A single self-contained file (HTML + CSS + JavaScript, no frameworks, no build step) that provides the whole user experience in English, Hindi and Kannada.",
     ["<b>Layout (lines 1–271)</b>: design tokens for light and dark themes, a hero section, the voice-test card with a half-circle gauge, a live spectrogram card, a chart of score over time, per-model bars, the “why this score” feature list, a summary card, and the upload drop zone.",
      "<b>Translations (<font name='Mono'>T</font> object)</b>: every visible string for en/hi/kn; <font name='Mono'>render()</font> re-applies them when the language dropdown changes. The Hindi and Kannada text needs review by native speakers.",
      "<b>Microphone capture (<font name='Mono'>start/stop</font>)</b>: <font name='Mono'>getUserMedia</font> with echo cancellation, noise suppression and auto gain <i>off</i> (they would distort voice-quality measures); a ScriptProcessor keeps a rolling 3 s buffer, resampled to 16 kHz by linear interpolation.",
      "<b>tick()</b> runs every 1.5 s, posts the buffer to <font name='Mono'>/predict</font>, keeps a moving average of the last four scores and updates the gauge, model bars, features and chart.",
      "<b>Upload</b>: <font name='Mono'>decodeTo16k</font> decodes the file in the browser with <font name='Mono'>decodeAudioData</font>, resamples to 16 kHz mono with an <font name='Mono'>OfflineAudioContext</font> and posts it to <font name='Mono'>/analyze</font>. Drag-and-drop is supported.",
      "<b>Score levels</b>: below 35 % “low”, 35–65 % “uncertain”, above 65 % “higher”. The page always states that it is a screening aid, not a diagnosis.",
      "<b>Summary</b> offers a downloadable JSON report and a print option."],
     [("friendly(name)", "Turns feature names into plain language."), ("render()", "Applies the selected language."), ("resample(x, from)", "Linear resampling to 16 kHz."),
      ("start() / stop()", "Begin and end live capture."), ("tick()", "Send audio, update views."), ("level / paintVerdict / paintScore", "Gauge and verdict."),
      ("paintModels / paintFeatures / paintChart", "Model bars, reasons, time chart."), ("drawSpec()", "Animated heat-map spectrogram."),
      ("decodeTo16k / analyseFile", "File upload path."), ("summarise()", "Session summary card.")],
     "Served by server.py."),
    ("docs/make_figures.py", "Report figures",
     "Draws the charts and the pipeline diagram used in the project report (data composition, cross-validation comparison, ROC curves and confusion matrix, before/after robustness fix, pipeline). All values are read from the CSV files in <font name='Mono'>results/</font>, so figures always match the numbers.",
     ["Outputs go to <font name='Mono'>docs/figures/</font>."], [("module body", "Creates each figure with matplotlib.")], "python docs/make_figures.py"),
    ("docs/build_report.py", "Project report generator",
     "Builds the 19-page <font name='Mono'>VoiceScreen_Project_Report.pdf</font> with ReportLab: cover, contents, background, methods, results tables read from the CSVs, figures and appendices.",
     ["Uses the helper functions P/H1/H2/table/callout/bullets and a table of contents built by multi-pass layout."], [("module body", "Assembles the story and builds the PDF.")],
     "python docs/build_report.py"),
]

TREE = """Parkison's Disease/
├── datasets/                      raw data (downloaded, not code)
│   ├── italian_pvs_audio/         Italian Parkinson's Voice & Speech (HC + PD)
│   ├── mdvr_kcl_audio/            King's College London mobile-phone voices
│   ├── librispeech_test_clean/    40 healthy speakers, external false-alarm test
│   └── uci_174 / 189 / 301 / 470 / 489/   UCI tabular benchmark sets
├── data_processed/                cached features written by extract.py
│   ├── tab.npy                    (windows x 207) hand-crafted features
│   ├── mel.npy                    (windows x 64 x 94) log-mel images
│   ├── mfcc.npy                   (windows x 40 x 94) MFCC+delta sequences
│   ├── windows_meta.csv           speaker / label / source / task per window
│   └── feature_names.csv
├── src/                           pipeline code
│   ├── manifest.py                build table of recordings
│   ├── features.py                windowing + feature extraction (shared with app)
│   ├── extract.py                 parallel feature extraction
│   ├── train_ml.py                SVM, RF, KNN, LDA, XGBoost + CV + final models
│   ├── train_dl.py                CNN and BiLSTM (GPU)
│   ├── train_uci.py               UCI benchmark
│   ├── experiment_robust.py       microphone-robustness experiment
│   └── eval_external.py           LibriSpeech false-alarm check
├── models/                        trained artefacts used by the app
│   ├── SVM / RandomForest / KNN / LDA / XGBoost .joblib
│   ├── cnn.pt, lstm.pt, lstm_norm.npz
│   ├── features.json              columns, names, HC/PD means for explanations
│   └── config.json                which models form the live score
├── app/
│   ├── server.py                  Flask API (/predict, /analyze, /models)
│   └── static/index.html          browser UI (mic, upload, gauge, 3 languages)
├── results/                       all metrics (CSV) and out-of-fold predictions
├── docs/
│   ├── make_figures.py            report charts
│   ├── build_report.py            19-page project report
│   ├── build_code_pdf.py          this document
│   └── figures/                   generated PNGs
├── run_training.sh                ML -> CNN -> LSTM -> external check
└── .venv_gpu/                     Python environment with CUDA PyTorch"""


def build():
    story = [Spacer(1, 1), PageBreak()]
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("t0", fontName="Arial", fontSize=10, leading=17, textColor=INK, leftIndent=0)]
    story += [H1("Contents"), toc, PageBreak()]

    story += [H1("1. Project overview")]
    story += [P("<b>VoiceScreen</b> listens to a short voice sample, from a microphone or an uploaded file, and estimates how closely the voice resembles the speech of people with Parkinson's disease. "
                "Parkinson's disease often changes the voice early: pitch and loudness become less steady (jitter and shimmer), the voice becomes breathier (lower harmonics-to-noise ratio) and the spectrum varies less. "
                "The system measures these effects automatically, scores them with several machine-learning models and explains the score in plain language."),
              P("It is a <b>screening aid for research and education</b>. It is not a medical device and its output is not a diagnosis."),
              H2("How the system works, end to end")]
    if (FIG / "fig_pipeline.png").exists():
        im = Image(str(FIG / "fig_pipeline.png")); im.drawWidth = 17 * cm; im.drawHeight = 17 * cm * im.imageHeight / im.imageWidth
        story += [im, Spacer(1, 6)]
    story += bullets([
        "<b>Data</b>: two audio corpora (Italian and KCL) give 89 speakers (45 Parkinson's, 44 healthy) and 8 655 three-second windows.",
        "<b>Features</b>: Praat voice-quality measures, MFCC statistics and spectral statistics; plus log-mel images and MFCC sequences for the neural networks.",
        "<b>Models</b>: SVM, Random Forest, KNN, LDA and XGBoost on the 71 robust features; a CNN and a BiLSTM on the sequences.",
        "<b>Validation</b>: speaker-independent 5-fold cross-validation, a cross-corpus test and an external false-alarm test on unseen healthy speakers.",
        "<b>Deployment</b>: Flask server running the models; a single web page that records or uploads audio every 1.5 s and shows a live score.",
        "<b>Headline result</b>: the five-model ensemble reaches 94.4 % speaker-level accuracy (sensitivity 88.9 %, specificity 100 %, AUC 0.955) in speaker-independent cross-validation. The live four-model ensemble flags 7.5 % of 40 unseen healthy speakers."])
    story += [H2("Technology stack"),
              table([["Area", "Tools"],
                     ["Language", "Python 3.14 (data and app), Python with CUDA PyTorch for GPU training, JavaScript (browser)"],
                     ["Signal processing", "librosa 1.0, praat-parselmouth 0.4.7, NumPy 2.5, SciPy 1.18"],
                     ["Classical ML", "scikit-learn 1.9, XGBoost 3.4, joblib 1.6, pandas 3.1"],
                     ["Deep learning", "PyTorch 2.14 (CUDA 12.6) on an RTX 3050 laptop GPU"],
                     ["Web", "Flask 3.1 backend; plain HTML/CSS/JS with Web Audio API"],
                     ["Reports", "matplotlib 3.10, ReportLab 4.5"]], [3.6, 13.8]),
              H2("How to set up and run"),
              table([["Step", "Command"],
                     ["1. Install", "pip install numpy pandas scipy librosa praat-parselmouth scikit-learn xgboost joblib flask matplotlib reportlab; install PyTorch from pytorch.org (CUDA build for GPU)"],
                     ["2. Place data", "Put the datasets under datasets/ as shown in the structure tree"],
                     ["3. Extract features", "python src/extract.py   "],
                     ["4. Train all models", "bash run_training.sh    (or run train_ml.py, train_dl.py cnn, train_dl.py lstm, eval_external.py individually)"],
                     ["5. Start the app", "python app/server.py    then open http://127.0.0.1:5000"],
                     ["6. Use it", "Click Start test and say “aaah” or read the passage, or upload a recording (up to 90 s)"]], [3.6, 13.8], mono_first=False),
              PageBreak()]

    story += [H1("2. Project structure"),
              P("The code is deliberately split by responsibility: <b>src</b> holds the pipeline, <b>models</b> holds what training produces, <b>app</b> holds what users see, and <b>results</b> holds every number quoted in the report."),
              Preformatted(TREE, S["tree"], dedent=0), Spacer(1, 8),
              H2("What each file does"),
              table([["File", "Role"]] + [[f[0], f[2].split(". ")[0].rstrip(".") + "."] for f in FILES], [5.2, 12.2], mono_first=True),
              H2("Data flow between files"),
              table([["Step", "Reads", "Writes"],
                     ["manifest.py", "datasets/ audio folders", "in-memory table (used by extract.py)"],
                     ["extract.py", "manifest + features.py", "data_processed/*.npy, windows_meta.csv"],
                     ["train_ml.py", "tab.npy, windows_meta.csv", "results/folds.csv, ml_results.csv, models/*.joblib, features.json"],
                     ["train_dl.py", "mel.npy / mfcc.npy, folds.csv", "results/cnn|lstm_results.csv, models/cnn.pt, lstm.pt, lstm_norm.npz"],
                     ["eval_external.py", "models/, LibriSpeech", "results/external_librispeech.csv"],
                     ["server.py", "models/, features.py", "HTTP JSON responses"],
                     ["index.html", "server.py API", "what the user sees"]], [3.4, 6.4, 7.6], mono_first=True),
              PageBreak()]

    story += [H1("3. Design decisions worth knowing"),
              *bullets([
                  "<b>Speaker-independent validation.</b> Splitting windows randomly would put the same person in training and test sets and give inflated accuracy (a well-known pitfall in voice-PD studies). Folds are formed on speakers, and window scores are averaged per speaker.",
                  "<b>Young controls removed.</b> They are decades younger than the PD group, so separating them partly measures age.",
                  "<b>Channel robustness.</b> The first models scored about 93 % in cross-validation but flagged about half of unseen healthy speakers, because absolute spectral features encode the microphone. Keeping only voice-quality and variability features, and normalising each frequency band for the neural networks, cut false alarms from 49.5 % to 10.5 % (7.5 % for the live ensemble).",
                  "<b>Honest ensemble.</b> CNN and LSTM did not generalise to new microphones, so they are displayed for comparison but excluded from the live score.",
                  "<b>Same code in training and in the app.</b> The server imports features.py, so there is no train/serve mismatch.",
                  "<b>Silence handling.</b> The raw peak is checked before normalisation; otherwise noise would be amplified into a high-confidence fake signal.",
                  "<b>Raw audio settings.</b> Browser echo cancellation, noise suppression and auto-gain are switched off because they distort jitter, shimmer and HNR.",
                  "<b>Explainability.</b> Each score comes with the five features that moved it most, and in which direction."]),
              H2("Known limitations"),
              *bullets(["Only 89 speakers; results are cross-validated estimates, not clinical evidence.",
                        "Live accuracy on new microphones and in noisy rooms has not been measured.",
                        "The fifth classical model (XGBoost) was chosen by the developer because the synopsis names four.",
                        "The Hindi and Kannada interface text needs review by native speakers."]),
              P("<b>How to read the listings.</b> Each file below has a short explanation, a table of its functions and then the complete source with line numbers. A wrapped long line is shown with an indented continuation and no number. "
                "Hindi and Kannada characters in <font name='Mono'>index.html</font> are drawn with the Nirmala UI font; a PDF library cannot join Kannada conjuncts exactly as a browser does, so the HTML file itself is the authoritative text."),
              PageBreak()]

    for i, (path, title, what, pts, fns, run) in enumerate(FILES, 1):
        code, n = listing(ROOT / path)
        story += [H1(f"{3 + i}. {title}"), P(f"<font name='Mono'>{path}</font> &nbsp;·&nbsp; {n} lines"), P(what)]
        story += [H2("How it works")] + bullets(pts)
        story += [H2("Functions and parts"), table([["Name", "Purpose"]] + [[a, b] for a, b in fns], [5.6, 11.8], mono_first=True)]
        if run:
            story += [H2("How to run"), Preformatted(run, S["tree"])]
        story += [H2("Complete source"), code, PageBreak()]

    k = 3 + len(FILES) + 1
    story += [H1(f"{k}. API reference"),
              table([["Endpoint", "Request", "Response"],
                     ["GET /", "none", "index.html"],
                     ["GET /models", "none", "JSON list of model names in the live score"],
                     ["POST /predict", "raw float32 PCM, 16 kHz mono, at least 1 s (latest 3 s used)",
                      "status ok: score, per-model probabilities, used models, voiced fraction, top-5 feature explanations. status no_voice or too_short otherwise"],
                     ["POST /analyze", "raw float32 PCM, 16 kHz mono, up to 90 s",
                      "status ok: per-window scores, mean score, per-model means, explanations, duration"]], [3.2, 6.2, 8], mono_first=True),
              H2("Feature set (207 columns, 71 used)"),
              P("Praat (19): f0_mean, f0_std, f0_min, f0_max, voiced_ratio, five jitter and six shimmer variants, hnr, f1, f2, f3. "
                "Spectral (188): mean and standard deviation over time of 20 MFCCs, 20 MFCC deltas, six spectral descriptors (centroid, bandwidth, roll-off, flatness, zero-crossing rate, RMS) and seven spectral-contrast bands. "
                "The 71 used are the 19 Praat measures plus every feature ending in <font name='Mono'>_std</font>, which describe how much the voice varies rather than how loud or bright it is."),
              H2("Result files"),
              table([["File", "Contents"],
                     ["results/ml_results.csv", "Five models + ensemble at window, recording and speaker level"],
                     ["results/cnn_results.csv, lstm_results.csv", "Deep-model cross-validation results"],
                     ["results/ml_cross_corpus.csv", "Train Italian→test KCL and reverse"],
                     ["results/robustness_experiment.csv", "Feature-subset experiment"],
                     ["results/external_librispeech.csv", "False-alarm rates on 40 unseen healthy speakers"],
                     ["results/uci470_results.csv", "UCI benchmark"],
                     ["results/oof_*.csv, folds.csv", "Out-of-fold predictions and the speaker-to-fold map"]], [6.4, 11], mono_first=True)]

    path = OUT
    doc = Doc(str(path), pagesize=A4, leftMargin=1.7 * cm, rightMargin=1.7 * cm, topMargin=1.6 * cm, bottomMargin=2 * cm,
              title="VoiceScreen: complete source code and explanation", author="VoiceScreen project")
    fr = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate("cover", [fr], onPage=cover), PageTemplate("main", [fr], onPage=footer)])
    from reportlab.platypus import NextPageTemplate
    story.insert(0, NextPageTemplate("main"))
    doc.multiBuild(story)
    print("written", path, path.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    build()
