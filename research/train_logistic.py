from __future__ import annotations

from typing import Dict, List, Sequence

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from research.loaders import label_to_binary, split_metadata_features
from research.metrics import binary_classification_metrics
from research.readiness import dataset_readiness_report


def train_logistic_regression(rows: Sequence[Dict[str, str]], feature_names: Sequence[str], seed: int = 1337) -> Dict:
    readiness = dataset_readiness_report(rows)
    if not readiness["ml_training_permitted"]:
        return {
            "status": "blocked_dataset_readiness_gate_failed",
            "ml_block_reasons": readiness["ml_block_reasons"],
        }

    train_rows = [row for row in rows if row.get("split") == "train"]
    test_rows = [row for row in rows if row.get("split") == "test"]
    x_train, y_train = _matrix(train_rows, feature_names)
    x_test, y_test = _matrix(test_rows, feature_names)

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(max_iter=1000, random_state=seed)),
    ])
    model.fit(x_train, y_train)
    predictions = model.predict(x_test).tolist()
    coefficients = model.named_steps["classifier"].coef_[0].tolist()

    return {
        "status": "trained",
        "model": model,
        "metrics": binary_classification_metrics(y_test, predictions),
        "coefficients": [
            {"feature": name, "coefficient": coefficients[index]}
            for index, name in enumerate(feature_names)
        ],
    }


def _matrix(rows: Sequence[Dict[str, str]], feature_names: Sequence[str]) -> tuple[List[List[float]], List[int]]:
    matrix: List[List[float]] = []
    labels: List[int] = []
    for row in rows:
        metadata, features = split_metadata_features(row)
        matrix.append([features.get(name, 0.0) for name in feature_names])
        labels.append(label_to_binary(metadata["label"]))
    return matrix, labels
