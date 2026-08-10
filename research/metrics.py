from __future__ import annotations

from typing import Dict, List, Sequence


def binary_confusion_matrix(y_true: Sequence[int], y_pred: Sequence[int]) -> Dict[str, int]:
    tp = sum(1 for truth, pred in zip(y_true, y_pred) if truth == 1 and pred == 1)
    tn = sum(1 for truth, pred in zip(y_true, y_pred) if truth == 0 and pred == 0)
    fp = sum(1 for truth, pred in zip(y_true, y_pred) if truth == 0 and pred == 1)
    fn = sum(1 for truth, pred in zip(y_true, y_pred) if truth == 1 and pred == 0)
    return {"tn": tn, "fp": fp, "fn": fn, "tp": tp}


def binary_classification_metrics(y_true: Sequence[int], y_pred: Sequence[int]) -> Dict[str, float | Dict[str, int]]:
    matrix = binary_confusion_matrix(y_true, y_pred)
    tp = matrix["tp"]
    tn = matrix["tn"]
    fp = matrix["fp"]
    fn = matrix["fn"]

    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    specificity = _safe_div(tn, tn + fp)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    fpr = _safe_div(fp, fp + tn)
    fnr = _safe_div(fn, fn + tp)
    balanced_accuracy = (recall + specificity) / 2 if (tp + fn) and (tn + fp) else 0.0
    false_alerts_per_100_benign = fpr * 100

    return {
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
        "balanced_accuracy": round(balanced_accuracy, 6),
        "false_positive_rate": round(fpr, 6),
        "false_negative_rate": round(fnr, 6),
        "false_alerts_per_100_benign": round(false_alerts_per_100_benign, 6),
        "confusion_matrix": matrix,
    }


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0
