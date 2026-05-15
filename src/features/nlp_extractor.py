import warnings
import torch
import numpy as np

# Suppress FP16 warnings on CPU
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

class NLPExtractor:
    def __init__(self, model_size="base", device=None):
        """
        Initializes the Whisper model.
        Args:
            model_size: "tiny", "base", "small", "medium", "large"
            device: "cuda" or "cpu". If None, auto-detect.
        """
        import whisper
        
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        print(f"🎙️ Loading Whisper ({model_size}) on {self.device}...")
        self.model = whisper.load_model(model_size, device=self.device)
        print("✅ Whisper loaded successfully!")
        
    def extract_text_and_language(self, filepath: str, max_duration=60, y: np.ndarray = None, sr_in: int = None):
        """
        Transcribes the first N seconds of an audio file.
        Returns:
            dict: {"language": str, "text": str}
        """
        import whisper
        import librosa
        
        try:
            print(f"   [NLP] Processing snippet for {filepath}...")
            
            # If audio is provided, just use it and resample if needed
            if y is not None and sr_in is not None:
                if sr_in != 16000:
                    y_16k = librosa.resample(y, orig_sr=sr_in, target_sr=16000)
                else:
                    y_16k = y
                
                # Take up to max_duration
                if len(y_16k) > max_duration * 16000:
                    audio_segment = y_16k[:max_duration * 16000]
                else:
                    audio_segment = y_16k
            else:
                # Load audio chunk if not provided
                y_raw, sr = librosa.load(filepath, sr=16000, mono=True)
                
                # Find energetic part
                if len(y_raw) > max_duration * sr:
                    rms_e = librosa.feature.rms(y=y_raw, frame_length=sr, hop_length=sr)[0]
                    best_i = np.argmax(np.convolve(rms_e, np.ones(max_duration), mode='valid'))
                    start = best_i * sr
                    end = start + max_duration * sr
                    audio_segment = y_raw[start:end]
                else:
                    audio_segment = y_raw
                
            # Make sure audio_segment is float32
            audio_segment = audio_segment.astype(np.float32)
            
            print(f"   [NLP] Transcribing snippet...")
            result_transcribe = self.model.transcribe(audio_segment, task="transcribe")
            
            # --- INSTRUMENTAL DETECTION ---
            # Whisper provides `no_speech_prob` for each segment.
            # But for music, this value is often high even WITH vocals (loud instruments).
            # So we use a DUAL check: high no_speech AND very short/empty text.
            segments = result_transcribe.get("segments", [])
            if segments:
                avg_no_speech = np.mean([s.get("no_speech_prob", 0) for s in segments])
            else:
                avg_no_speech = 1.0
            
            raw_text = result_transcribe["text"].strip()
            
            # Only instrumental if BOTH conditions are met:
            # 1. Whisper is very unsure about speech (>0.85)
            # 2. AND the transcribed text is very short (<15 chars) — i.e. Whisper found almost nothing
            is_instrumental = avg_no_speech > 0.85 and len(raw_text) < 15
            
            print(f"   [NLP] no_speech_prob: {avg_no_speech:.2f}, text_len: {len(raw_text)}")
            
            if is_instrumental:
                print(f"   [NLP] 🎻 INSTRUMENTAL DETECTED (no_speech_prob: {avg_no_speech:.2f})")
                print(f"   [NLP] Skipping language/lyrics analysis for instrumental track.")
                return {
                    "language": "none",
                    "original_text": "",
                    "english_translation": "",
                    "is_instrumental": True,
                    "no_speech_prob": float(avg_no_speech)
                }
            
            language = result_transcribe["language"]
            
            # Reconstruct text line-by-line from segments instead of a flat string
            if segments:
                original_text = "\n".join([s.get("text", "").strip() for s in segments if s.get("text", "").strip()])
            else:
                original_text = result_transcribe.get("text", "").strip()
            
            print(f"   [NLP] Detected Language: {language}")
            
            # If language is not english, translate for keyword matching
            english_translation = original_text
            if language != "en" and len(original_text) > 2:
                print(f"   [NLP] Translating {language} to English via Google Translate...")
                from deep_translator import GoogleTranslator
                try:
                    translator = GoogleTranslator(source='auto', target='en')
                    english_translation = translator.translate(original_text)
                except Exception as e:
                    print(f"   [NLP] Translation warning: {e}")
                    
            return {
                "language": language,
                "original_text": original_text,
                "english_translation": english_translation,
                "is_instrumental": False,
                "no_speech_prob": float(avg_no_speech)
            }
            
        except Exception as e:
            print(f"❌ NLP Extraction Error: {e}")
            return {
                "language": "unknown",
                "original_text": "",
                "english_translation": ""
            }

if __name__ == "__main__":
    # Test block
    import sys
    if len(sys.argv) > 1:
        extractor = NLPExtractor()
        res = extractor.extract_text_and_language(sys.argv[1], max_duration=30)
        print("Result:", res)
    else:
        print("Usage: py -3.11 nlp_extractor.py <audio_file>")
