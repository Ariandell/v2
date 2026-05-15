import warnings
from transformers import pipeline
import torch

class VibeExtractor:
    def __init__(self, device=None):
        if device is None:
            self.device = 0 if torch.cuda.is_available() else -1
        else:
            self.device = 0 if device == "cuda" else -1
            
        print("🎭 Loading Vibe Engine (Zero-Shot Classifier)...")
        # DistilBERT is fast and lightweight (~260MB) for text classification
        self.classifier = pipeline(
            "zero-shot-classification", 
            model="typeform/distilbert-base-uncased-mnli", 
            device=self.device
        )
        
        # The user's requested 15 emotional/vibe labels
        self.vibes = [
            "energetic", "sad", "motivating", "melancholic", "playful", 
            "aggressive", "romantic", "chill", "dark", "uplifting",
            "angry", "dreamy", "epic", "nostalgic", "sexy"
        ]
        
    def get_vibe(self, text: str):
        if not text or len(text.strip()) < 3:
            return None
            
        print("   [NLP] Extracting emotional vibe from lyrics...")
        try:
            res = self.classifier(text, candidate_labels=self.vibes)
            # Return top 2 vibes and their confidence scores
            top_vibes = {
                "vibe_1": res["labels"][0], "score_1": res["scores"][0],
                "vibe_2": res["labels"][1], "score_2": res["scores"][1]
            }
            print(f"   [NLP] Primary Vibe: {top_vibes['vibe_1']} ({top_vibes['score_1']*100:.1f}%)")
            print(f"   [NLP] Secondary Vibe: {top_vibes['vibe_2']} ({top_vibes['score_2']*100:.1f}%)")
            return top_vibes
        except Exception as e:
            print(f"   [NLP] Vibe classification failed: {e}")
            return None
