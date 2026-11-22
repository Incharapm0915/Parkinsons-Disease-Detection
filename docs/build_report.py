"""Builds docs/VoiceScreen_Project_Report.pdf. Numbers come from results/*.csv; charts from docs/make_figures.py."""
import datetime
from pathlib import Path

import pandas as pd
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, ListFlowable, ListItem, PageBreak, PageTemplate,
                                Paragraph, Preformatted, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
FIG, RES = ROOT / "docs" / "figures", ROOT / "results"
OUT = ROOT / "docs" / "VoiceScreen_Project_Report.pdf"

F = "C:/Windows/Fonts/"
for name, file in (("Arial", "arial.ttf"), ("Arial-Bold", "arialbd.ttf"), ("Arial-Italic", "ariali.ttf"), ("Arial-BoldItalic", "arialbi.ttf")):
    pdfmetrics.registerFont(TTFont(name, F + file))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic", boldItalic="Arial-BoldItalic")

INDIGO, VIOLET = colors.HexColor("#3b4fd9"), colors.HexColor("#8a5cf5")
INK, MUTE, LINE = colors.HexColor("#1d2540"), colors.HexColor("#5b6882"), colors.HexColor("#d9deea")
TINT, GREEN, RED, AMBER = colors.HexColor("#f2f4fd"), colors.HexColor("#14966b"), colors.HexColor("#d9483b"), colors.HexColor("#d68a10")

S = {
    "body": ParagraphStyle("body", fontName="Arial", fontSize=9.8, leading=14.6, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=6),
    "h1": ParagraphStyle("h1", fontName="Arial-Bold", fontSize=18, leading=22, textColor=INDIGO, spaceBefore=4, spaceAfter=10),
    "h1x": ParagraphStyle("h1x", fontName="Arial-Bold", fontSize=18, leading=22, textColor=INDIGO, spaceBefore=4, spaceAfter=10),
    "h2": ParagraphStyle("h2", fontName="Arial-Bold", fontSize=12.2, leading=16, textColor=INK, spaceBefore=10, spaceAfter=5),
    "cap": ParagraphStyle("cap", fontName="Arial-Italic", fontSize=8.4, leading=11, textColor=MUTE, alignment=TA_CENTER, spaceAfter=10),
    "cell": ParagraphStyle("cell", fontName="Arial", fontSize=8.6, leading=11.2, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Arial-Bold", fontSize=8.6, leading=11.2, textColor=colors.white),
    "small": ParagraphStyle("small", fontName="Arial", fontSize=8.4, leading=11.4, textColor=MUTE),
    "ref": ParagraphStyle("ref", fontName="Arial", fontSize=8.8, leading=12.4, textColor=INK, leftIndent=14, firstLineIndent=-14, spaceAfter=4),
    "toc1": ParagraphStyle("toc1", fontName="Arial-Bold", fontSize=10.5, leading=17, spaceBefore=4, textColor=INK),
    "toc2": ParagraphStyle("toc2", fontName="Arial", fontSize=9, leading=12.2, leftIndent=16, textColor=MUTE),
}


def P(t, s="body"):
    return Paragraph(t, S[s])


def H1(t):
    return Paragraph(t, S["h1"])


def H2(t):
    return Paragraph(t, S["h2"])


def bullets(items, size=None):
    return ListFlowable([ListItem(P(i), leftIndent=14, value="circle") for i in items], bulletType="bullet", start="•",
                        bulletFontName="Arial", bulletFontSize=9, bulletColor=INDIGO, leftIndent=14)


def table(rows, widths, head=True, align=None, zebra=True, bold_first_col=False):
    data = [[(P(str(c), "cellb") if (head and r == 0) else P(("<b>%s</b>" % c) if (bold_first_col and k == 0) else str(c), "cell"))
             for k, c in enumerate(row)] for r, row in enumerate(rows)]
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1 if head else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
          ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("LINEBELOW", (0, 0), (-1, -1), .4, LINE)]
    if head:
        st += [("BACKGROUND", (0, 0), (-1, 0), INDIGO)]
    if zebra:
        st += [("BACKGROUND", (0, r), (-1, r), TINT) for r in range(2 if head else 1, len(rows), 2)]
    t.setStyle(TableStyle(st))
    return t


def callout(text, color=INDIGO, title=None):
    body = [P(("<b>%s</b><br/>" % title if title else "") + text, "cell")]
    t = Table([[body]], colWidths=[17 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.Color(color.red, color.green, color.blue, alpha=.08)),
                           ("LINEBEFORE", (0, 0), (0, -1), 3.2, color), ("LEFTPADDING", (0, 0), (-1, -1), 11), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return t


def kpis(items):
    cells = [[Paragraph('<font name="Arial-Bold" size="20" color="#3b4fd9">%s</font><br/><font size="7.8" color="#5b6882">%s</font>' % (v, l),
                        ParagraphStyle("k", alignment=TA_CENTER, leading=24, fontName="Arial")) for v, l in items]]
    t = Table(cells, colWidths=[17 / len(items) * cm] * len(items))
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), TINT), ("BOX", (0, 0), (-1, -1), .5, LINE), ("INNERGRID", (0, 0), (-1, -1), .5, colors.white),
                           ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    return t


def fig(name, width_cm, caption):
    w, h = PILImage.open(FIG / name).size
    return KeepTogether([Image(str(FIG / name), width=width_cm * cm, height=width_cm * cm * h / w), P(caption, "cap")])


class Doc(BaseDocTemplate):
    def afterFlowable(self, fl):
        if isinstance(fl, Paragraph) and fl.style.name == "h1":
            self.notify("TOCEntry", (0, fl.getPlainText(), self.page))


def footer(c, d):
    c.saveState()
    c.setFont("Arial", 8)
    c.setFillColor(MUTE)
    c.drawString(2 * cm, 1.2 * cm, "VoiceScreen · AI-based real-time voice analysis for Parkinson's disease screening")
    c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, "Page %d" % d.page)
    c.setStrokeColor(LINE)
    c.line(2 * cm, 1.6 * cm, A4[0] - 2 * cm, 1.6 * cm)
    c.restoreState()


def cover(c, d):
    W, H = A4
    c.saveState()
    c.setFillColor(INDIGO)
    c.rect(0, H * .42, W, H * .58, stroke=0, fill=1)
    c.setFillColor(VIOLET)
    p = c.beginPath(); p.moveTo(W * .55, H); p.lineTo(W, H); p.lineTo(W, H * .42); p.lineTo(W * .78, H * .42); p.close()
    c.setFillAlpha(.55); c.drawPath(p, stroke=0, fill=1); c.setFillAlpha(1)
    c.setStrokeColor(colors.white); c.setLineWidth(3); c.setLineCap(1); c.setLineJoin(1)       # waveform mark
    pts = [(2.2, 0), (3.4, 0), (4.2, 1.7), (5.6, -2.6), (7, 3.6), (8.3, -1.6), (9, 0), (10.4, 0)]
    q = c.beginPath(); q.moveTo(2 * cm + pts[0][0] * .45 * cm, H - 5.2 * cm + pts[0][1] * .45 * cm)
    for x, y in pts[1:]:
        q.lineTo(2 * cm + x * .45 * cm, H - 5.2 * cm + y * .45 * cm)
    c.drawPath(q, stroke=1, fill=0)
    c.setFillColor(colors.white)
    c.setFont("Arial-Bold", 38); c.drawString(2 * cm, H - 9.2 * cm, "VoiceScreen")
    c.setFont("Arial", 15)
    c.drawString(2 * cm, H - 10.7 * cm, "AI-Based Real-Time Voice Analysis System")
    c.drawString(2 * cm, H - 11.5 * cm, "for the Early Detection of Parkinson's Disease")
    c.setFont("Arial-Bold", 11); c.drawString(2 * cm, H - 13.4 * cm, "PROJECT DOCUMENTATION AND RESULTS REPORT")
    c.setFillColor(INK)
    c.setFont("Arial-Bold", 11); c.drawString(2 * cm, H * .42 - 2 * cm, "Jain Institute of Technology, Davangere")
    c.setFont("Arial", 10.5); c.setFillColor(MUTE)
    c.drawString(2 * cm, H * .42 - 2.7 * cm, "Synopsis presentation project · Under the guidance of Dr. H S Saraswathi, HOD, Department of ISE")
    c.setFont("Arial", 9.5)
    c.drawString(2 * cm, 3.3 * cm, "Report generated: " + datetime.date.today().strftime("%d %B %Y"))
    c.drawString(2 * cm, 2.7 * cm, "Screening aid for research and education only. Not a medical device and not a diagnosis.")
    c.restoreState()


# ------------------------------------------------------------------ data
ml = pd.read_csv(RES / "ml_results.csv")
dl = pd.concat([pd.read_csv(RES / "cnn_results.csv"), pd.read_csv(RES / "lstm_results.csv")])
allr = pd.concat([ml, dl])
spk, wnd = allr[allr.level == "speaker"].set_index("model"), allr[allr.level == "window"].set_index("model")
uci = pd.read_csv(RES / "uci470_results.csv")
uci = uci[uci.level == "subject"].set_index("model")
rb = pd.read_csv(RES / "robustness_experiment.csv")
cross = pd.read_csv(RES / "ml_cross_corpus.csv")
pc = lambda x: "%.1f%%" % (100 * x)
order = ["SVM", "RandomForest", "KNN", "LDA", "XGBoost", "Ensemble", "CNN", "LSTM"]
nice = {"RandomForest": "Random Forest", "Ensemble": "Ensemble of 5 ML models", "CNN": "CNN (spectrogram)", "LSTM": "BiLSTM (MFCC sequence)"}

story = []

# ------------------------------------------------------------------ contents
story += [PageBreak(), Paragraph("Contents", S["h1x"])]
toc = TableOfContents()
toc.levelStyles = [S["toc1"], S["toc2"]]
story += [toc, PageBreak()]

# ------------------------------------------------------------------ 1
story += [H1("1. Executive summary"),
          P("VoiceScreen is a working prototype of the system proposed in the synopsis: a non-invasive tool that listens to a person's voice and estimates "
            "how closely it resembles the voices of people with Parkinson's disease. It was built end to end: public voice datasets were collected and cleaned, "
            "seven models were trained and compared (the five machine-learning models plus a CNN and an LSTM), and a web application was created that scores a "
            "live microphone stream, or an uploaded recording, in real time and explains which voice features drove the score."),
          kpis([("89", "speakers (45 PD, 44 healthy)"), ("8,655", "three-second windows"), (pc(spk.loc["Ensemble", "acc"]), "ensemble accuracy, unseen speakers"),
                ("7.5%", "false alarms, 40 unseen healthy speakers")]),
          Spacer(1, 8),
          H2("Main findings"),
          bullets([
              "<b>The ML models work well when test speakers are new but the recording setup is familiar.</b> With speakers kept completely separate between "
              "training and testing, the five-model ensemble reaches %s speaker-level accuracy (sensitivity %s, specificity %s, AUC %.3f). "
              "The best single model is Random Forest (%s); the other four are within about two points of it." % (
                  pc(spk.loc["Ensemble", "acc"]), pc(spk.loc["Ensemble", "sens"]), pc(spk.loc["Ensemble", "spec"]), spk.loc["Ensemble", "auc"], pc(spk.loc["RandomForest", "acc"])),
              "<b>Early results were misleading, and this was found and partly fixed.</b> The first models scored about 93% but were at chance when trained on one "
              "corpus and tested on the other, and flagged about half of 40 unseen healthy speakers as Parkinson's. They had learnt the microphone, not the voice. "
              "Keeping only channel-robust features (71 of 125) cut false alarms from 49.5% to 10.5% on average while accuracy barely changed.",
              "<b>The deep models are weaker and do not generalise.</b> The CNN (%s) and BiLSTM (%s) are below the ML ensemble and still flag roughly half of unseen "
              "healthy speakers. They are reported honestly and shown in the app for comparison, but excluded from the live score." % (pc(spk.loc["CNN", "acc"]), pc(spk.loc["LSTM", "acc"])),
              "<b>A complete application exists.</b> It supports live microphone analysis (a new score every 1.5 s), audio-file upload, a live spectrogram, "
              "per-model scores, plain-language explanations, a session report and an English / Hindi / Kannada interface.",
              "<b>Main limitation:</b> 89 speakers, two languages and two recording setups. The results are promising but do not prove clinical accuracy, "
              "and performance on other microphones and languages is unproven.",
          ]),
          Spacer(1, 6),
          callout("The figures quoted in this report are speaker-independent cross-validation results. They are lower than the 95–99% sometimes reported in the literature, "
                  "because those papers often let recordings of the same person appear in both training and test data. The lower number here is the honest one.",
                  AMBER, "How to read the accuracy")]

# ------------------------------------------------------------------ 2
story += [PageBreak(), H1("2. Background and problem statement"),
          P("Parkinson's disease is a progressive neurological disorder caused by the loss of dopamine-producing cells. It affects movement and also speech: voices "
            "become quieter, more monotone, breathier and less steady. Diagnosis normally relies on clinical examination, neurological tests and imaging. These are "
            "expensive and time-consuming, and they may miss the subtle changes of the early stage."),
          P("Voice-based biomarkers such as pitch, jitter (cycle-to-cycle pitch irregularity), shimmer (cycle-to-cycle loudness irregularity), harmonics-to-noise "
            "ratio and MFCCs (a compact description of the spectrum) can be measured from a short recording with only a microphone. Machine learning can combine "
            "them into a risk estimate. However, existing approaches mostly work on pre-recorded samples with manually extracted features, and are rarely tested "
            "on unseen speakers or different microphones."),
          callout("<b>Problem statement (from the synopsis).</b> Early detection of Parkinson's disease is difficult because the initial symptoms are subtle and develop "
                  "gradually. Voice biomarkers are useful but not widely used. There is a need for an AI-based, non-invasive system for early and reliable screening.",
                  INDIGO),
          Spacer(1, 6),
          H2("Objectives and what was delivered"),
          table([
              ["Objective in the synopsis", "What was built", "Status"],
              ["Real-time AI system for early detection using voice analysis", "Browser microphone streamed to a Flask server; a new score every 1.5 s from the latest 3 s of audio, smoothed over 4 windows.", "Delivered"],
              ["Extract and analyse pitch, jitter, shimmer, MFCC", "Praat-based pitch, jitter, shimmer, HNR and formants plus MFCC / spectral statistics (125 candidate features, 71 kept).", "Delivered"],
              ["ML classification with confidence score and explainability", "Five ML models plus CNN and LSTM; probability score; the explanation panel lists the voice features that look closer to the PD or healthy group.", "Delivered (simple explanations, not SHAP)"],
              ["User-friendly web app with language-independent analysis", "Responsive web app; interface in English, Hindi, Kannada. The analysis uses no speech recognition, so it is language-agnostic by design, but it was validated only on Italian and English.", "Partly: validated on 2 languages"],
              ["CNN + LSTM on spectrograms (proposed model)", "Trained and cross-validated. Weaker than the ML models and poor on unseen speakers (Section 7).", "Delivered, with caveats"],
          ], [5.2, 8.6, 3.2])]

# ------------------------------------------------------------------ 3
story += [PageBreak(), H1("3. Related work"),
          P("The synopsis surveys five recent studies. They agree that voice carries useful signal for Parkinson's detection, and they leave similar gaps."),
          table([
              ["Study", "Approach", "Finding", "Gap this project addresses"],
              ["Malekroodi et al., 2025", "Systematic review of SVM, CNN, RNN on voice", "Deep learning generally beats traditional methods; datasets are imbalanced", "No standard datasets or evaluation; real-time systems needed"],
              ["Swain et al., 2024", "KNN, SVM, CNN, LDA on voice data", "KNN highest accuracy; voice is reliable and cheap", "Little real-time work; limited dataset size"],
              ["Iyer et al., 2023", "CNN (Inception V3) on telephone recordings", "Remote collection works for early, non-invasive diagnosis", "Needs diverse datasets; real time not explored"],
              ["Suppa et al., 2022", "SVM on voice analysis", "Separates healthy from affected; tracks L-Dopa effect", "Traditional ML only; no real-time analysis"],
              ["Alzubaidi et al., 2021", "Scoping review of neural networks", "Deep learning improves feature extraction and diagnosis", "Mostly research stage; few real-world systems"],
          ], [3.1, 4.0, 5.0, 4.9]),
          Spacer(1, 8),
          P("<b>What this project adds.</b> Three things go beyond the surveyed work. First, all headline numbers use <i>speaker-independent</i> validation. Second, the models "
            "were tested across two separate corpora and on 40 further unseen healthy speakers, which exposed a recording-setup problem that ordinary cross-validation hides. "
            "Third, the models are packaged as a working real-time and file-upload application.")]

# ------------------------------------------------------------------ 4
story += [PageBreak(), H1("4. Datasets"),
          P("Only openly available, free data was used. Two raw-audio corpora form the training set; a third provides an external check; and one tabular dataset "
            "gives a separate benchmark."),
          table([
              ["Dataset", "Content", "Used for", "Licence / access"],
              ["Italian Parkinson's Voice and Speech (Dimauro and Girardi, 2019)", "65 speakers recorded in a controlled setting: 28 PD, 22 elderly healthy, 15 young healthy. Vowels a, e, i, o, u, syllables, two reading tasks.", "Training and validation (young controls excluded)", "CC BY 4.0. IEEE DataPort; open copy on Hugging Face"],
              ["MDVR-KCL smartphone recordings (King's College London)", "39 speakers on a smartphone: 17 PD and 22 healthy. Text reading and spontaneous dialogue.", "Training and validation", "Open; the Hugging Face copy used is tagged MIT. Original on Zenodo"],
              ["LibriSpeech test-clean", "40 healthy English audiobook speakers; 240 files (6 per speaker) used.", "External false-alarm check only. Never trained on", "CC BY 4.0; openslr.org/12"],
              ["UCI Parkinson's Disease Classification (Sakar et al.)", "756 recordings of 252 subjects, 750+ precomputed features.", "Tabular benchmark of the five ML models", "UCI repository, open"],
          ], [4.4, 6.0, 3.4, 3.2]),
          Spacer(1, 6),
          fig("fig_data.png", 15.2, "Figure 1. Speakers and 3-second windows per corpus after cleaning (89 speakers, 8,655 windows)."),
          H2("Decisions about the data"),
          bullets([
              "<b>Young healthy controls removed (15 speakers).</b> They are decades younger than the PD group, so separating them from PD mostly measures age, which would flatter the accuracy.",
              "<b>LibriSpeech not used for training.</b> All PD audio comes from other sources. Adding audiobook speakers as healthy examples would let the model learn "
              "“audiobook recording = healthy”, inflating scores without any real benefit. It is used only as an unseen check.",
              "<b>Unique speaker IDs.</b> Two different Italian patients share the name “Roberto R” in different sub-folders. Speaker IDs are built from the folder path, giving 28 PD speakers, not 24.",
              "<b>Unused downloads.</b> UCI sets 174, 301, 489 and 189 were downloaded but are not part of the final models (small, different tasks, or a regression target). NeuroVoz (Spanish, 108 speakers) "
              "and mPower could not be downloaded in this environment.",
              "<b>Volume.</b> About 7.9 hours of audio from the 89 speakers; 8,655 windows; between 8 and 183 windows per speaker (median 94). Reading tasks make up 56% of windows (text 45%, phrases 11%), dialogue 13% and sustained vowels 31%.",
          ])]

# ------------------------------------------------------------------ 5
story += [PageBreak(), H1("5. Methodology"),
          fig("fig_pipeline.png", 16.8, "Figure 2. End-to-end processing: input, pre-processing, windowing, three feature views, models and the final score."),
          H2("5.1 Pre-processing and windowing"),
          P("Audio is converted to mono, resampled to 16 kHz and peak-normalised once per file. It is cut into 3-second windows with a 1.5-second hop. A window is kept only when "
            "at least half of its 25-ms frames are above a silence threshold; pauses and silence are skipped. Recordings shorter than 3 s are zero-padded. "
            "The same code runs for training, file upload and the live microphone, so the model always sees identical inputs."),
          H2("5.2 Features"),
          P("Three views are computed for every window:"),
          bullets([
              "<b>Voice-quality and variability features (tabular).</b> Using Praat (through Parselmouth): fundamental frequency (F0) statistics, voiced ratio, four jitter and six shimmer measures, "
              "harmonics-to-noise ratio and the first three formants. Using librosa: 20 MFCCs and their deltas, spectral centroid, bandwidth, roll-off, flatness, zero-crossing rate, RMS energy and 7-band spectral contrast, each summarised by mean and standard deviation. This gives 125 candidate features.",
              "<b>Log-mel spectrogram</b> (64 mel bands x 94 frames) for the CNN.",
              "<b>MFCC + delta sequence</b> (40 coefficients x 94 frames) for the LSTM.",
          ]),
          H2("5.3 The five machine-learning models"),
          table([
              ["Model", "Configuration"],
              ["SVM", "RBF kernel, C = 3, gamma = scale, probability outputs, balanced class weights; median imputation and standardisation"],
              ["Random Forest", "400 trees, min. 3 samples per leaf, sqrt features per split, balanced class weights"],
              ["KNN", "k = 25, distance-weighted; median imputation and standardisation"],
              ["LDA", "Least-squares solver with automatic shrinkage; median imputation and standardisation"],
              ["XGBoost", "400 trees, depth 4, learning rate 0.05, row subsample 0.8, column subsample 0.5"],
          ], [3.2, 13.8]),
          Spacer(1, 4),
          P("The “ensemble” is the plain average of the model probabilities. The synopsis names SVM, Random Forest, KNN and LDA; XGBoost was added as the fifth model. If the supervisor specified a different fifth model, it can be swapped in with one line in <b>make_models()</b> in train_ml.py."),
          H2("5.4 The deep models"),
          bullets([
              "<b>CNN:</b> four convolution blocks (16, 32, 64, 64 filters; each with batch-norm, ReLU, 2x2 max-pooling), global average pooling, dropout 0.4, one output unit.",
              "<b>BiLSTM:</b> two bidirectional LSTM layers (64 hidden units), mean and max pooling over time, dropout, one output unit.",
              "<b>Training:</b> AdamW (weight decay 0.01) with a one-cycle learning-rate schedule (peak 3e-3), 30 epochs, batch 64, class-weighted loss, gradient clipping. "
              "Augmentation: Gaussian noise, random frequency and time masks (SpecAugment), and time shifts for the CNN. The best epoch is chosen on held-out <i>training</i> speakers, never on the test fold. "
              "Training ran on an NVIDIA RTX 3050 GPU: one CNN fold took 36 s against 285 s on the CPU.",
          ]),
          H2("5.5 Validation protocol"),
          bullets([
              "<b>Speaker-independent 5-fold cross-validation</b> (stratified by class and corpus, fixed seed 42). All windows of a speaker stay in one fold. All models use the same folds.",
              "<b>Window to speaker aggregation.</b> Window probabilities are averaged per speaker. The speaker-level score is the headline number because it matches how the app is used.",
              "<b>Cross-corpus test.</b> Train on one corpus, test on the other, in both directions.",
              "<b>External false-alarm test.</b> Final models are run on 40 unseen healthy LibriSpeech speakers; any “PD” verdict is a false alarm.",
              "<b>Metrics.</b> Accuracy, balanced accuracy, AUC, F1, sensitivity (PD correctly found) and specificity (healthy correctly cleared).",
          ])]

# ------------------------------------------------------------------ 6
rows = [["Model", "Speaker acc.", "Sensitivity", "Specificity", "AUC", "Window acc."]]
for m in order:
    rows.append([nice.get(m, m), pc(spk.loc[m, "acc"]), pc(spk.loc[m, "sens"]), pc(spk.loc[m, "spec"]), "%.3f" % spk.loc[m, "auc"], pc(wnd.loc[m, "acc"])])
urows = [["Model", "Subject acc.", "Balanced acc.", "Sensitivity", "Specificity", "AUC"]]
for m in ["SVM", "RandomForest", "KNN", "LDA", "XGBoost", "Ensemble"]:
    urows.append([nice.get(m, m), pc(uci.loc[m, "acc"]), pc(uci.loc[m, "bal_acc"]), pc(uci.loc[m, "sens"]), pc(uci.loc[m, "spec"]), "%.3f" % uci.loc[m, "auc"]])
story += [PageBreak(), H1("6. Results"),
          H2("6.1 Speaker-independent cross-validation"),
          P("Table 1 gives the main results. The speaker-level columns are computed over all 89 speakers (n = 89); the window-level column over 8,655 windows."),
          table(rows, [5.0, 2.5, 2.4, 2.4, 2.0, 2.7]),
          P("Table 1. Speaker-independent 5-fold cross-validation. Speaker-level columns average each speaker's window probabilities. “Ensemble” is the average of all five ML models; the live app uses the four most robust (Section 7).", "cap"),
          fig("fig_cv.png", 15.6, "Figure 3. Accuracy and AUC for each model. The five ML models and their ensemble are close; the CNN is clearly lower."),
          fig("fig_roc.png", 15.6, "Figure 4. Left: ROC curves at speaker level. Right: ensemble confusion matrix. All 44 healthy speakers were cleared; 40 of 45 PD speakers were found."),
          H2("6.2 Reading the results"),
          bullets([
              "The five ML models are statistically close: with 89 speakers, each speaker is worth about 1.1 points, so a difference of one or two points is within noise. A realistic range for the ensemble is roughly 88–98%.",
              "The ensemble makes no false alarms on healthy speakers in cross-validation but misses 5 of 45 PD speakers (sensitivity 88.9%). For screening, a missed case is the more costly error, so sensitivity is the number to improve with more data.",
              "Averaging windows into a speaker-level decision adds about 4–11 points for the ML models and 13 for the BiLSTM over single 3-second windows, which is why the app smooths over four windows.",
              "The BiLSTM reaches %s at speaker level but only %s per window; the CNN is lowest at %s." % (pc(spk.loc["LSTM", "acc"]), pc(wnd.loc["LSTM", "acc"]), pc(spk.loc["CNN", "acc"])),
          ]),
          H2("6.3 Independent tabular benchmark (UCI, 252 subjects)"),
          P("The same five models were run on the UCI Parkinson's Disease Classification table (756 recordings, three per subject, subject-independent folds). "
            "This dataset has pre-computed features and a different recording setup."),
          table(urows, [4.2, 2.6, 2.8, 2.6, 2.6, 2.2]),
          P("Table 2. UCI benchmark, subject level. XGBoost is best (85.3% accuracy, AUC 0.904). Specificity is low (about 28–53%): this benchmark is harder and class-imbalanced (3:1).", "cap")]

# ------------------------------------------------------------------ 7
cr = lambda col: (rb[rb.subset == "all (baseline)"][col].mean(), rb[rb.subset == "praat + dynamics (std features)"][col].mean())
sub = rb.groupby("subset").agg(nf=("n_feat", "first"), cv=("cv_bal_acc", "mean"), a=("italian->kcl_auc", "mean"), b=("kcl->italian_auc", "mean"), fa=("libri_false_alarm", "mean"))
srows = [["Feature set", "Features", "CV balanced acc.", "Italian to KCL AUC", "KCL to Italian AUC", "False alarms, unseen speakers"]]
for key, label in (("all (baseline)", "All features (baseline)"), ("praat voice-quality only", "Voice-quality measures only"), ("praat + dynamics (std features)", "Voice quality + variability (chosen)")):
    r = sub.loc[key]
    srows.append([label, int(r.nf), pc(r.cv), "%.2f" % r.a, "%.2f" % r.b, pc(r.fa)])
story += [PageBreak(), H1("7. Generalisation: the key finding"),
          callout("A model that is 93% accurate on new speakers recorded the same way can still fail completely on a new microphone. This was found by testing on a second corpus and on "
                  "40 unseen healthy speakers, and the feature set was changed in response.", RED, "In one sentence"),
          Spacer(1, 6),
          H2("7.1 The problem"),
          P("The first models used all 125 features and scored about 93% in cross-validation. Two further tests then revealed a problem:"),
          bullets([
              "<b>Cross-corpus:</b> trained on the Italian studio recordings and tested on the KCL smartphone recordings, the models were at chance (mean AUC 0.46). In the other direction the mean AUC was 0.69.",
              "<b>Unseen healthy speakers:</b> on 40 LibriSpeech speakers about half (mean 49.5%) were wrongly flagged as Parkinson's.",
          ]),
          P("The cause is that features such as MFCC means and spectral levels describe the <i>recording chain</i> (microphone, room, compression) as much as the voice. "
            "Within one corpus, patient and control recordings share a setup, so the model can use these cues without penalty; on a new setup they mislead it."),
          H2("7.2 The fix"),
          P("Features were grouped and re-tested. Absolute spectral-level features (means of MFCCs, centroid, contrast and similar) were dropped. Kept were the Praat voice-quality measures "
            "(jitter, shimmer, HNR, F0 range, voiced ratio, formants) and the <i>variability</i> (standard deviation) of every spectral feature, 71 in total. For the CNN and LSTM, each window's per-frequency average was subtracted, "
            "which removes a fixed microphone response."),
          table(srows, [4.0, 1.6, 2.5, 2.6, 2.6, 3.7]),
          P("Table 3. Feature sets compared (mean over the five ML models). Voice quality alone was too little; adding variability gave the best balance.", "cap"),
          fig("fig_robust.png", 16.8, "Figure 5. Left and middle: cross-corpus AUC before and after (dashed line = chance). Right: false alarms on 40 unseen healthy speakers before and after, for all models."),
          H2("7.3 Outcome and remaining weaknesses"),
          bullets([
              "Cross-validation balanced accuracy is essentially unchanged (%s against %s), cross-corpus AUC rises to 0.72 and 0.82, and false alarms fall from 49.5%% to 10.5%%." % (pc(sub.loc["praat + dynamics (std features)", "cv"]), pc(sub.loc["all (baseline)", "cv"])),
              "<b>The CNN and LSTM did not benefit enough.</b> After the fix they still flag 52.5% and 45% of unseen healthy speakers, which is near chance. The likely reason is that with only 89 speakers, deep networks find recording-specific shortcuts that hand-designed features avoid.",
              "<b>Live-score ensemble.</b> LDA, XGBoost, Random Forest and SVM are averaged (cross-validated balanced accuracy 93.3%; 7.5% false alarms on unseen speakers). KNN is left out because it is the weakest across corpora. "
              "This selection was made after seeing the LibriSpeech check, so the 7.5% figure is slightly optimistic.",
              "<b>Cross-corpus accuracy is still imperfect.</b> At a fixed 0.5 threshold, models trained on one corpus mostly over-call PD on the other (AUC 0.5–0.9 but poor accuracy). The ranking is partly right, but the threshold does not transfer. "
              "Calibrating the threshold on a few samples from each new microphone would likely help.",
          ])]

# ------------------------------------------------------------------ 8
story += [PageBreak(), H1("8. The application"),
          P("The app runs locally (Flask backend, single-page web front end) and processes audio on the same computer; nothing is stored or sent elsewhere."),
          H2("8.1 How it works"),
          table([
              ["Component", "Description"],
              ["Live mode", "The browser captures the microphone with echo cancellation, noise suppression and auto-gain switched off, resamples to 16 kHz and keeps the latest 3 s. Every 1.5 s it posts the window to <b>/predict</b>. The score shown is the average of the last 4 windows."],
              ["Upload mode", "A file (WAV, MP3, M4A, FLAC, OGG, WebM) is decoded in the browser, converted to 16 kHz mono and sent to <b>/analyze</b>. The server normalises the file once, scores every valid 3 s window (first 90 s only) and returns the average, per-window scores and explanations. About 0.2 s per window on the development laptop (26 windows in 5.5 s)."],
              ["Quality checks", "Near-silent input and windows with too little speech are rejected with a clear message instead of a score."],
              ["Score and verdict", "Score = mean probability of LDA, XGBoost, Random Forest and SVM. Below 35%: low likelihood. 35–65%: uncertain. Above 65%: higher likelihood. CNN, LSTM and KNN scores are displayed as comparison bars."],
              ["Explanations", "For each window the five features that deviate most from the healthy average, in the direction of the PD average, are listed in plain language (for example “Pitch instability (jitter)”), with the value and which group it resembles."],
              ["Session report", "After a recording the summary shows average score, windows analysed and duration; a JSON report can be downloaded or the page printed."],
              ["Languages", "Interface in English, Hindi and Kannada. The Hindi and Kannada text was written for this project and should be reviewed by a native speaker."],
          ], [3.2, 13.8]),
          Spacer(1, 6),
          PageBreak(),
          KeepTogether([H2("8.2 Interface"),
          P("The page has a gradient gauge with a moving knob, a live heat-map spectrogram, a score-over-time chart, per-model bars, an explanation panel and a recording guide with two tasks "
            "(a held “aaah”, or reading a short passage aloud). It follows the system light or dark theme and works on phone-sized screens."),
          fig("ui_home.png", 15.4, "Figure 6. Home screen: hero, voice-test card with gauge, microphone and upload buttons.")])]
story += [PageBreak(),
          fig("ui_result.png", 11.6, "Figure 7. Results view. <b>Values shown are illustrative demo values, not a real recording.</b>"),
          bullets(["<b>Gauge and chip (top left):</b> the smoothed score, with a colour-coded verdict. The knob and arc move as new windows arrive.",
                   "<b>Spectrogram and timeline (top right):</b> the live spectrogram while recording; the score of each window over time against the 35% and 65% limits.",
                   "<b>Model scores:</b> solid bars are the four models counted in the score; grey bars (CNN, LSTM, KNN) are shown for comparison only.",
                   "<b>What influenced this window:</b> the voice features closest to the PD or the healthy group, in plain language, with their measured value.",
                   "<b>Session summary:</b> average score, windows analysed, duration, a one-line interpretation, and report download."])]

# ------------------------------------------------------------------ 9
story += [PageBreak(), H1("9. Limitations and ethical considerations"),
          bullets([
              "<b>Small and narrow data.</b> 89 speakers, two corpora, Italian and English speech, two recording setups. Estimates are uncertain by several points, and behaviour on other languages, accents, ages and microphones is unknown.",
              "<b>Age and sex are not fully controlled.</b> Controls were chosen to be elderly, but exact age and sex balance between PD and healthy groups was not verified. The model could partly be picking up age-related voice change.",
              "<b>Medication state.</b> Patients in the datasets were recorded on or off medication in ways not modelled here.",
              "<b>Severity and other conditions.</b> The models give a binary resemblance score, not a stage or severity; other voice conditions (for example laryngeal disorders, a cold, heavy accents) may also raise the score.",
              "<b>Live app untested at scale.</b> The server paths were tested with recordings, and the interface was checked visually. Real-world microphone accuracy has not been measured.",
              "<b>In-sample demonstrations.</b> The final models are trained on all 89 speakers, so demonstrating the app on those speakers' recordings gives optimistic scores. A fair demonstration needs recordings of new people.",
              "<b>Not a diagnosis.</b> The tool must be presented as a screening aid. Any concern should be referred to a neurologist. A high or low score must never be used to start or stop treatment.",
              "<b>Privacy.</b> Voice is personal data. The app keeps audio on the local machine; any future cloud version would need consent, encryption and clear retention rules.",
          ]),
          H1("10. Future work"),
          bullets([
              "Add NeuroVoz (108 Spanish speakers) and mPower (thousands of smartphone recordings) to enlarge and diversify the data. Both need a manual download or approval.",
              "Collect a small local dataset (with ethical approval) in the target language and on the target microphones, and calibrate the decision threshold per device.",
              "Match age and sex between groups and report results by task (sustained vowel versus reading).",
              "Try pretrained speech encoders (for example self-supervised audio models) which may transfer better than networks trained from scratch on 89 speakers.",
              "Add proper explainability (SHAP) and a calibrated probability, and test the live path with new volunteers.",
              "Package the app as an installable program or mobile app for real-world pilots.",
          ])]

# ------------------------------------------------------------------ 11
tree = """Parkison's Disease/
  datasets/            downloaded data (UCI sets, Italian PVS audio, MDVR-KCL audio, LibriSpeech test-clean)
  src/
    manifest.py        lists every recording with label, speaker, corpus and task
    features.py        windowing, Praat + librosa features, log-mel, MFCC sequence, channel normalisation
    extract.py         builds data_processed/ (tab.npy, mel.npy, mfcc.npy, windows_meta.csv)
    train_ml.py        5 ML models, speaker-independent CV, cross-corpus test, saves final models
    train_dl.py        CNN and BiLSTM (python train_dl.py cnn | lstm)
    train_uci.py       UCI 470 benchmark
    eval_external.py   LibriSpeech false-alarm check
    experiment_robust.py  feature-subset experiment (Section 7)
  app/
    server.py          Flask API: /predict, /analyze, /models
    static/index.html  the web interface
  models/              trained models (*.joblib, cnn.pt, lstm.pt, config.json)
  results/             all result tables (CSV)
  docs/                this report and its figures
  run_training.sh      CNN, LSTM and external check in sequence"""
story += [PageBreak(), H1("11. Reproducibility"),
          H2("11.1 Project layout"), Preformatted(tree, ParagraphStyle("code", fontName="Courier", fontSize=7.6, leading=10.2, textColor=INK, backColor=TINT, borderPadding=7, leftIndent=4)),
          Spacer(1, 10),
          H2("11.2 Environment"),
          bullets(["Windows 11, Python 3.14. A separate virtual environment (<b>.venv_gpu</b>) holds PyTorch 2.14 with CUDA 12.6 for the NVIDIA RTX 3050 laptop GPU (4 GB).",
                   "Libraries: scikit-learn 1.8, XGBoost 3.3, librosa 1.0, praat-parselmouth 0.4.7, pandas, NumPy, Flask 3.1, ReportLab (this report)."]),
          H2("11.3 Commands"),
          Preformatted("""# 1. build features (one time, about 3 minutes)
python src/extract.py
# 2. train and evaluate
python src/train_ml.py
.venv_gpu/Scripts/python.exe src/train_dl.py cnn
.venv_gpu/Scripts/python.exe src/train_dl.py lstm
.venv_gpu/Scripts/python.exe src/eval_external.py
# 3. run the app, then open http://127.0.0.1:5000
.venv_gpu/Scripts/python.exe app/server.py""", ParagraphStyle("code2", fontName="Courier", fontSize=8, leading=11, textColor=INK, backColor=TINT, borderPadding=7, leftIndent=4)),
          Spacer(1, 10),
          P("All splits use random seed 42 and the same speaker-to-fold map (<b>results/folds.csv</b>), so the tables in this report can be regenerated exactly from the saved CSV files."),
          H1("12. Conclusion"),
          P("VoiceScreen shows that a short voice sample, a small set of interpretable voice features and standard machine-learning models can separate speakers with and without Parkinson's disease "
            "with %s accuracy on speakers never seen in training, and that this can be delivered as a real-time, easy-to-use web application with explanations. "
            "Equally important is what the project learned about evaluation: accuracy measured inside one corpus overstated real-world performance, and the improvement came from "
            "choosing features that describe the voice rather than the microphone. The deep models proposed in the synopsis were trained and evaluated but need far more data before they can be trusted. "
            "With larger, more varied recordings and local calibration, the same pipeline is a sound basis for a screening aid that could support, never replace, clinical assessment." % pc(spk.loc["Ensemble", "acc"]))]

# ------------------------------------------------------------------ appendices
story += [PageBreak(), H1("Appendix A. The 71 features used by the final ML models"),
          table([
              ["Group", "Count", "Features"],
              ["Voice quality (Praat)", "17", "F0 minimum and maximum, voiced ratio; jitter local, rap, ppq5, ddp; shimmer local, local-dB, apq3, apq5, apq11, dda; harmonics-to-noise ratio; formants F1, F2, F3"],
              ["Pitch variability", "1", "F0 standard deviation"],
              ["MFCC variability", "20", "Standard deviation over time of MFCC 1–20"],
              ["MFCC change variability", "20", "Standard deviation of the delta of MFCC 1–20"],
              ["Spectral shape variability", "6", "Standard deviation of centroid, bandwidth, roll-off, flatness, zero-crossing rate, RMS energy"],
              ["Spectral contrast variability", "7", "Standard deviation of the 7 contrast bands"],
          ], [4.2, 1.5, 11.3]),
          P("Dropped (54 features): the mean values of the MFCCs, their deltas, centroid, bandwidth, roll-off, flatness, zero-crossing rate, RMS and contrast, and mean F0, because they describe absolute levels that depend on the microphone.", "small"),
          Spacer(1, 10),
          H1("Appendix B. Data sources and links"),
          table([
              ["Dataset", "Link"],
              ["Italian Parkinson's Voice and Speech", "doi.org/10.21227/aw6b-tg17 (IEEE DataPort); open copy: huggingface.co/datasets/macwhinney/Italian_Parkinsons_Voice_and_Speech"],
              ["MDVR-KCL smartphone recordings", "zenodo.org/records/2867216; copy used: huggingface.co/datasets/Hahad14/Parkinsons_Disease_Speech"],
              ["LibriSpeech", "openslr.org/12"],
              ["UCI Parkinson's Disease Classification", "archive.ics.uci.edu/dataset/470"],
              ["UCI Parkinson's, multiple sound recordings, replicated features, telemonitoring", "archive.ics.uci.edu/dataset/174, /301, /489, /189 (downloaded, not used in final models)"],
              ["NeuroVoz (not obtained)", "doi.org/10.5281/zenodo.10777657; code: github.com/BYO-UPM/Neurovoz_Dababase"],
              ["mPower (not obtained)", "synapse.org/Synapse:syn4993293 (registration and data-use agreement required)"],
          ], [5.5, 11.5]),
          Spacer(1, 10),
          H1("Appendix C. References"),
          ]
refs = [
    "Malekroodi, H. S., et al. (2025). Voice-based Parkinson's detection using AI: a systematic review. (As cited in the project synopsis.)",
    "Swain, K. P., et al. (2024). Comparative study of ML models for voice-based Parkinson's detection. (As cited in the project synopsis.)",
    "Iyer, A., et al. (2023). CNN-based voice analysis for Parkinson's disease classification. (As cited in the project synopsis.)",
    "Suppa, A., et al. (2022). Machine learning analysis of voice for Parkinson's disease detection. (As cited in the project synopsis.)",
    "Alzubaidi, M. S., et al. (2021). Neural networks for Parkinson's disease detection: a scoping review. (As cited in the project synopsis.)",
    "Dimauro, G. and Girardi, F. (2019). Italian Parkinson's Voice and Speech. IEEE DataPort. doi:10.21227/aw6b-tg17.",
    "Dimauro, G., Di Nicola, V., Bevilacqua, V., Caivano, D. and Girardi, F. (2017). Assessment of speech intelligibility in Parkinson's disease using a speech-to-text system. IEEE Access, 5, 22199–22208.",
    "Jaeger, H., Trivedi, D. and Stadtschnitzer, M. (2019). Mobile device voice recordings at King's College London (MDVR-KCL) from both early and advanced Parkinson's disease patients and healthy controls. Zenodo.",
    "Sakar, C. O., et al. (2019). A comparative analysis of speech signal processing algorithms for Parkinson's disease classification and the use of the tunable Q-factor wavelet transform. Applied Soft Computing, 74, 255–263.",
    "Panayotov, V., Chen, G., Povey, D. and Khudanpur, S. (2015). LibriSpeech: an ASR corpus based on public domain audio books. ICASSP.",
    "Mendes-Laureano, J., et al. (2024). NeuroVoz: a Castillian Spanish corpus of parkinsonian speech. Scientific Data, 11, 1367.",
    "Boersma, P. and Weenink, D. Praat: doing phonetics by computer; Jadoul, Y., Thompson, B. and de Boer, B. (2018). Introducing Parselmouth: a Python interface to Praat. Journal of Phonetics, 71.",
    "McFee, B., et al. (2015). librosa: audio and music signal analysis in Python. SciPy.",
    "Pedregosa, F., et al. (2011). Scikit-learn: machine learning in Python. JMLR, 12. Chen, T. and Guestrin, C. (2016). XGBoost: a scalable tree boosting system. KDD. Paszke, A., et al. (2019). PyTorch. NeurIPS.",
]
story += [Paragraph("[%d] %s" % (i + 1, r), S["ref"]) for i, r in enumerate(refs)]
story += [Spacer(1, 6), P("Citations marked “as cited in the project synopsis” are listed as they appear there. The dataset, software and other citations were written from the standard references and should be checked against the originals (authors, years, page numbers) before submission.", "small")]

# ------------------------------------------------------------------ build
doc = Doc(str(OUT), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=2.2 * cm,
          title="VoiceScreen: AI-based real-time voice analysis for early detection of Parkinson's disease", author="Project report")
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
doc.addPageTemplates([PageTemplate(id="cover", frames=[frame], onPage=cover, autoNextPageTemplate="body"), PageTemplate(id="body", frames=[frame], onPage=footer)])
doc.multiBuild(story)
print("wrote", OUT)
