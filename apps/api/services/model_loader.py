"""
Model loader service — loads ML artifacts for inference
"""
import os
import json
import pickle
from typing import Optional, Dict, Any
from pathlib import Path


class ModelArtifacts:
    def __init__(
        self,
        model_path: Optional[str] = None,
        residual_bands_path: Optional[str] = None,
        feature_schema_path: Optional[str] = None,
        metrics_path: Optional[str] = None,
    ):
        self.model_path = model_path
        self.residual_bands_path = residual_bands_path
        self.feature_schema_path = feature_schema_path
        self.metrics_path = metrics_path

        self._model = None
        self._residual_bands = None
        self._feature_schema = None
        self._metrics = None

    @property
    def model(self):
        if self._model is None and self.model_path and os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f:
                self._model = pickle.load(f)
        return self._model

    @property
    def residual_bands(self) -> Optional[Dict[str, Any]]:
        if self._residual_bands is None and self.residual_bands_path and os.path.exists(self.residual_bands_path):
            with open(self.residual_bands_path, 'r') as f:
                self._residual_bands = json.load(f)
        return self._residual_bands

    @property
    def feature_schema(self) -> Optional[Dict[str, Any]]:
        if self._feature_schema is None and self.feature_schema_path and os.path.exists(self.feature_schema_path):
            with open(self.feature_schema_path, 'r') as f:
                self._feature_schema = json.load(f)
        return self._feature_schema

    @property
    def metrics(self) -> Optional[Dict[str, Any]]:
        if self._metrics is None and self.metrics_path and os.path.exists(self.metrics_path):
            with open(self.metrics_path, 'r') as f:
                self._metrics = json.load(f)
        return self._metrics

    def is_loaded(self) -> bool:
        return self.model is not None

    def get_engine_name(self) -> str:
        if self.is_loaded():
            return "lightgbm_mlops_prototype"
        return "baseline_heuristic"

    def get_model_status(self) -> str:
        if self.is_loaded():
            return "MLOps prototype"
        return "Baseline heuristic (model not available)"

    def get_validation_window(self) -> str:
        if self.metrics:
            return self.metrics.get("validation_window", "unknown")
        return "unknown"


# Global model artifacts instance
_model_artifacts = None


def get_model_artifacts() -> ModelArtifacts:
    """Get or create the global model artifacts instance"""
    global _model_artifacts
    if _model_artifacts is None:
        repo_root = Path(__file__).parent.parent.parent.parent
        base_path = repo_root / "backend" / "models"

        _model_artifacts = ModelArtifacts(
            model_path=str(base_path / "lightgbm_p50_v1.pkl"),
            residual_bands_path=str(base_path / "residual_bands_v1.json"),
            feature_schema_path=str(base_path / "feature_schema_v1.json"),
            metrics_path=str(base_path / "model_metrics_v1.json"),
        )

    return _model_artifacts


def load_model_for_inference():
    """Load model artifacts for inference, return engine info"""
    artifacts = get_model_artifacts()

    return {
        "engine_name": artifacts.get_engine_name(),
        "model_status": artifacts.get_model_status(),
        "validation_window": artifacts.get_validation_window(),
        "is_loaded": artifacts.is_loaded(),
        "metrics": artifacts.metrics or {},
    }
