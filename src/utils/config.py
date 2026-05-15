"""
Utility functions for loading config and common operations.
"""

import yaml
import os
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory (where config.yaml lives)."""
    current = Path(__file__).resolve()
    # Navigate up from src/utils/ to project root
    return current.parent.parent.parent


def load_config(config_path: str = None) -> dict:
    """
    Load configuration from config.yaml.
    
    Args:
        config_path: Optional path to config file. If None, uses project root.
    
    Returns:
        Dictionary with configuration values.
    """
    if config_path is None:
        config_path = get_project_root() / "config.yaml"
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    return config


def ensure_dirs(config: dict):
    """Create all necessary directories from config."""
    root = get_project_root()
    
    for key in ["raw_audio", "spectrograms", "models", "logs"]:
        dir_path = root / config["paths"][key]
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # Create genre subdirectories in raw_audio
    raw_dir = root / config["paths"]["raw_audio"]
    for genre in config["dataset"]["genres"]:
        (raw_dir / genre).mkdir(exist_ok=True)
    
    # Create spectrograms subdirectories
    spec_dir = root / config["paths"]["spectrograms"]
    for genre in config["dataset"]["genres"]:
        (spec_dir / genre).mkdir(exist_ok=True)
    
    # Ensure parent dir for features.parquet exists
    features_path = root / config["paths"]["features"]
    features_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Ensure parent dir for metadata.csv exists
    metadata_path = root / config["paths"]["metadata"]
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"✅ All directories created under {root}")


def get_genre_dir(config: dict, genre: str) -> Path:
    """Get the raw audio directory for a specific genre."""
    root = get_project_root()
    return root / config["paths"]["raw_audio"] / genre


def get_spectrogram_dir(config: dict, genre: str) -> Path:
    """Get the spectrogram directory for a specific genre."""
    root = get_project_root()
    return root / config["paths"]["spectrograms"] / genre


if __name__ == "__main__":
    config = load_config()
    ensure_dirs(config)
    print(f"📁 Project root: {get_project_root()}")
    print(f"🎵 Genres: {config['dataset']['genres']}")
    print(f"🎯 Tracks per genre: {config['dataset']['tracks_per_genre']}")
