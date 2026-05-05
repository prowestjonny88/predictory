"""
Model loader service — loads ML artifacts for inference
"""
import os
import json
import pickle
from typing import Optional, Dict, Any
from pathlib import Path


class ModelArtifactError(RuntimeError):
    """Raised when required ML artifacts are missing or unusable."""


class ModelArtifacts:
    def __init__(
        self,
        model_path: Optional[str] = None,
        residual_bands_path: Optional[str] = None,
        feature_schema_path: Optional[str] = None,
        encoded_feature_schema_path: Optional[str] = None,
        metrics_path: Optional[str] = None,
    ):
        self.model_path = model_path
        self.residual_bands_path = residual_bands_path
        self.feature_schema_path = feature_schema_path
        self.encoded_feature_schema_path = encoded_feature_schema_path
        self.metrics_path = metrics_path

        self._model = None
        self._residual_bands = None
        self._feature_schema = None
        self._encoded_feature_schema = None
        self._metrics = None
        self.base_path = str(Path(model_path).parent) if model_path else None

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
    def encoded_feature_schema(self) -> Optional[Dict[str, Any]]:
        if (
            self._encoded_feature_schema is None
            and self.encoded_feature_schema_path
            and os.path.exists(self.encoded_feature_schema_path)
        ):
            with open(self.encoded_feature_schema_path, 'r') as f:
                self._encoded_feature_schema = json.load(f)
        return self._encoded_feature_schema

    @property
    def metrics(self) -> Optional[Dict[str, Any]]:
        if self._metrics is None and self.metrics_path and os.path.exists(self.metrics_path):
            with open(self.metrics_path, 'r') as f:
                self._metrics = json.load(f)
        return self._metrics

    def is_loaded(self) -> bool:
        return all(
            bool(path and os.path.exists(path))
            for path in (
                self.model_path,
                self.residual_bands_path,
                self.feature_schema_path,
                self.encoded_feature_schema_path,
                self.metrics_path,
            )
        )

    def validate_for_inference(self) -> None:
        missing = [
            label
            for label, path in (
                ("LightGBM model", self.model_path),
                ("residual bands", self.residual_bands_path),
                ("raw feature schema", self.feature_schema_path),
                ("encoded feature schema", self.encoded_feature_schema_path),
                ("model metrics", self.metrics_path),
            )
            if not path or not os.path.exists(path)
        ]
        if missing:
            raise ModelArtifactError(f"Missing required ML artifact(s): {', '.join(missing)}")
        if self.model is None:
            raise ModelArtifactError("LightGBM model artifact could not be loaded")
        if not self.residual_bands:
            raise ModelArtifactError("Residual band artifact could not be loaded")
        if not self.feature_schema:
            raise ModelArtifactError("Raw feature schema artifact could not be loaded")
        encoded = self.encoded_feature_schema or {}
        encoded_columns = encoded.get("encoded_feature_columns") or []
        if not encoded_columns:
            raise ModelArtifactError("Encoded feature schema has no encoded_feature_columns")
        model_columns = list(getattr(self.model, "feature_name_", []) or [])
        if model_columns and model_columns != encoded_columns:
            raise ModelArtifactError("Encoded feature schema does not match model feature order")
        if not self.metrics:
            raise ModelArtifactError("Model metrics artifact could not be loaded")

    def get_engine_name(self) -> str:
        return "lightgbm_mlops_prototype"

    def get_model_status(self) -> str:
        return "MLOps prototype"

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
        root_models = repo_root / "models"
        legacy_models = repo_root / "backend" / "models"
        base_path = root_models if root_models.exists() else legacy_models

        _model_artifacts = ModelArtifacts(
            model_path=str(base_path / "lightgbm_p50_v1.pkl"),
            residual_bands_path=str(base_path / "residual_bands_v1.json"),
            feature_schema_path=str(base_path / "feature_schema_v1.json"),
            encoded_feature_schema_path=str(base_path / "encoded_feature_schema_step8.json"),
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
        "artifact_base_path": artifacts.base_path,
        "offline_model_available": artifacts.is_loaded(),
        "residual_bands_available": artifacts.residual_bands is not None,
        "encoded_feature_schema_available": artifacts.encoded_feature_schema is not None,
    }
