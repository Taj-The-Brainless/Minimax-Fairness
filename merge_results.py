"""Merge result folders (for example from parallel shards) into one folder for final_analysis.py.

    python merge_results.py --out results/merged results/final results/final_big0 results/final_big1

Rows of the same variant (and eval/depth) that appear in several folders are kept once (first folder wins).
Only merge folders that were produced with the same settings (--games, --random-opening, --node-limit).
Stop the collection processes first, or copy the folders, so no file is half-written while reading.
"""
import argparse
import os

import pandas as pd

KEYS = {"exact": ["variant_id"], "depth": ["variant_id", "eval", "depth"],
        "dstar": ["variant_id", "eval"], "matches": ["variant_id", "eval", "depth"]}

p = argparse.ArgumentParser()
p.add_argument("--out", required=True)
p.add_argument("dirs", nargs="+", help="result folders, highest priority first")
args = p.parse_args()
os.makedirs(args.out, exist_ok=True)

for name, keys in KEYS.items():
    frames = []
    for d in args.dirs:
        path = os.path.join(d, f"{name}.csv")
        if os.path.exists(path):
            try:
                frames.append(pd.read_csv(path))
            except pd.errors.EmptyDataError:
                print(f"note: {path} is empty, skipped")
        else:
            print(f"note: {path} not found, skipped")
    if not frames:
        continue
    df = pd.concat(frames, ignore_index=True)
    keys = [k for k in keys if k in df.columns]
    before = len(df)
    df = df.drop_duplicates(subset=keys, keep="first")
    df.to_csv(os.path.join(args.out, f"{name}.csv"), index=False)
    print(f"{name}: {before} rows -> {len(df)} rows after removing duplicates")
print("merged into", args.out, "- next: python final_analysis.py --dir", args.out)
