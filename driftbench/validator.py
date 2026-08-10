from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Sequence

from driftbench.labels import LABEL_ONTOLOGY, Label, is_valid_label
from driftbench.provenance import sha256_file
from driftbench.schema import DatasetPairRecord


ALLOWED_SPLITS = {"train", "validation", "test", "controlled_holdout", None}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}


@dataclass
class ValidationReport:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    record_count: int = 0


class DatasetValidator:
    """Validate DriftBench metadata without executing extension code."""

    @classmethod
    def validate_records(
        cls,
        records: Sequence[DatasetPairRecord],
        *,
        base_dir: str | Path = ".",
        validate_paths: bool = True,
        validate_hashes: bool = True,
    ) -> ValidationReport:
        report = ValidationReport(is_valid=True, record_count=len(records))
        seen_pair_ids = set()

        for index, record in enumerate(records):
            prefix = f"record[{index}] {record.pair_id or '<missing pair_id>'}"
            cls._validate_required(record, prefix, report)
            cls._validate_label(record, prefix, report)
            cls._validate_time_order(record, prefix, report)
            cls._validate_split(record, prefix, report)

            if record.pair_id in seen_pair_ids:
                report.errors.append(f"{prefix}: duplicate pair_id")
            seen_pair_ids.add(record.pair_id)

            if validate_paths:
                cls._validate_paths(record, prefix, report, Path(base_dir), validate_hashes)

        cls._validate_split_leakage(records, report)
        report.is_valid = not report.errors
        return report

    @staticmethod
    def _validate_required(record: DatasetPairRecord, prefix: str, report: ValidationReport) -> None:
        required = [
            "pair_id",
            "extension_id",
            "extension_name",
            "old_version",
            "new_version",
            "old_archive_path",
            "new_archive_path",
            "source",
            "license",
            "label",
            "label_rationale",
        ]
        for field_name in required:
            if not getattr(record, field_name):
                report.errors.append(f"{prefix}: missing {field_name}")

        if not record.provenance.source_type:
            report.errors.append(f"{prefix}: missing provenance.source_type")
        if not record.provenance.source_uri:
            report.errors.append(f"{prefix}: missing provenance.source_uri")
        if not record.provenance.collection_timestamp:
            report.errors.append(f"{prefix}: missing provenance.collection_timestamp")

    @staticmethod
    def _validate_label(record: DatasetPairRecord, prefix: str, report: ValidationReport) -> None:
        if not is_valid_label(record.label):
            report.errors.append(f"{prefix}: invalid label {record.label!r}")
            return

        if record.label_confidence not in ALLOWED_CONFIDENCE:
            report.errors.append(f"{prefix}: invalid label_confidence {record.label_confidence!r}")

        if record.label == Label.CONTROLLED_MALICIOUS.value and not record.controlled_mutation_type:
            report.errors.append(f"{prefix}: controlled malicious label requires controlled_mutation_type")

        if not LABEL_ONTOLOGY[record.label]["allowed_for_training"]:
            report.warnings.append(f"{prefix}: label {record.label!r} must be excluded from supervised training")

    @staticmethod
    def _parse_timestamp(value: str | None) -> dt.datetime | None:
        if not value:
            return None
        normalized = value.replace("Z", "+00:00")
        return dt.datetime.fromisoformat(normalized)

    @classmethod
    def _validate_time_order(cls, record: DatasetPairRecord, prefix: str, report: ValidationReport) -> None:
        try:
            old_time = cls._parse_timestamp(record.old_timestamp)
            new_time = cls._parse_timestamp(record.new_timestamp)
            cls._parse_timestamp(record.provenance.collection_timestamp)
        except ValueError as exc:
            report.errors.append(f"{prefix}: invalid timestamp: {exc}")
            return

        if old_time and new_time and old_time > new_time:
            report.errors.append(f"{prefix}: old_timestamp is after new_timestamp")

    @staticmethod
    def _validate_split(record: DatasetPairRecord, prefix: str, report: ValidationReport) -> None:
        if record.split not in ALLOWED_SPLITS:
            report.errors.append(f"{prefix}: invalid split {record.split!r}")

    @staticmethod
    def _validate_paths(
        record: DatasetPairRecord,
        prefix: str,
        report: ValidationReport,
        base_dir: Path,
        validate_hashes: bool,
    ) -> None:
        for attr, hash_attr in (("old_archive_path", "old_sha256"), ("new_archive_path", "new_sha256")):
            raw_path = Path(getattr(record, attr))
            path = raw_path if raw_path.is_absolute() else base_dir / raw_path
            if not path.exists():
                report.errors.append(f"{prefix}: {attr} does not exist: {raw_path}")
                continue
            expected_hash = getattr(record.provenance, hash_attr)
            if validate_hashes and expected_hash:
                actual_hash = sha256_file(path)
                if actual_hash.lower() != expected_hash.lower():
                    report.errors.append(f"{prefix}: {attr} SHA-256 mismatch")

    @staticmethod
    def _validate_split_leakage(records: Sequence[DatasetPairRecord], report: ValidationReport) -> None:
        extension_splits = {}
        for record in records:
            if record.split is None:
                continue
            extension_splits.setdefault(record.extension_id, set()).add(record.split)

        for extension_id, splits in extension_splits.items():
            experiment_splits = splits - {"controlled_holdout"}
            if len(experiment_splits) > 1:
                report.errors.append(
                    f"extension_id {extension_id!r} appears in multiple experiment splits: {sorted(experiment_splits)}"
                )
