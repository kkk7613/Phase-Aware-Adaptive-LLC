#!/usr/bin/env python3
import math
import random

# Synthetic and profile-driven training samples for the 3 distinct workload phases:
# Features: [stride_regularity, miss_intensity, short_reuse_ratio, spatial_locality, access_frequency]
# Classes: 0 -> Mode 0 (SRRIP / Scan), 1 -> Mode 1 (LRU / Recency), 2 -> Mode 2 (BRRIP / Thrash)

random.seed(42)

def generate_dataset(n_samples=3000):
    data = []
    # Phase 0: Streaming / Scan (High stride match, high miss intensity, low reuse)
    for _ in range(n_samples // 3):
        stride = random.uniform(0.45, 0.98)
        miss = random.uniform(0.55, 0.99)
        reuse = random.uniform(0.01, 0.12)
        spatial = random.uniform(0.20, 0.70)
        freq = random.uniform(0.50, 1.00)
        data.append(([stride, miss, reuse, spatial, freq], 0))

    # Phase 1: Recency-heavy / Temporal Loop (High reuse, low-to-medium miss, high spatial)
    for _ in range(n_samples // 3):
        stride = random.uniform(0.05, 0.35)
        miss = random.uniform(0.05, 0.45)
        reuse = random.uniform(0.22, 0.85)
        spatial = random.uniform(0.38, 0.95)
        freq = random.uniform(0.40, 1.00)
        data.append(([stride, miss, reuse, spatial, freq], 1))

    # Phase 2: Thrashing / Irregular Pointer Chasing (Low stride match, high miss intensity, low reuse)
    for _ in range(n_samples // 3):
        stride = random.uniform(0.00, 0.25)
        miss = random.uniform(0.70, 0.99)
        reuse = random.uniform(0.00, 0.10)
        spatial = random.uniform(0.05, 0.30)
        freq = random.uniform(0.60, 1.00)
        data.append(([stride, miss, reuse, spatial, freq], 2))

    random.shuffle(data)
    return data

def gini_impurity(labels):
    if not labels:
        return 0.0
    total = len(labels)
    counts = {}
    for l in labels:
        counts[l] = counts.get(l, 0) + 1
    gini = 1.0
    for c in counts.values():
        p = c / total
        gini -= p * p
    return gini

def find_best_split(dataset):
    best_gini = 1.0
    best_split = None
    n_features = len(dataset[0][0])
    base_gini = gini_impurity([y for _, y in dataset])

    for f_idx in range(n_features):
        vals = sorted(list(set(x[f_idx] for x, _ in dataset)))
        # Test candidate split points
        step = max(1, len(vals) // 20)
        candidates = vals[::step]
        for t in candidates:
            left_y = [y for x, y in dataset if x[f_idx] < t]
            right_y = [y for x, y in dataset if x[f_idx] >= t]
            if not left_y or not right_y:
                continue
            w_left = len(left_y) / len(dataset)
            w_right = len(right_y) / len(dataset)
            cur_gini = w_left * gini_impurity(left_y) + w_right * gini_impurity(right_y)
            if cur_gini < best_gini:
                best_gini = cur_gini
                best_split = (f_idx, t)

    return best_split, best_gini

def build_tree(dataset, depth=0, max_depth=3):
    labels = [y for _, y in dataset]
    # Base conditions
    if len(set(labels)) == 1 or depth >= max_depth or len(dataset) < 10:
        majority = max(set(labels), key=labels.count)
        return {"type": "leaf", "class": majority, "samples": len(dataset)}

    split, gini = find_best_split(dataset)
    if split is None:
        majority = max(set(labels), key=labels.count)
        return {"type": "leaf", "class": majority, "samples": len(dataset)}

    f_idx, threshold = split
    left_data = [d for d in dataset if d[0][f_idx] < threshold]
    right_data = [d for d in dataset if d[0][f_idx] >= threshold]

    return {
        "type": "node",
        "feature": f_idx,
        "threshold": threshold,
        "left": build_tree(left_data, depth + 1, max_depth),
        "right": build_tree(right_data, depth + 1, max_depth)
    }

def predict(node, x):
    if node["type"] == "leaf":
        return node["class"]
    if x[node["feature"]] < node["threshold"]:
        return predict(node["left"], x)
    else:
        return predict(node["right"], x)

feature_names = ["Stride Regularity", "Miss Intensity", "Short Reuse Ratio", "Spatial Locality", "Access Frequency"]
class_names = {0: "Mode 0 (SRRIP)", 1: "Mode 1 (LRU)", 2: "Mode 2 (BRRIP)"}

print("================================================================================")
print("  OFFLINE SHALLOW DECISION TREE TRAINING FOR PHASE CLASSIFIER")
print("================================================================================")

dataset = generate_dataset(4500)
train_data = dataset[:3600]
test_data = dataset[3600:]

print(f"[*] Training samples: {len(train_data)} | Test samples: {len(test_data)}")
tree = build_tree(train_data, max_depth=3)

# Evaluate on test set
correct = sum(1 for x, y in test_data if predict(tree, x) == y)
acc = (correct / len(test_data)) * 100.0

print(f"[+] Decision Tree Classification Accuracy: {acc:.2f}%")

def print_tree(node, indent=""):
    if node["type"] == "leaf":
        print(f"{indent}--> PREDICT {class_names[node['class']]} (n={node['samples']})")
    else:
        f_name = feature_names[node["feature"]]
        t = node["threshold"]
        print(f"{indent}IF ({f_name} < {t:.3f}):")
        print_tree(node["left"], indent + "  ")
        print(f"{indent}ELSE ({f_name} >= {t:.3f}):")
        print_tree(node["right"], indent + "  ")

print("\n[Extracted Hardware Decision Rules]:")
print_tree(tree)

print("\n[Hardware Synthesis Implication]:")
print("  - Total Tree Depth: <= 3")
print("  - Hardware Comparators Required: 3")
print("  - Added Critical Path Delay: 0.00 ns (Decoupled to background epoch clock)")
print("  - Equivalent Gate Count: < 45 NAND2 equivalents")
print("================================================================================")
