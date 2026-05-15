"""
Audio analysis pipeline — the core AI inference flow.

Takes an audio file, extracts features, runs through ResNet + MLP ensemble,
applies NLP/cultural adjustments, and returns genre predictions with metadata.
"""

import numpy as np
import torch
import librosa
from pathlib import Path

from src.features.extractor import extract_all_features
from .ai_models import ModelRegistry


def run_analysis(audio_path: Path, display_name: str, registry: ModelRegistry) -> dict:
    """
    Full AI analysis pipeline on a local audio file.

    Steps:
        1. Find the most energetic 60-second fragment
        2. Generate mel-spectrogram → ResNet inference
        3. Extract numerical features → MLP inference
        4. Ensemble (70% ResNet + 30% MLP)
        5. NLP / cultural layer (Whisper + vibe)
        6. Return top-5 genre predictions

    Returns:
        dict with keys: filename, predictions, language, is_instrumental,
        lyrics, lyrics_english, vibes
    """
    config = registry.config
    device = registry.device
    genres = registry.genres

    # ── 1. Find peak-energy fragment ──────────────────────────────────────────
    y, sr_out = _load_peak_fragment(audio_path, config)

    # ── 2. ResNet: mel-spectrogram CNN ────────────────────────────────────────
    fragment_dur = config["audio"]["fragment_duration"]
    y_cnn = y[: int(fragment_dur * sr_out)]
    spec_tensor = _build_spectrogram_tensor(y_cnn, sr_out, config, device)

    # ── 3. MLP: numerical features ───────────────────────────────────────────
    raw_features = extract_all_features(str(audio_path), config, y=y, sr_out=sr_out)
    normed = registry.normalise_features(raw_features)
    feat_tensor = torch.from_numpy(normed).float().unsqueeze(0).to(device)

    # ── 4. Inference + ensemble ──────────────────────────────────────────────
    with torch.no_grad():
        resnet_out = torch.sigmoid(registry.resnet(spec_tensor))[0].cpu().numpy()
        mlp_out = torch.sigmoid(registry.mlp(feat_tensor))[0].cpu().numpy()

    ensemble = (resnet_out * 0.7) + (mlp_out * 0.3)

    # ── 5. NLP / cultural adjustment ─────────────────────────────────────────
    nlp_data = registry.nlp_extractor.extract_text_and_language(
        str(audio_path), max_duration=30, y=y_cnn, sr_in=sr_out,
    )
    is_instrumental = nlp_data.get("is_instrumental", False)

    vibe_data = None
    if not is_instrumental and nlp_data.get("english_translation"):
        vibe_data = registry.vibe_extractor.get_vibe(nlp_data["english_translation"])

    final_out = registry.nlp_classifier.adjust_probabilities(
        ensemble, nlp_data, vibe_data,
    )

    # ── 6. Build response ────────────────────────────────────────────────────
    top5_idx = np.argsort(final_out)[::-1][:5]
    top_genres = [
        {"genre": genres[idx], "probability": float(final_out[idx])}
        for idx in top5_idx
    ]

    return {
        "filename": display_name,
        "predictions": top_genres,
        "language": nlp_data.get("language", "unknown"),
        "is_instrumental": is_instrumental,
        "lyrics": nlp_data.get("original_text", ""),
        "lyrics_english": nlp_data.get("english_translation", ""),
        "vibes": vibe_data or {},
    }


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_peak_fragment(
    audio_path: Path, config: dict, window_sec: float = 60.0,
) -> tuple[np.ndarray, int]:
    """Load the most energetic fragment of an audio file."""
    # Fast energy scan at native sample rate
    start_sec = 0.0
    try:
        y_fast, sr_fast = librosa.load(str(audio_path), sr=None, mono=True)
        if len(y_fast) > window_sec * sr_fast:
            rms = librosa.feature.rms(
                y=y_fast, frame_length=sr_fast, hop_length=sr_fast,
            )[0]
            best_i = np.argmax(
                np.convolve(rms, np.ones(int(window_sec)), mode="valid")
            )
            start_sec = float(best_i)
    except Exception:
        pass

    # Re-load the peak window at target sample rate
    sr = config["audio"]["sample_rate"]
    try:
        y, sr_out = librosa.load(
            str(audio_path), sr=sr, mono=True,
            offset=start_sec, duration=window_sec,
        )
    except Exception:
        y, sr_out = librosa.load(
            str(audio_path), sr=sr, mono=True, duration=window_sec,
        )

    return y, sr_out


def _build_spectrogram_tensor(
    y: np.ndarray, sr: int, config: dict, device: torch.device,
) -> torch.Tensor:
    """Convert raw audio to a normalised mel-spectrogram tensor [1,1,128,256]."""
    mel = librosa.feature.melspectrogram(
        y=y, sr=sr,
        n_mels=config["features"]["n_mels"],
        hop_length=config["features"]["hop_length"],
        n_fft=config["features"]["n_fft"],
    )
    mel_db = librosa.power_to_db(mel, ref=np.max)
    mel_db = (mel_db - mel_db.min()) / (mel_db.max() - mel_db.min() + 1e-8)

    target_width = 256
    if mel_db.shape[1] > target_width:
        mel_db = mel_db[:, :target_width]
    else:
        mel_db = np.pad(
            mel_db, ((0, 0), (0, target_width - mel_db.shape[1])), mode="constant",
        )

    return torch.from_numpy(mel_db).float().unsqueeze(0).unsqueeze(0).to(device)
