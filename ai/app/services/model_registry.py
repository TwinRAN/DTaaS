import json
import pickle
from pathlib import Path


def load_models(models_dir: str) -> dict[str, dict]:
    """
    Scan models_dir recursively, load each JSON as metadata and the matching
    pickle (same folder, file name = tag + '.pkl'), and return:

      { model_tag: {"metadata": <json_dict>, "model": <pickle_object>}, ... }
    """
    base = Path(models_dir).resolve()
    results: dict[str, dict] = {}

    if not base.exists():
        return results

    for json_path in base.rglob("*.json"):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            tag = metadata.get("tag") or metadata.get("model_tag")
            if not tag:
                continue

            pkl_path = json_path.parent / f"{tag}.pkl"
            if not pkl_path.exists():
                continue

            with open(pkl_path, "rb") as pf:
                model = pickle.load(pf)

            results[str(tag)] = {"metadata": metadata, "model": model}
        except Exception:
            # Silently skip problematic files
            continue

    return results
