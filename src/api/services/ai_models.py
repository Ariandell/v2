"""
ModelRegistry — centralised AI model management.

Handles loading, storing, and exposing all ML models needed for inference:
ResNet (mel-spectrogram CNN), MLP (numerical features), Whisper (NLP),
DistilBERT (vibe/zero-shot), and NLP genre classifier.
"""

import numpy as np
import pandas as pd
import torch
from pathlib import Path

from src.utils.config import load_config, get_project_root
from src.features.nlp_extractor import NLPExtractor
from src.features.vibe_extractor import VibeExtractor
from src.models.cnn_model import MusicResNet, MusicMLP
from src.models.nlp_classifier import NLPClassifier


class ModelRegistry:
    """
    Singleton-style container for all AI models.

    Usage:
        registry = ModelRegistry()
        registry.load()          # call once at startup
        registry.resnet          # access loaded model
    """

    def __init__(self) -> None:
        self.config: dict = {}
        self.device: torch.device = torch.device("cpu")
        self.genres: list[str] = []

        # Torch models
        self.resnet: MusicResNet | None = None
        self.mlp: MusicMLP | None = None

        # NLP / Vibe
        self.nlp_extractor: NLPExtractor | None = None
        self.vibe_extractor: VibeExtractor | None = None
        self.nlp_classifier: NLPClassifier | None = None

        # Normalisation stats (computed from training data)
        self.train_mean: np.ndarray | None = None
        self.train_std: np.ndarray | None = None
        self.feat_cols: list[str] = []

    # ── Loading ───────────────────────────────────────────────────────────────

    def load(self) -> None:
        """Load config, normalisation stats, and all models into VRAM/RAM."""
        print("Starting AI Music Server. Loading models into VRAM...")

        self.config = load_config()
        root = get_project_root()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.genres = self.config["dataset"]["genres"]

        self._load_normalisation_stats(root)
        self._load_torch_models(root)
        self._load_nlp_models()

        print("All models loaded successfully!")

    def _load_normalisation_stats(self, root: Path) -> None:
        """Load feature parquet and compute mean/std for MLP normalisation."""
        feat_path = root / self.config["paths"]["features"]
        if not feat_path.exists():
            raise RuntimeError(
                f"Cannot find {feat_path} to normalise MLP inputs."
            )

        df = pd.read_parquet(feat_path)
        drop_cols = {"track_id", "genre", "filepath", "duration"}
        self.feat_cols = [c for c in df.columns if c not in drop_cols]

        features = df[self.feat_cols].values.astype(np.float32)
        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
        self.train_mean = np.mean(features, axis=0)
        self.train_std = np.std(features, axis=0) + 1e-8

    def _load_torch_models(self, root: Path) -> None:
        """Load ResNet and MLP state dicts."""
        n_classes = len(self.genres)
        emb_dim = self.config["model"]["cnn"]["embedding_dim"]

        resnet_path = root / "models" / "best_resnet.pth"
        mlp_path = root / "models" / "best_mlp.pth"

        self.resnet = MusicResNet(n_classes=n_classes, embedding_dim=emb_dim).to(self.device)
        self.mlp = MusicMLP(
            n_features=len(self.feat_cols),
            n_classes=n_classes,
            embedding_dim=emb_dim,
        ).to(self.device)

        self.resnet.load_state_dict(torch.load(resnet_path, map_location=self.device))
        self.mlp.load_state_dict(torch.load(mlp_path, map_location=self.device))

        self.resnet.eval()
        self.mlp.eval()

    def _load_nlp_models(self) -> None:
        """Load Whisper, vibe (zero-shot), and NLP genre classifier."""
        self.nlp_classifier = NLPClassifier(self.genres)
        self.nlp_extractor = NLPExtractor()
        self.vibe_extractor = VibeExtractor()

    # ── Inference helpers ─────────────────────────────────────────────────────

    def normalise_features(self, raw_features: dict) -> np.ndarray:
        """Normalise a raw feature dict using training mean/std."""
        vec = np.array(
            [raw_features.get(c, 0.0) for c in self.feat_cols],
            dtype=np.float32,
        )
        vec = np.nan_to_num(vec, nan=0.0, posinf=0.0, neginf=0.0)
        normed = (vec - self.train_mean) / self.train_std
        normed = np.nan_to_num(normed, nan=0.0, posinf=0.0, neginf=0.0)
        return np.clip(normed, -10.0, 10.0)
