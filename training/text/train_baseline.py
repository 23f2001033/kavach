"""TF-IDF + Logistic Regression baseline for the Kavach social-engineering text classifier.

Features: word 1-2 grams + char 3-5 grams, combined via FeatureUnion, feeding a single
LogisticRegression. C is tuned on val.jsonl over a small grid, then the tuned model is
evaluated on test.jsonl (overall + split by source, to check for template memorization)
and on test_real_youtube.jsonl (20 real scam calls, the honest real-world probe).

Run: python training/text/train_baseline.py   (from the repo root; CPU, <1 minute)
"""

import json
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import FeatureUnion

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"
METRICS_PATH = Path(__file__).resolve().parent / "baseline_metrics.json"

# Small grid; balanced classes so we tune for val F1.
C_GRID = [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0]


def load_jsonl(path):
    """Load a JSONL file of unified-schema records into a list of dicts."""
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def build_vectorizer():
    """Word 1-2 grams + char 3-5 grams, combined into one feature matrix via FeatureUnion."""
    return FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=30000, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char", ngram_range=(3, 5), min_df=2, max_features=30000, sublinear_tf=True)),
    ])


def compute_metrics(y_true, y_pred, y_prob):
    """Accuracy/precision/recall/F1/ROC-AUC; ROC-AUC is None if the subset is single-class."""
    auc = roc_auc_score(y_true, y_prob) if len(set(y_true)) > 1 else None
    return {
        "n": len(y_true),
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": auc,
    }


def tune_c(X_train, y_train, X_val, y_val):
    """Fit LogisticRegression for each C in C_GRID, pick the one with best val F1."""
    tuning_log = []
    best_c, best_f1, best_clf = None, -1.0, None
    for c in C_GRID:
        clf = LogisticRegression(C=c, max_iter=2000, class_weight="balanced")
        clf.fit(X_train, y_train)
        val_pred = clf.predict(X_val)
        val_prob = clf.predict_proba(X_val)[:, 1]
        val_metrics = compute_metrics(y_val, val_pred, val_prob)
        tuning_log.append({"C": c, **val_metrics})
        print(f"  C={c:<6} val_acc={val_metrics['accuracy']:.4f} val_f1={val_metrics['f1']:.4f} "
              f"val_auc={val_metrics['roc_auc']:.4f}")
        if val_metrics["f1"] > best_f1:
            best_f1, best_c, best_clf = val_metrics["f1"], c, clf
    return best_c, best_clf, tuning_log


def test_breakdown_by_source(test_records, y_test, test_pred, test_prob):
    """Split test metrics by source group: kavach-india-synth vs. other (BothBosu) synthetic
    sources, so we can see whether the model is just memorizing our own templates rather
    than generalizing to independently-written scam/legit dialogue."""
    groups = {
        "kavach-india-synth": [i for i, r in enumerate(test_records) if r["source"] == "kavach-india-synth"],
        "other-synthetic-sources": [i for i, r in enumerate(test_records) if r["source"] != "kavach-india-synth"],
    }
    breakdown = {}
    for name, idx in groups.items():
        if not idx:
            continue
        breakdown[name] = compute_metrics(
            [y_test[i] for i in idx],
            [test_pred[i] for i in idx],
            [test_prob[i] for i in idx],
        )
    return breakdown


def top_word_features(vectorizer, clf, k=25):
    """Top-k highest-weight scam-indicative and legit-indicative word (not char) n-grams."""
    word_vec = dict(vectorizer.transformer_list)["word"]
    word_names = word_vec.get_feature_names_out()
    n_word = len(word_names)
    word_coefs = clf.coef_[0][:n_word]
    order = np.argsort(word_coefs)
    legit = [(word_names[i], float(word_coefs[i])) for i in order[:k]]
    scam = [(word_names[i], float(word_coefs[i])) for i in order[::-1][:k]]
    return scam, legit


def main():
    t0 = time.time()
    train = load_jsonl(DATA_DIR / "train.jsonl")
    val = load_jsonl(DATA_DIR / "val.jsonl")
    test = load_jsonl(DATA_DIR / "test.jsonl")
    youtube = load_jsonl(DATA_DIR / "test_real_youtube.jsonl")
    print(f"train={len(train)} val={len(val)} test={len(test)} youtube_real={len(youtube)}")

    y_train = [r["label"] for r in train]
    y_val = [r["label"] for r in val]
    y_test = [r["label"] for r in test]
    y_yt = [r["label"] for r in youtube]

    vectorizer = build_vectorizer()
    print("fitting TF-IDF (word 1-2 grams + char 3-5 grams) on train ...")
    X_train = vectorizer.fit_transform([r["text"] for r in train])
    X_val = vectorizer.transform([r["text"] for r in val])
    X_test = vectorizer.transform([r["text"] for r in test])
    X_yt = vectorizer.transform([r["text"] for r in youtube])
    print(f"feature matrix: {X_train.shape[1]} dims")

    print("tuning C on val.jsonl ...")
    best_c, clf, tuning_log = tune_c(X_train, y_train, X_val, y_val)
    print(f"best C = {best_c}")

    test_pred = clf.predict(X_test)
    test_prob = clf.predict_proba(X_test)[:, 1]
    test_metrics = compute_metrics(y_test, test_pred, test_prob)
    test_by_source = test_breakdown_by_source(test, y_test, test_pred, test_prob)

    yt_prob = clf.predict_proba(X_yt)[:, 1]
    yt_pred = (yt_prob >= 0.5).astype(int)
    yt_flagged = int(yt_pred.sum())
    yt_records = [
        {"id": r["id"], "scam_type": r["scam_type"], "prob_scam": float(p), "flagged": bool(p >= 0.5)}
        for r, p in zip(youtube, yt_prob)
    ]

    scam_features, legit_features = top_word_features(vectorizer, clf, k=25)

    word_vec = dict(vectorizer.transformer_list)["word"]
    char_vec = dict(vectorizer.transformer_list)["char"]
    metrics = {
        "model": "tfidf(word_1-2gram + char_3-5gram) + LogisticRegression",
        "best_C": best_c,
        "c_grid_tuning_on_val": tuning_log,
        "feature_dims": {
            "word": len(word_vec.get_feature_names_out()),
            "char": len(char_vec.get_feature_names_out()),
            "total": X_train.shape[1],
        },
        "n_train": len(train),
        "n_val": len(val),
        "n_test": len(test),
        "test": test_metrics,
        "test_by_source": test_by_source,
        "youtube_real_probe": {
            "n": len(youtube),
            "flagged_at_0.5": yt_flagged,
            "recall_at_0.5": yt_flagged / len(youtube) if youtube else None,
            "records": yt_records,
        },
        "top_features": {
            "scam_indicative_word_ngrams": scam_features,
            "legit_indicative_word_ngrams": legit_features,
        },
        "runtime_seconds": round(time.time() - t0, 1),
    }

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / "text_baseline.joblib"
    joblib.dump({"vectorizer": vectorizer, "clf": clf, "best_C": best_c}, model_path)

    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    # ---- readable summary ----
    print("\n=== TEST METRICS (test.jsonl) ===")
    for k, v in test_metrics.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    print("\n=== TEST BY SOURCE (memorization check) ===")
    for name, m in test_by_source.items():
        auc = f"{m['roc_auc']:.4f}" if m["roc_auc"] is not None else "n/a"
        print(f"  {name} (n={m['n']}): acc={m['accuracy']:.4f} prec={m['precision']:.4f} "
              f"rec={m['recall']:.4f} f1={m['f1']:.4f} auc={auc}")

    print(f"\n=== YOUTUBE REAL PROBE: {yt_flagged}/{len(youtube)} flagged at threshold 0.5 ===")
    for rec in yt_records:
        flag = "FLAGGED" if rec["flagged"] else "missed "
        print(f"  [{flag}] {rec['id']:<45} scam_type={rec['scam_type']:<20} prob={rec['prob_scam']:.3f}")

    print("\n=== TOP 25 SCAM-INDICATIVE WORD FEATURES ===")
    for w, c in scam_features:
        print(f"  {w:<30} {c:+.3f}")

    print("\n=== TOP 25 LEGIT-INDICATIVE WORD FEATURES ===")
    for w, c in legit_features:
        print(f"  {w:<30} {c:+.3f}")

    print(f"\nsaved model -> {model_path}")
    print(f"saved metrics -> {METRICS_PATH}")
    print(f"total runtime: {metrics['runtime_seconds']}s")


if __name__ == "__main__":
    main()
