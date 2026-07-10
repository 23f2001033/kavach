"""Assemble the unified Kavach scam/legit call-transcript corpus.

Pulls five BothBosu HuggingFace datasets plus our India-specific synthetic
generator, normalizes every record to the unified schema (schema.py), dedups,
stratifies into train/val/test, and writes JSONL + stats.json to
data/processed/. The 20 real YouTube scam calls are held out into their own
file and never enter train/val/test.

Run: python -m data_pipeline.build_corpus
"""

import json
import random
import re
import statistics
from collections import Counter
from pathlib import Path

from datasets import load_dataset

from data_pipeline.india_synth import generate as generate_india_synth
from data_pipeline.schema import BOTHBOSU_TYPE_MAP, CALLER_ALIASES, RECEIVER_ALIASES

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "processed"

# scam types mapped from BOTHBOSU_TYPE_MAP that are legitimately scam families
SCAM_MAPPED_TYPES = {"govt_impersonation", "tech_support", "refund_scam", "prize_scam"}
BENIGN_MAPPED_TYPES = {"delivery", "insurance", "telemarketing", "wrong_number", "appointment"}

_ALIAS_PATTERN = re.compile(
    r"\b(" + "|".join(sorted((CALLER_ALIASES | RECEIVER_ALIASES), key=len, reverse=True)) + r")\s*:",
    re.IGNORECASE,
)


def normalize_text(raw):
    """Map every speaker alias to Caller:/Receiver: and collapse whitespace."""
    def repl(m):
        word = m.group(1).lower()
        if word in CALLER_ALIASES:
            return "Caller:"
        if word in RECEIVER_ALIASES:
            return "Receiver:"
        return m.group(0)

    tagged = _ALIAS_PATTERN.sub(repl, raw)
    return re.sub(r"\s+", " ", tagged).strip()


def unify_scam_type(raw_type, label):
    """Map a BothBosu `type` tag (or None) + label into the unified taxonomy."""
    mapped = BOTHBOSU_TYPE_MAP.get(raw_type) if raw_type else None
    if label == 1:
        return mapped if mapped in SCAM_MAPPED_TYPES else "unknown_scam"
    return mapped if mapped in BENIGN_MAPPED_TYPES else "none"


def _rows(dataset_dict):
    """Yield (split, index, row-dict) across all splits of a HF DatasetDict, pooling every split."""
    for split in dataset_dict:
        for i, row in enumerate(dataset_dict[split]):
            yield split, i, row


def load_scam_dialogue():
    """BothBosu/scam-dialogue -- dialogue, type, label."""
    ds = load_dataset("BothBosu/scam-dialogue")
    records = []
    for split, i, row in _rows(ds):
        label = int(row["label"])
        records.append({
            "id": f"bothbosu-scam-dialogue-{split}-{i}",
            "source": "bothbosu-scam-dialogue",
            "text": normalize_text(row["dialogue"]),
            "label": label,
            "scam_type": unify_scam_type(row["type"], label),
            "origin": "synthetic",
        })
    return records


def load_multi_agent():
    """BothBosu/multi-agent-scam-conversation -- dialogue, personality, type, labels."""
    ds = load_dataset("BothBosu/multi-agent-scam-conversation")
    records = []
    for split, i, row in _rows(ds):
        label = int(row["labels"])
        records.append({
            "id": f"bothbosu-multi-agent-scam-conversation-{split}-{i}",
            "source": "bothbosu-multi-agent-scam-conversation",
            "text": normalize_text(row["dialogue"]),
            "label": label,
            "scam_type": unify_scam_type(row["type"], label),
            "origin": "synthetic",
        })
    return records


def load_single_agent():
    """BothBosu/single-agent-scam-conversations -- dialogue, type, labels."""
    ds = load_dataset("BothBosu/single-agent-scam-conversations")
    records = []
    for split, i, row in _rows(ds):
        label = int(row["labels"])
        records.append({
            "id": f"bothbosu-single-agent-scam-conversations-{split}-{i}",
            "source": "bothbosu-single-agent-scam-conversations",
            "text": normalize_text(row["dialogue"]),
            "label": label,
            "scam_type": unify_scam_type(row["type"], label),
            "origin": "synthetic",
        })
    return records


def load_scammer_conversation():
    """BothBosu/Scammer-Conversation -- conversation, label. No type column."""
    ds = load_dataset("BothBosu/Scammer-Conversation")
    records = []
    for split, i, row in _rows(ds):
        label = int(row["label"])
        records.append({
            "id": f"bothbosu-scammer-conversation-{split}-{i}",
            "source": "bothbosu-scammer-conversation",
            "text": normalize_text(row["conversation"]),
            "label": label,
            "scam_type": unify_scam_type(None, label),
            "origin": "synthetic",
        })
    return records


def load_youtube():
    """BothBosu/youtube-scam-conversations -- 20 REAL scam calls. Held out only."""
    ds = load_dataset("BothBosu/youtube-scam-conversations")
    records = []
    for split, i, row in _rows(ds):
        label = int(row["labels"])
        records.append({
            "id": f"bothbosu-youtube-scam-conversations-{split}-{i}",
            "source": "bothbosu-youtube-scam-conversations",
            "text": normalize_text(row["dialogue"]),
            "label": label,
            "scam_type": unify_scam_type(row["type"], label),
            "origin": "real",
        })
    return records


def dedup(records):
    """Exact-duplicate dedup on normalized text, keep first occurrence."""
    seen, kept, dropped = set(), [], 0
    for r in records:
        if r["text"] in seen:
            dropped += 1
            continue
        seen.add(r["text"])
        kept.append(r)
    return kept, dropped


def stratified_split(records, seed=42, ratios=(0.8, 0.1, 0.1)):
    """Split records into train/val/test stratified jointly on (label, source)."""
    keys = [f"{r['label']}|{r['source']}" for r in records]
    try:
        from sklearn.model_selection import train_test_split

        idx = list(range(len(records)))
        train_idx, temp_idx = train_test_split(
            idx, test_size=ratios[1] + ratios[2], random_state=seed,
            stratify=keys,
        )
        temp_keys = [keys[i] for i in temp_idx]
        val_idx, test_idx = train_test_split(
            temp_idx, test_size=ratios[2] / (ratios[1] + ratios[2]), random_state=seed,
            stratify=temp_keys,
        )
        train = [records[i] for i in train_idx]
        val = [records[i] for i in val_idx]
        test = [records[i] for i in test_idx]
        return train, val, test
    except ImportError:
        return _manual_stratified_split(records, keys, seed, ratios)


def _manual_stratified_split(records, keys, seed, ratios):
    """Deterministic manual fallback stratifier (used only if sklearn is unavailable)."""
    by_key = {}
    for r, k in zip(records, keys):
        by_key.setdefault(k, []).append(r)
    rng = random.Random(seed)
    train, val, test = [], [], []
    for k in sorted(by_key):
        group = by_key[k][:]
        rng.shuffle(group)
        n = len(group)
        n_train = round(n * ratios[0])
        n_val = round(n * ratios[1])
        train.extend(group[:n_train])
        val.extend(group[n_train:n_train + n_val])
        test.extend(group[n_train + n_val:])
    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)
    return train, val, test


def write_jsonl(records, path):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _length_stats(records):
    lengths = [len(r["text"].split()) for r in records]
    if not lengths:
        return {"mean": 0, "median": 0}
    return {"mean": round(statistics.mean(lengths), 2), "median": statistics.median(lengths)}


def file_stats(records):
    return {
        "count": len(records),
        "label_balance": dict(Counter(r["label"] for r in records)),
        "per_source": dict(Counter(r["source"] for r in records)),
        "per_scam_type": dict(Counter(r["scam_type"] for r in records)),
        "text_length_words": _length_stats(records),
    }


def sanity_check(files):
    """Assert schema invariants across all written files. Raises on violation."""
    required = {"id", "source", "text", "label", "scam_type", "origin"}
    for name, records in files.items():
        for r in records:
            missing = required - r.keys()
            assert not missing, f"{name}: record {r.get('id')} missing fields {missing}"
            assert r["label"] in (0, 1), f"{name}: bad label in {r['id']}"
            assert r["text"].strip(), f"{name}: empty text in {r['id']}"
            if name != "test_real_youtube.jsonl":
                assert "youtube" not in r["source"], f"{name}: youtube record {r['id']} leaked outside held-out file"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("loading BothBosu/scam-dialogue ...")
    scam_dialogue = load_scam_dialogue()
    print("loading BothBosu/multi-agent-scam-conversation ...")
    multi_agent = load_multi_agent()
    print("loading BothBosu/single-agent-scam-conversations ...")
    single_agent = load_single_agent()
    print("loading BothBosu/Scammer-Conversation ...")
    scammer_conv = load_scammer_conversation()
    print("loading BothBosu/youtube-scam-conversations (held-out only) ...")
    youtube = load_youtube()
    print("generating India-specific synthetic records ...")
    india_synth = generate_india_synth(n_per_scenario=120, seed=13)
    # india_synth records already match the unified schema, but pass text through
    # the same whitespace normalization for consistency (idempotent, no speaker
    # aliases to translate since they already use Caller:/Receiver:).
    for r in india_synth:
        r["text"] = normalize_text(r["text"])

    pool_raw = scam_dialogue + multi_agent + single_agent + scammer_conv + india_synth
    pool, pool_dropped = dedup(pool_raw)

    youtube_deduped, youtube_dropped = dedup(youtube)

    train, val, test = stratified_split(pool, seed=42)

    write_jsonl(train, OUT_DIR / "train.jsonl")
    write_jsonl(val, OUT_DIR / "val.jsonl")
    write_jsonl(test, OUT_DIR / "test.jsonl")
    write_jsonl(youtube_deduped, OUT_DIR / "test_real_youtube.jsonl")

    files = {
        "train.jsonl": train,
        "val.jsonl": val,
        "test.jsonl": test,
        "test_real_youtube.jsonl": youtube_deduped,
    }
    sanity_check(files)

    stats = {name: file_stats(records) for name, records in files.items()}
    stats["_meta"] = {
        "pool_size_before_dedup": len(pool_raw),
        "pool_duplicates_dropped": pool_dropped,
        "youtube_duplicates_dropped": youtube_dropped,
        "split_ratios": {"train": 0.8, "val": 0.1, "test": 0.1},
        "split_seed": 42,
    }
    with open(OUT_DIR / "stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print("\n=== corpus build complete ===")
    for name, s in stats.items():
        if name == "_meta":
            continue
        print(f"{name}: {s['count']} records, label balance {s['label_balance']}")
    print(f"duplicates dropped: pool={pool_dropped}, youtube={youtube_dropped}")
    print(f"wrote files to {OUT_DIR}")


if __name__ == "__main__":
    main()
