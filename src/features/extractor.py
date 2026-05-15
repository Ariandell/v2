"""
Feature Extraction Pipeline.

Extracts ~150-200 audio features from each track using librosa and essentia:
  - Timbral (MFCC, spectral centroid/bandwidth/rolloff/contrast, ZCR)
  - Rhythmic (tempo, onset strength, beat strength)
  - Harmonic (chroma CQT, tonnetz, key detection)
  - Dynamic (RMS energy, dynamic range)

Each time-series feature is aggregated with 6 statistics:
  mean, std, min, max, skewness, kurtosis
"""

import numpy as np
import librosa
import pandas as pd
from pathlib import Path
from scipy import stats as scipy_stats
from tqdm import tqdm

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.utils.config import load_config, get_project_root


def compute_statistics(feature_array: np.ndarray) -> dict:
    """
    Compute 6 aggregate statistics for a time-series feature.
    
    Args:
        feature_array: 1D numpy array of feature values over time.
    
    Returns:
        Dict with keys: mean, std, min, max, skewness, kurtosis.
    """
    if len(feature_array) == 0:
        return {"mean": 0, "std": 0, "min": 0, "max": 0, "skewness": 0, "kurtosis": 0}
    
    return {
        "mean": float(np.mean(feature_array)),
        "std": float(np.std(feature_array)),
        "min": float(np.min(feature_array)),
        "max": float(np.max(feature_array)),
        "skewness": float(scipy_stats.skew(feature_array)),
        "kurtosis": float(scipy_stats.kurtosis(feature_array)),
    }


def extract_timbral_features(y: np.ndarray, sr: int, config: dict) -> dict:
    """
    Extract timbral features using librosa.
    
    Features:
        - MFCC (20 coefficients × 6 stats = 120 values)
        - Spectral Centroid (6 stats)
        - Spectral Bandwidth (6 stats)
        - Spectral Rolloff (6 stats)
        - Spectral Contrast (7 bands × 6 stats = 42 values)
        - Zero-Crossing Rate (6 stats)
    
    Total: ~192 values
    """
    features = {}
    
    n_fft = config["features"]["n_fft"]
    hop_length = config["features"]["hop_length"]
    n_mfcc = config["features"]["mfcc_coefficients"]
    
    # --- MFCC ---
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc, n_fft=n_fft, hop_length=hop_length)
    for i in range(n_mfcc):
        stats = compute_statistics(mfcc[i])
        for stat_name, stat_val in stats.items():
            features[f"mfcc_{i:02d}_{stat_name}"] = stat_val
    
    # --- MFCC Delta (first derivative — shows how timbre changes) ---
    mfcc_delta = librosa.feature.delta(mfcc)
    for i in range(n_mfcc):
        stats = compute_statistics(mfcc_delta[i])
        for stat_name, stat_val in stats.items():
            features[f"mfcc_delta_{i:02d}_{stat_name}"] = stat_val
    
    # --- Spectral Centroid ---
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, n_fft=n_fft, hop_length=hop_length)[0]
    stats = compute_statistics(centroid)
    for stat_name, stat_val in stats.items():
        features[f"spectral_centroid_{stat_name}"] = stat_val
    
    # --- Spectral Bandwidth ---
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr, n_fft=n_fft, hop_length=hop_length)[0]
    stats = compute_statistics(bandwidth)
    for stat_name, stat_val in stats.items():
        features[f"spectral_bandwidth_{stat_name}"] = stat_val
    
    # --- Spectral Rolloff ---
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, n_fft=n_fft, hop_length=hop_length)[0]
    stats = compute_statistics(rolloff)
    for stat_name, stat_val in stats.items():
        features[f"spectral_rolloff_{stat_name}"] = stat_val
    
    # --- Spectral Contrast (7 frequency bands) ---
    contrast = librosa.feature.spectral_contrast(y=y, sr=sr, n_fft=n_fft, hop_length=hop_length)
    for i in range(contrast.shape[0]):
        stats = compute_statistics(contrast[i])
        for stat_name, stat_val in stats.items():
            features[f"spectral_contrast_{i}_{stat_name}"] = stat_val
    
    # --- Zero-Crossing Rate ---
    zcr = librosa.feature.zero_crossing_rate(y, frame_length=n_fft, hop_length=hop_length)[0]
    stats = compute_statistics(zcr)
    for stat_name, stat_val in stats.items():
        features[f"zcr_{stat_name}"] = stat_val
    
    return features


def extract_rhythmic_features(y: np.ndarray, sr: int, config: dict) -> dict:
    """
    Extract rhythmic features using librosa.
    
    Features:
        - Tempo (BPM) — single value
        - Onset Strength (6 stats)
        - Tempogram — dominant rhythm period (6 stats)
        - Beat Strength Variance — single value
    """
    features = {}
    
    hop_length = config["features"]["hop_length"]
    
    # --- Tempo (BPM) ---
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
    # tempo can be an array in newer librosa versions
    if isinstance(tempo, np.ndarray):
        tempo = float(tempo[0]) if len(tempo) > 0 else 0.0
    features["tempo_bpm"] = float(tempo)
    
    # --- Onset Strength ---
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    stats = compute_statistics(onset_env)
    for stat_name, stat_val in stats.items():
        features[f"onset_strength_{stat_name}"] = stat_val
    
    # --- Tempogram (shows rhythmic patterns) ---
    tempogram = librosa.feature.tempogram(y=y, sr=sr, hop_length=hop_length)
    # Take the mean across time to get a rhythm profile
    tempo_profile = np.mean(tempogram, axis=1)
    stats = compute_statistics(tempo_profile)
    for stat_name, stat_val in stats.items():
        features[f"tempogram_{stat_name}"] = stat_val
    
    # --- Beat Strength Variance ---
    if len(beat_frames) > 1:
        beat_strengths = onset_env[beat_frames]
        features["beat_strength_variance"] = float(np.var(beat_strengths))
        features["beat_strength_mean"] = float(np.mean(beat_strengths))
    else:
        features["beat_strength_variance"] = 0.0
        features["beat_strength_mean"] = 0.0
    
    # --- Beat regularity (how consistent are beat intervals) ---
    if len(beat_frames) > 2:
        beat_intervals = np.diff(beat_frames)
        features["beat_regularity"] = float(1.0 / (np.std(beat_intervals) + 1e-6))
    else:
        features["beat_regularity"] = 0.0
    
    return features


def extract_harmonic_features(y: np.ndarray, sr: int, config: dict) -> dict:
    """
    Extract harmonic features using librosa.
    
    Features:
        - Chroma CQT (12 pitch classes × 6 stats = 72 values)
        - Tonnetz (6 dimensions × 6 stats = 36 values)
        - Estimated key & mode (2 values)
    """
    features = {}
    
    hop_length = config["features"]["hop_length"]
    
    # --- Harmonic/Percussive separation ---
    y_harmonic, y_percussive = librosa.effects.hpss(y)
    
    # --- Chroma CQT (on harmonic component for cleaner results) ---
    chroma = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr, hop_length=hop_length)
    
    pitch_classes = ['C', 'Cs', 'D', 'Ds', 'E', 'F', 'Fs', 'G', 'Gs', 'A', 'As', 'B']
    for i in range(12):
        stats = compute_statistics(chroma[i])
        for stat_name, stat_val in stats.items():
            features[f"chroma_{pitch_classes[i]}_{stat_name}"] = stat_val
    
    # --- Tonnetz (tonal centroid features — 6D representation of harmony) ---
    tonnetz = librosa.feature.tonnetz(y=y_harmonic, sr=sr)
    tonnetz_names = ['fifth_x', 'fifth_y', 'minor_x', 'minor_y', 'major_x', 'major_y']
    for i in range(6):
        stats = compute_statistics(tonnetz[i])
        for stat_name, stat_val in stats.items():
            features[f"tonnetz_{tonnetz_names[i]}_{stat_name}"] = stat_val
    
    # --- Key detection (Krumhansl-Schmuckler) ---
    # Use mean chroma profile to estimate key
    chroma_mean = np.mean(chroma, axis=1)
    
    # Krumhansl-Kessler key profiles
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    
    best_corr = -2
    best_key = 0
    best_mode = 0  # 0 = major, 1 = minor
    
    for shift in range(12):
        shifted = np.roll(chroma_mean, shift)
        
        corr_major = np.corrcoef(shifted, major_profile)[0, 1]
        corr_minor = np.corrcoef(shifted, minor_profile)[0, 1]
        
        if corr_major > best_corr:
            best_corr = corr_major
            best_key = shift
            best_mode = 0
        
        if corr_minor > best_corr:
            best_corr = corr_minor
            best_key = shift
            best_mode = 1
    
    features["estimated_key"] = best_key           # 0=C, 1=C#, ... 11=B
    features["estimated_mode"] = best_mode          # 0=major, 1=minor
    features["key_confidence"] = float(best_corr)   # correlation strength
    
    # --- Harmonic-to-percussive ratio ---
    harmonic_energy = float(np.mean(y_harmonic ** 2))
    percussive_energy = float(np.mean(y_percussive ** 2))
    features["harmonic_percussive_ratio"] = harmonic_energy / (percussive_energy + 1e-10)
    
    return features


def extract_dynamic_features(y: np.ndarray, sr: int, config: dict) -> dict:
    """
    Extract dynamic (energy/loudness) features using librosa.
    
    Features:
        - RMS Energy (6 stats)
        - Energy in 3 time segments (beginning, middle, end)
        - Dynamic range
    """
    features = {}
    
    n_fft = config["features"]["n_fft"]
    hop_length = config["features"]["hop_length"]
    
    # --- RMS Energy ---
    rms = librosa.feature.rms(y=y, frame_length=n_fft, hop_length=hop_length)[0]
    stats = compute_statistics(rms)
    for stat_name, stat_val in stats.items():
        features[f"rms_{stat_name}"] = stat_val
    
    # --- RMS in dB ---
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)
    stats = compute_statistics(rms_db)
    for stat_name, stat_val in stats.items():
        features[f"rms_db_{stat_name}"] = stat_val
    
    # --- Dynamic range (difference between loudest and quietest moments) ---
    features["dynamic_range_db"] = float(np.max(rms_db) - np.min(rms_db))
    
    # --- Energy in 3 segments (beginning, middle, end) ---
    n_frames = len(rms)
    third = n_frames // 3
    
    if third > 0:
        features["energy_segment_1_mean"] = float(np.mean(rms[:third]))
        features["energy_segment_2_mean"] = float(np.mean(rms[third:2*third]))
        features["energy_segment_3_mean"] = float(np.mean(rms[2*third:]))
        
        # Energy contrast between segments
        features["energy_rise"] = features["energy_segment_2_mean"] - features["energy_segment_1_mean"]
        features["energy_fall"] = features["energy_segment_3_mean"] - features["energy_segment_2_mean"]
    else:
        features["energy_segment_1_mean"] = float(np.mean(rms))
        features["energy_segment_2_mean"] = float(np.mean(rms))
        features["energy_segment_3_mean"] = float(np.mean(rms))
        features["energy_rise"] = 0.0
        features["energy_fall"] = 0.0
    
    return features


def extract_all_features(filepath: str, config: dict, y: np.ndarray = None, sr_out: int = None) -> dict:
    """
    Extract ALL features from a single audio file.
    
    Args:
        filepath: Path to the .wav file (used for metadata/duration).
        config: Project configuration dict.
        y: Optional pre-loaded audio array. If not provided, it will be loaded.
        sr_out: Optional sample rate of pre-loaded array.
    
    Returns:
        Dict with all features (flat, ready for DataFrame row).
    """
    sr = config["audio"]["sample_rate"]
    
    # Load audio only if not provided
    if y is None or sr_out is None:
        y, sr_out = librosa.load(filepath, sr=sr, mono=True)
    
    features = {}
    features["filepath"] = str(filepath)
    features["duration"] = float(librosa.get_duration(y=y, sr=sr_out))
    
    # Extract all feature groups
    features.update(extract_timbral_features(y, sr_out, config))
    features.update(extract_rhythmic_features(y, sr_out, config))
    features.update(extract_harmonic_features(y, sr_out, config))
    features.update(extract_dynamic_features(y, sr_out, config))
    
    return features


def generate_mel_spectrogram(
    filepath: str,
    output_path: str,
    config: dict,
) -> bool:
    """
    Generate and save a mel-spectrogram as .npy file for CNN input.
    
    Args:
        filepath: Path to the .wav file.
        output_path: Path to save the .npy spectrogram.
        config: Project configuration dict.
    
    Returns:
        True if successful.
    """
    try:
        sr = config["audio"]["sample_rate"]
        n_mels = config["features"]["n_mels"]
        n_fft = config["features"]["n_fft"]
        hop_length = config["features"]["hop_length"]
        
        y, sr_out = librosa.load(filepath, sr=sr, mono=True)
        
        # Compute mel-spectrogram
        mel_spec = librosa.feature.melspectrogram(
            y=y, sr=sr_out,
            n_mels=n_mels, n_fft=n_fft, hop_length=hop_length,
        )
        
        # Convert to log scale (dB)
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        
        # Normalize to [0, 1] range for CNN
        mel_spec_norm = (mel_spec_db - mel_spec_db.min()) / (mel_spec_db.max() - mel_spec_db.min() + 1e-10)
        
        # Resize to fixed dimensions if needed
        target_width = config["spectrogram"]["width"]
        target_height = config["spectrogram"]["height"]
        
        # Pad or trim time axis to target width
        if mel_spec_norm.shape[1] < target_width:
            # Pad with zeros
            pad_width = target_width - mel_spec_norm.shape[1]
            mel_spec_norm = np.pad(mel_spec_norm, ((0, 0), (0, pad_width)), mode='constant')
        elif mel_spec_norm.shape[1] > target_width:
            # Trim
            mel_spec_norm = mel_spec_norm[:, :target_width]
        
        # Save
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(output), mel_spec_norm)
        
        return True
        
    except Exception as e:
        print(f"❌ Spectrogram error for {filepath}: {e}")
        return False


import multiprocessing
from tqdm import tqdm

def process_track(args):
    """Worker function for multiprocessing."""
    genre, wav_path_str, spec_dir_str, config = args
    wav_path = Path(wav_path_str)
    spec_dir = Path(spec_dir_str)
    
    try:
        # Extract numerical features
        features = extract_all_features(str(wav_path), config)
        features["genre"] = genre
        features["track_id"] = wav_path.stem
        
        # Generate mel-spectrogram
        spec_path = spec_dir / genre / f"{wav_path.stem}.npy"
        generate_mel_spectrogram(str(wav_path), str(spec_path), config)
        
        return features
    except Exception as e:
        # Return error string if failed
        return f"Error on {wav_path.stem}: {e}"

def run_feature_extraction(config: dict = None):
    """
    Run feature extraction on all processed audio files using MultiProcessing.
    
    Extracts numerical features → features.parquet
    Generates mel-spectrograms → data/spectrograms/
    """
    if config is None:
        config = load_config()
    
    root = get_project_root()
    # Read from processed directory (normalized, fragmented tracks)
    audio_dir = root / "data" / "processed"
    spec_dir = root / config["paths"]["spectrograms"]
    features_path = root / config["paths"]["features"]
    
    # Collect all .wav files
    wav_files = []
    for genre in config["dataset"]["genres"]:
        genre_dir = audio_dir / genre
        if not genre_dir.exists():
            continue
        
        # Ensure output genre directory exists
        out_genre_dir = spec_dir / genre
        out_genre_dir.mkdir(parents=True, exist_ok=True)
        
        for wav_file in sorted(genre_dir.glob("*.wav")):
            wav_files.append((genre, str(wav_file), str(spec_dir), config))
    
    if not wav_files:
        print("No audio files found! Run process_raw.py first.")
        return
    
    # Check what's already processed to skip them
    existing_df = None
    processed_ids = set()
    if features_path.exists():
        existing_df = pd.read_parquet(features_path)
        if "track_id" in existing_df.columns:
            processed_ids = set(existing_df["track_id"].values)
            print(f"📦 Found {len(processed_ids)} already extracted tracks in features.parquet. Skipping them!")
            
    # Filter out already processed tracks
    new_wav_files = []
    for wf in wav_files:
        # wf is (genre, wav_path_str, spec_dir_str, config)
        _id = Path(wf[1]).stem
        if _id not in processed_ids:
            new_wav_files.append(wf)
            
    wav_files = new_wav_files
    
    if not wav_files:
        print("🎉 All files are already extracted! Nothing to do.")
        return
    
    print(f"\n🚀 Extractor upgraded to Multiprocessing mode!")
    print(f"🎵 Found {len(wav_files)} NEW tracks remaining. Starting extraction...")
    
    # The user has 12 threads. We use 6 as requested to avoid overheating.
    num_cores = 6
    print(f"💻 Using {num_cores} CPU threads out of {multiprocessing.cpu_count()}")
    
    all_features = []
    errors = 0
    
    with multiprocessing.Pool(num_cores) as pool:
        for result in tqdm(pool.imap_unordered(process_track, wav_files), total=len(wav_files)):
            if isinstance(result, dict):
                all_features.append(result)
            else:
                errors += 1
                # To avoid spamming, we just count errors in progress bar
    
    # Save feature matrix
    if all_features:
        new_df = pd.DataFrame(all_features)
        
        # Combine with existing data if present
        if existing_df is not None:
            df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            df = new_df
            
        # Move identifying columns to front
        id_cols = ["track_id", "genre", "filepath", "duration"]
        other_cols = [c for c in df.columns if c not in id_cols]
        df = df[id_cols + other_cols]
        
        df.to_parquet(str(features_path), index=False)
        
        print(f"\n✅ Feature extraction complete!")
        print(f"   Tracks processed efficiently: {len(df)}")
        print(f"   Features per track: {len(other_cols)}")
        print(f"   Errors: {errors}")
        print(f"   Saved to: {features_path}")
        
        # Print summary per genre
        print(f"\nTracks per genre:")
        for genre, count in df["genre"].value_counts().sort_index().items():
            print(f"   {genre}: {count}")
    else:
        print("No features extracted!")


if __name__ == "__main__":
    config = load_config()
    run_feature_extraction(config)
