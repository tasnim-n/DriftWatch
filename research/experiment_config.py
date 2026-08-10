from __future__ import annotations

from dataclasses import dataclass

from research.baselines import BASELINE_RULES


VALID_SPLIT_STRATEGIES = {"preserved_phase3b_assignments", "chronological"}


@dataclass(frozen=True)
class ExperimentConfig:
    experiment_id: str
    dataset_version: str
    feature_set: str
    split_strategy: str = "preserved_phase3b_assignments"
    seed: int = 1337

    def validate(self) -> None:
        if not self.experiment_id.strip():
            raise ValueError("experiment_id is required")
        if not self.dataset_version.strip():
            raise ValueError("dataset_version is required")
        if self.feature_set not in BASELINE_RULES:
            raise ValueError(f"unknown feature_set: {self.feature_set}")
        if self.split_strategy not in VALID_SPLIT_STRATEGIES:
            raise ValueError(f"unknown split_strategy: {self.split_strategy}")
        if self.seed < 0:
            raise ValueError("seed must be non-negative")
