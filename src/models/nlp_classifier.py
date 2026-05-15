import numpy as np
import re

class NLPClassifier:
    """
    Adjusts the acoustic ensemble probabilities based on text, language, and cultural themes.
    This is a rule-based expert system that acts as a final 'Multiplier Layer'.
    """
    
    def __init__(self, genres: list):
        self.genres = genres
        self.genre_to_idx = {g: i for i, g in enumerate(genres)}
        
        # 1. Linguistic Multipliers (if language == X, multiply genre Y by Z)
        # Note: These are now "Baseline" language boosts. The real magic happens in vibe_rules.
        self.language_rules = {
            "ko": [("k_pop", 4.0)],
            "es": [("reggaeton_latin", 4.0)],
            "fr": [("indie_pop", 1.5), ("classic_jazz", 1.2)],
            "ru": [("post_punk", 2.0), ("darksynth", 1.5)],
            "de": [("house_techno", 2.0), ("modern_metal", 1.5)]
        }
        
        # 2. Vibe/Emotion Multipliers + Language Combinations
        self.vibe_rules = {
            "energetic": [("house_techno", 1.5), ("mainstream_pop", 1.5), ("power_metal", 1.5), ("trap", 1.5)],
            "sad": [("midwestern_emo", 2.5), ("indie_pop", 2.0), ("lofi_chillhop", 1.5), ("grunge", 1.5)],
            "melancholic": [("city_pop", 2.0), ("indie_pop", 1.5), ("post_punk", 2.0), ("lofi_chillhop", 1.5)],
            "motivating": [("anime_ost", 2.0), ("power_metal", 2.0), ("modern_metal", 1.5)],
            "epic": [("anime_ost", 2.5), ("power_metal", 2.0)],
            "aggressive": [("punk_hardcore", 2.0), ("modern_metal", 2.0), ("drill", 2.0), ("trap", 1.5)],
            "angry": [("modern_metal", 2.0), ("punk_hardcore", 2.0), ("drill", 1.5)],
            "chill": [("lofi_chillhop", 2.5), ("smooth_jazz", 2.5), ("city_pop", 1.5), ("reggae", 2.0)],
            "dark": [("darksynth", 2.5), ("post_punk", 2.0), ("phonk", 2.0)],
            "sexy": [("classic_rnb", 2.5), ("smooth_jazz", 1.5), ("reggaeton_latin", 1.5)],
            "nostalgic": [("synthwave", 2.0), ("city_pop", 2.0), ("classic_rock", 1.5), ("disco", 2.0)],
            "playful": [("funk", 2.0), ("disco", 2.0), ("hyperpop", 2.0)],
        }
        
        # Cultural Overrides (Language + Vibe combos)
        # This solves the "If Japanese and Sad -> City Pop, If Japanese and Energetic -> Anime OST" issue
        self.cultural_overrides = {
            "ja": {
                "sad": [("city_pop", 4.0), ("j_rock", 1.5), ("anime_ost", 0.5)], # Penalize anime, boost city_pop
                "melancholic": [("city_pop", 4.0), ("lofi_chillhop", 2.0), ("anime_ost", 0.5)],
                "chill": [("city_pop", 3.0), ("lofi_chillhop", 2.0), ("anime_ost", 0.5)],
                "nostalgic": [("city_pop", 4.0), ("j_rock", 1.5)],
                
                "energetic": [("anime_ost", 4.0), ("j_rock", 3.0), ("power_metal", 2.0)],
                "motivating": [("anime_ost", 5.0), ("j_rock", 3.0)],
                "epic": [("anime_ost", 5.0), ("j_rock", 2.0)],
                "aggressive": [("j_rock", 3.0), ("modern_metal", 2.0)],
                "playful": [("hyperpop", 3.0), ("anime_ost", 2.0)]
            }
        }
        
        # 2. Thematic Multipliers (if english_text contains keyword X, multiply genre Y by Z)
        # Using regex to quickly find words
        self.theme_rules = {
            "anime_hero": {
                "keywords": ["fight", "dream", "believe", "shadow", "future", "light", "power", "together", "friend", "never give up", "sky", "wind"],
                "boosts": [("anime_ost", 2.0), ("j_rock", 1.5), ("power_metal", 1.5)] 
            },
            "hiphop_culture": {
                "keywords": ["nigga", "bitch", "money", "block", "hood", "street", "hustle", "trap", "glock", "shoot", "fuck"],
                "boosts": [("oldschool_hiphop", 2.5), ("trap", 2.5), ("drill", 2.5), ("cloud_rap", 2.0)]
            },
            "metal_angst": {
                "keywords": ["blood", "pain", "die", "death", "kill", "scream", "burn", "flesh", "soul", "darkness", "hell"],
                "boosts": [("modern_metal", 2.0), ("punk_hardcore", 1.5), ("grunge", 1.5)]
            },
            "emo_sadness": {
                "keywords": ["tears", "cry", "alone", "lonely", "miss you", "broken", "heart", "sad", "goodbye"],
                "boosts": [("midwestern_emo", 2.0), ("lofi_chillhop", 1.5), ("indie_pop", 1.5)]
            },
            "club_dance": {
                "keywords": ["dance", "club", "party", "bass", "dj", "tonight", "rhythm", "shake", "move"],
                "boosts": [("house_techno", 2.0), ("mainstream_pop", 1.5), ("reggaeton_latin", 1.5)]
            }
        }

    def adjust_probabilities(self, acoustic_probs: np.ndarray, nlp_data: dict, vibe_data: dict = None) -> np.ndarray:
        """
        Takes the base probabilities from ResNet+MLP, the NLP text data, and Vibe data.
        Returns newly balanced probabilities.
        """
        if acoustic_probs is None or not nlp_data:
            return acoustic_probs
            
        final_probs = acoustic_probs.copy()
        language = nlp_data.get("language", "unknown")
        text = nlp_data.get("english_translation", "").lower()
        
        vibe_1 = vibe_data.get("vibe_1") if vibe_data else None
        
        if not text and not language and not vibe_1:
            return final_probs
            
        print(f"\n🧠 [NLP Engine] Applying cultural & emotional adjustments...")
        
        # 1. Apply Baseline Language Boosts
        if language in self.language_rules:
            rules = self.language_rules[language]
            print(f"   -> Baseline Language '{language}' detected. Boosting: {[g[0] for g in rules]}")
            for genre, multiplier in rules:
                if genre in self.genre_to_idx:
                    idx = self.genre_to_idx[genre]
                    base_prob = max(final_probs[idx], 0.05) 
                    final_probs[idx] = base_prob * multiplier
                    
        # 2. Apply Vibe / Emotion Boosts
        if vibe_1 and vibe_1 in self.vibe_rules:
            rules = self.vibe_rules[vibe_1]
            print(f"   -> Emotional Vibe '{vibe_1}' detected. Boosting: {[g[0] for g in rules]}")
            for genre, multiplier in rules:
                if genre in self.genre_to_idx:
                    idx = self.genre_to_idx[genre]
                    base_prob = max(final_probs[idx], 0.05) 
                    final_probs[idx] = base_prob * multiplier
                    
        # 3. Apply Deep Cultural Overrides 
        # (e.g., Japanese + Sad = City Pop, NOT Anime OST)
        if language in self.cultural_overrides and vibe_1 in self.cultural_overrides[language]:
            rules = self.cultural_overrides[language][vibe_1]
            print(f"   -> 🎯 CULTURAL OVERRIDE: [{language} + {vibe_1}]. Applying specific multipliers: {[g[0] for g in rules]}")
            for genre, multiplier in rules:
                if genre in self.genre_to_idx:
                    idx = self.genre_to_idx[genre]
                    base_prob = max(final_probs[idx], 0.05)
                    final_probs[idx] = base_prob * multiplier
                    
        # 2. Apply Thematic Boosts
        if text:
            for theme_name, theme_data in self.theme_rules.items():
                keywords = theme_data["keywords"]
                boosts = theme_data["boosts"]
                
                # Check how many keywords match
                matches = sum(1 for kw in keywords if re.search(r'\b' + kw + r'\b', text))
                if matches > 0:
                    # The more keywords match, the stronger the boost
                    strength = 1.0 + (matches * 0.2) 
                    print(f"   -> Theme '{theme_name}' detected ({matches} matches). Boosting: {[g[0] for g in boosts]} by x{strength:.1f}")
                    
                    for genre, base_multiplier in boosts:
                        if genre in self.genre_to_idx:
                            idx = self.genre_to_idx[genre]
                            base_prob = max(final_probs[idx], 0.02)
                            final_probs[idx] = base_prob * (base_multiplier * strength)
                            
        # 3. Normalize back to probability distribution (sum = 1 or relative percentages)
        # However, since we display individual sigmoid outputs usually, we don't strictly need to sum to 1.
        # But to keep things readable (0-100%), we can scale it back if it exceeds 1.0
        max_val = np.max(final_probs)
        if max_val > 1.0:
            final_probs = final_probs / max_val
            
        return final_probs
