from __future__ import annotations

import argparse
import datetime as dt
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Sequence

from driftbench.governance import (
    DRIFTBENCH_VERSION,
    QUARANTINE_LICENSE_STATUSES,
    license_allows_research_dataset,
    source_category_is_acceptable,
)
from driftbench.label_quality import eligible_for_supervised_training, infer_label_quality_tier
from driftbench.labels import LABEL_REVIEW_STATUSES, Label, is_valid_label, is_valid_label_source
from driftbench.provenance import sha256_file
from driftbench.schema import DatasetPairRecord, ProvenanceRecord
from driftbench.versioning import compare_versions, parse_timestamp


@dataclass
class CuratedRecord:
    record: DatasetPairRecord
    stage: str
    quality_status: str
    reasons: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntakeResult:
    dataset_version: str
    accepted: List[CuratedRecord] = field(default_factory=list)
    quarantined: List[CuratedRecord] = field(default_factory=list)
    excluded: List[CuratedRecord] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    dry_run: bool = True

    @property
    def accepted_records(self) -> List[DatasetPairRecord]:
        return [item.record for item in self.accepted]

    def summary(self) -> Dict[str, Any]:
        label_counts: Dict[str, int] = {}
        label_sources: Dict[str, int] = {}
        label_quality_tiers: Dict[str, int] = {}
        license_statuses: Dict[str, int] = {}
        license_identifiers: Dict[str, int] = {}
        source_types: Dict[str, int] = {}
        split_counts: Dict[str, int] = {}
        category_counts: Dict[str, int] = {}
        eligible_count = 0
        real = 0
        controlled = 0
        for group in (self.accepted, self.quarantined, self.excluded):
            for item in group:
                record = item.record
                label_counts[record.label] = label_counts.get(record.label, 0) + 1
                label_source = item.metadata.get("label_source", "unknown")
                label_sources[label_source] = label_sources.get(label_source, 0) + 1
                label_quality = item.metadata.get("label_quality_tier", "unknown")
                label_quality_tiers[label_quality] = label_quality_tiers.get(label_quality, 0) + 1
                license_status = item.metadata.get("license_status", "unknown")
                license_statuses[license_status] = license_statuses.get(license_status, 0) + 1
                license_identifier = item.metadata.get("license", "unknown")
                license_identifiers[license_identifier] = license_identifiers.get(license_identifier, 0) + 1
                source_type = item.metadata.get("source_type", "unknown/unverified")
                source_types[source_type] = source_types.get(source_type, 0) + 1
                split = record.split or "unsplit"
                split_counts[split] = split_counts.get(split, 0) + 1
                category = item.metadata.get("functional_category") or "unknown"
                category_counts[category] = category_counts.get(category, 0) + 1
                if record.eligible_for_supervised_training:
                    eligible_count += 1
                if item.metadata.get("is_controlled"):
                    controlled += 1
                else:
                    real += 1
        return {
            "dataset_version": self.dataset_version,
            "imported": len(self.accepted) + len(self.quarantined) + len(self.excluded),
            "accepted": len(self.accepted),
            "quarantined": len(self.quarantined),
            "excluded": len(self.excluded),
            "real_record_count": real,
            "controlled_record_count": controlled,
            "unique_extension_count": len({item.record.extension_id for item in self.accepted}),
            "version_pair_count": len(self.accepted),
            "label_distribution": dict(sorted(label_counts.items())),
            "label_source_distribution": dict(sorted(label_sources.items())),
            "label_quality_tier_distribution": dict(sorted(label_quality_tiers.items())),
            "license_status_distribution": dict(sorted(license_statuses.items())),
            "license_identifier_distribution": dict(sorted(license_identifiers.items())),
            "source_type_distribution": dict(sorted(source_types.items())),
            "split_counts": dict(sorted(split_counts.items())),
            "functional_category_distribution": dict(sorted(category_counts.items())),
            "eligible_supervised_training_count": eligible_count,
            "dry_run": self.dry_run,
        }


def load_import_manifest(path: str | Path) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def curate_import_manifest(path: str | Path, *, dataset_root: str | Path = ".", dry_run: bool = True) -> IntakeResult:
    manifest_path = Path(path).resolve()
    payload = load_import_manifest(manifest_path)
    base_dir = manifest_path.parent
    dataset_version = payload.get("dataset_version") or DRIFTBENCH_VERSION
    records = payload.get("records", [])
    result = IntakeResult(dataset_version=dataset_version, dry_run=dry_run)

    for index, entry in enumerate(records):
        try:
            curated = _curate_entry(entry, base_dir=base_dir)
        except Exception as exc:
            result.validation_errors.append(f"record[{index}]: {exc}")
            continue
        if curated.stage == "ACCEPTED":
            result.accepted.append(curated)
        elif curated.stage == "QUARANTINED":
            result.quarantined.append(curated)
        else:
            result.excluded.append(curated)

    return result


def _curate_entry(entry: Dict[str, Any], *, base_dir: Path) -> CuratedRecord:
    old = entry.get("old", {})
    new = entry.get("new", {})
    reasons: List[str] = []
    warnings: List[str] = []

    source_type = entry.get("source_type", "unknown/unverified")
    license_status = entry.get("license_status", "unknown")
    label_source = entry.get("label_source", "unknown")
    label_review_status = entry.get("label_review_status", "unreviewed")
    explicit_label_quality_tier = entry.get("label_quality_tier")
    label = entry.get("label", "")
    is_controlled = bool(entry.get("is_controlled", source_type == "controlled"))

    for field_name in ("record_id", "extension_id", "extension_name", "source_reference", "label_rationale"):
        if not entry.get(field_name):
            reasons.append(f"missing {field_name}")
    if not source_category_is_acceptable(source_type):
        reasons.append(f"source_type {source_type!r} is not acceptable for automatic research intake")
    if not license_allows_research_dataset(license_status):
        reasons.append(f"license_status {license_status!r} blocks automatic acceptance")
    if not is_valid_label(label):
        reasons.append(f"invalid label {label!r}")
    if not is_valid_label_source(label_source):
        reasons.append(f"invalid label_source {label_source!r}")
    if label_review_status not in LABEL_REVIEW_STATUSES:
        reasons.append(f"invalid label_review_status {label_review_status!r}")
    try:
        label_quality_tier = infer_label_quality_tier(
            label=label,
            label_source=label_source,
            review_status=label_review_status,
            explicit_tier=explicit_label_quality_tier,
        )
    except ValueError as exc:
        label_quality_tier = "UNCERTAIN"
        reasons.append(str(exc))
    if label_source == "unknown":
        reasons.append("label_source is unknown")
    if label_source == "driftwatch_score":
        reasons.append("label_source must not be DriftWatch score")
    if label in {Label.UNCERTAIN.value, Label.NEEDS_REVIEW.value}:
        warnings.append(f"label {label!r} is retained for review/exclusion and not automatically accepted")
    if label == Label.EXCLUDED.value:
        reasons.append("label is excluded")

    old_path = _resolve_local_path(old.get("path"), base_dir)
    new_path = _resolve_local_path(new.get("path"), base_dir)
    old_manifest = _package_manifest(old_path, reasons, "old")
    new_manifest = _package_manifest(new_path, reasons, "new")
    old_sha = _hash_if_possible(old_path)
    new_sha = _hash_if_possible(new_path)
    _validate_expected_hash(old, old_sha, reasons, "old")
    _validate_expected_hash(new, new_sha, reasons, "new")
    _validate_identity(entry, old_manifest, new_manifest, reasons, warnings)
    _validate_version_order(entry, old, new, reasons)

    record = DatasetPairRecord(
        pair_id=entry.get("record_id", ""),
        extension_id=entry.get("extension_id", ""),
        extension_name=entry.get("extension_name", ""),
        old_version=old.get("version", ""),
        new_version=new.get("version", ""),
        old_archive_path=str(old_path) if old_path else "",
        new_archive_path=str(new_path) if new_path else "",
        old_timestamp=old.get("timestamp"),
        new_timestamp=new.get("timestamp"),
        source=entry.get("source_reference", ""),
        license=entry.get("license", "unknown"),
        label=label,
        label_rationale=entry.get("label_rationale", ""),
        provenance=ProvenanceRecord(
            source_type=source_type,
            source_uri=entry.get("source_reference", ""),
            collection_timestamp=entry.get("acquisition_timestamp") or dt.datetime.now(dt.timezone.utc).isoformat(),
            license=entry.get("license", "unknown"),
            collector=entry.get("collector", "unknown"),
            old_sha256=old_sha,
            new_sha256=new_sha,
            generation_method="phase3d_local_import",
            notes=list(entry.get("notes", [])),
        ),
        controlled_mutation_type=entry.get("controlled_mutation_type"),
        label_confidence=entry.get("label_confidence", "low"),
        label_source=label_source,
        label_review_status=label_review_status,
        label_quality_tier=label_quality_tier,
        eligible_for_supervised_training=False,
        functional_category=entry.get("functional_category"),
        review_packet_path=entry.get("review_packet_path"),
        split=entry.get("split"),
        notes=warnings,
    )

    metadata = {
        "source_type": source_type,
        "source_reference": entry.get("source_reference"),
        "source_repository": entry.get("source_repository"),
        "source_url": entry.get("source_url"),
        "source_dataset": entry.get("source_dataset"),
        "acquisition_timestamp": entry.get("acquisition_timestamp"),
        "old_original_filename": old.get("original_filename") or (old_path.name if old_path else None),
        "new_original_filename": new.get("original_filename") or (new_path.name if new_path else None),
        "old_original_path": old.get("original_path"),
        "new_original_path": new.get("original_path"),
        "old_raw_sha256": old.get("raw_sha256"),
        "new_raw_sha256": new.get("raw_sha256"),
        "old_normalized_sha256": old.get("normalized_sha256") or old_sha,
        "new_normalized_sha256": new.get("normalized_sha256") or new_sha,
        "old_download_url": old.get("download_url"),
        "new_download_url": new.get("download_url"),
        "old_tag": old.get("tag"),
        "new_tag": new.get("tag"),
        "old_manifest_path_in_raw_archive": old.get("manifest_path_in_raw_archive"),
        "new_manifest_path_in_raw_archive": new.get("manifest_path_in_raw_archive"),
        "manifest_version": new_manifest.get("manifest_version") if new_manifest else None,
        "license": entry.get("license", "unknown"),
        "license_status": license_status,
        "redistribution_allowed": entry.get("redistribution_allowed"),
        "research_use_allowed": entry.get("research_use_allowed"),
        "attribution_required": entry.get("attribution_required"),
        "is_controlled": is_controlled,
        "controlled_or_real": "controlled" if is_controlled else "real",
        "label_source": label_source,
        "label_review_status": label_review_status,
        "label_quality_tier": label_quality_tier,
        "eligible_for_supervised_training": None,
        "functional_category": entry.get("functional_category"),
        "review_packet_path": entry.get("review_packet_path"),
        "evidence_references": entry.get("evidence_references", []),
        "previous_release_time": old.get("timestamp"),
        "current_release_time": new.get("timestamp"),
        "pair_time": new.get("timestamp"),
        "timestamp_source": new.get("timestamp_source"),
        "timestamp_confidence": new.get("timestamp_confidence"),
        "validation_status": None,
    }

    if reasons:
        stage = "QUARANTINED" if license_status in QUARANTINE_LICENSE_STATUSES or source_type == "unknown/unverified" else "EXCLUDED"
        quality = "QUESTIONABLE" if stage == "QUARANTINED" else "REJECTED"
    elif warnings:
        stage = "ACCEPTED"
        quality = "QUESTIONABLE"
    else:
        stage = "ACCEPTED"
        quality = "COMPLETE" if _provenance_complete(metadata, record) else "PARTIAL"
    metadata["validation_status"] = stage
    provenance_complete = _provenance_complete(metadata, record)
    record.eligible_for_supervised_training = eligible_for_supervised_training(
        label=record.label,
        label_quality_tier=record.label_quality_tier,
        provenance_complete=provenance_complete,
        validation_stage=stage,
        explicit_eligible=entry.get("eligible_for_supervised_training"),
    )
    metadata["eligible_for_supervised_training"] = record.eligible_for_supervised_training
    return CuratedRecord(record=record, stage=stage, quality_status=quality, reasons=reasons + warnings, metadata=metadata)


def _resolve_local_path(value: str | None, base_dir: Path) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else (base_dir / path).resolve()


def _hash_if_possible(path: Path | None) -> str | None:
    if path and path.exists() and path.is_file():
        return sha256_file(path)
    return None


def _validate_expected_hash(version_entry: Dict[str, Any], actual_hash: str | None, reasons: List[str], label: str) -> None:
    expected = version_entry.get("sha256")
    if expected and actual_hash and expected.lower() != actual_hash.lower():
        reasons.append(f"{label} package SHA-256 mismatch")


def _package_manifest(path: Path | None, reasons: List[str], label: str) -> Dict[str, Any]:
    if not path:
        reasons.append(f"missing {label} package path")
        return {}
    if not path.exists():
        reasons.append(f"{label} package path does not exist")
        return {}
    try:
        with zipfile.ZipFile(path) as archive:
            if "manifest.json" not in archive.namelist():
                reasons.append(f"{label} package missing manifest.json")
                return {}
            with archive.open("manifest.json") as handle:
                return json.loads(handle.read().decode("utf-8"))
    except zipfile.BadZipFile:
        reasons.append(f"{label} package is not a valid ZIP/CRX-compatible archive")
    except json.JSONDecodeError:
        reasons.append(f"{label} manifest.json is invalid JSON")
    except UnicodeDecodeError:
        reasons.append(f"{label} manifest.json is not UTF-8 JSON")
    return {}


def _validate_identity(entry: Dict[str, Any], old_manifest: Dict[str, Any], new_manifest: Dict[str, Any], reasons: List[str], warnings: List[str]) -> None:
    old_ext_id = entry.get("old", {}).get("extension_id")
    new_ext_id = entry.get("new", {}).get("extension_id")
    if old_ext_id and new_ext_id and old_ext_id != new_ext_id:
        reasons.append("old/new extension IDs do not match")
    if old_manifest and new_manifest:
        old_name = old_manifest.get("name")
        new_name = new_manifest.get("name")
        if old_name and new_name and old_name != new_name:
            warnings.append("manifest names differ; identity accepted only with external evidence")


def _validate_version_order(entry: Dict[str, Any], old: Dict[str, Any], new: Dict[str, Any], reasons: List[str]) -> None:
    comparison = compare_versions(
        old.get("version", ""),
        new.get("version", ""),
        old_timestamp=old.get("timestamp"),
        new_timestamp=new.get("timestamp"),
    )
    if comparison is None:
        reasons.append("version order cannot be established")
    elif comparison <= 0:
        reasons.append("old/new version order is not longitudinal")

    for timestamp_value, label in ((old.get("timestamp"), "old"), (new.get("timestamp"), "new"), (entry.get("acquisition_timestamp"), "acquisition")):
        if timestamp_value and parse_timestamp(timestamp_value) is None:
            reasons.append(f"{label} timestamp is invalid")


def _provenance_complete(metadata: Dict[str, Any], record: DatasetPairRecord) -> bool:
    required = [
        record.pair_id,
        record.extension_id,
        record.extension_name,
        record.old_version,
        record.new_version,
        record.provenance.old_sha256,
        record.provenance.new_sha256,
        metadata.get("source_reference"),
        metadata.get("license_status"),
        metadata.get("label_source"),
    ]
    return all(required)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safely curate local DriftBench import manifests.")
    parser.add_argument("--manifest", required=True, help="Path to Phase 3D import manifest JSON.")
    parser.add_argument("--output", default="artifacts/driftbench/phase3d", help="Output directory for curation manifests.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and report without accepting records into validated output.")
    args = parser.parse_args(argv)

    result = curate_import_manifest(args.manifest, dry_run=args.dry_run)
    from driftbench.manifests import write_phase3d_manifests

    write_phase3d_manifests(result, args.output, source_manifest_path=args.manifest)
    print(json.dumps(result.summary(), indent=2, sort_keys=True))
    return 0 if not result.validation_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
