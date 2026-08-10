from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProvenanceRecord:
    source_type: str
    source_uri: str
    collection_timestamp: str
    license: str
    collector: str
    old_sha256: Optional[str] = None
    new_sha256: Optional[str] = None
    generation_method: Optional[str] = None
    notes: List[str] = field(default_factory=list)


@dataclass
class DatasetPairRecord:
    pair_id: str
    extension_id: str
    extension_name: str
    old_version: str
    new_version: str
    old_archive_path: str
    new_archive_path: str
    old_timestamp: Optional[str]
    new_timestamp: Optional[str]
    source: str
    license: str
    label: str
    label_rationale: str
    provenance: ProvenanceRecord
    controlled_mutation_type: Optional[str] = None
    label_confidence: str = "high"
    label_source: str = "unknown"
    label_review_status: str = "unreviewed"
    label_quality_tier: str = "UNCERTAIN"
    eligible_for_supervised_training: bool = False
    functional_category: Optional[str] = None
    review_packet_path: Optional[str] = None
    feature_vector: Dict[str, Any] = field(default_factory=dict)
    drift_vector: Dict[str, Any] = field(default_factory=dict)
    split: Optional[str] = None
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair_id": self.pair_id,
            "extension_id": self.extension_id,
            "extension_name": self.extension_name,
            "old_version": self.old_version,
            "new_version": self.new_version,
            "old_archive_path": self.old_archive_path,
            "new_archive_path": self.new_archive_path,
            "old_timestamp": self.old_timestamp,
            "new_timestamp": self.new_timestamp,
            "source": self.source,
            "license": self.license,
            "label": self.label,
            "label_rationale": self.label_rationale,
            "provenance": {
                "source_type": self.provenance.source_type,
                "source_uri": self.provenance.source_uri,
                "collection_timestamp": self.provenance.collection_timestamp,
                "license": self.provenance.license,
                "collector": self.provenance.collector,
                "old_sha256": self.provenance.old_sha256,
                "new_sha256": self.provenance.new_sha256,
                "generation_method": self.provenance.generation_method,
                "notes": list(self.provenance.notes),
            },
            "controlled_mutation_type": self.controlled_mutation_type,
            "label_confidence": self.label_confidence,
            "label_source": self.label_source,
            "label_review_status": self.label_review_status,
            "label_quality_tier": self.label_quality_tier,
            "eligible_for_supervised_training": self.eligible_for_supervised_training,
            "functional_category": self.functional_category,
            "review_packet_path": self.review_packet_path,
            "feature_vector": dict(self.feature_vector),
            "drift_vector": dict(self.drift_vector),
            "split": self.split,
            "notes": list(self.notes),
        }
