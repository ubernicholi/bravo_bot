import random
from typing import Dict, List, Optional

class FluxPromptGenerator:
    def __init__(self):
        self.quality_tags = [
            "masterpiece", "best quality", "highly detailed", "sharp focus",
            "intricate details", "professional", "8k uhd", "high resolution"
        ]
        
        self.style_tags = {
            'photorealistic': [
                "photorealistic", "hyperrealistic", "photographic", "realistic lighting",
                "volumetric lighting", "subsurface scattering", "ray tracing", "ambient occlusion"
            ],
            'artistic': [
                "concept art", "digital painting", "trending on artstation",
                "octane render", "unreal engine 5", "cinematic", "dynamic composition"
            ],
            'atmosphere': [
                "volumetric fog", "god rays", "atmospheric", "dramatic lighting",
                "studio lighting", "golden hour", "backlit", "rim lighting"
            ]
        }

        # Enhanced templates specifically for FLUX
        self.templates = {
            'scene': [
                "{quality}, {style}, {adj:scale} {location} with {adj:atmosphere} atmosphere, "
                "{adj:lighting} lighting illuminating {adj:material} {plural_noun}, {composition}",
                
                "{quality}, {style}, deep within a {adj:atmosphere} {location}, "
                "where {adj:material} {plural_noun} {verb_ing} through {adj:lighting} spaces, {composition}"
            ],
            'portrait': [
                "{quality}, {style}, portrait of {adj:character} {character:type}, "
                "{adj:lighting} lighting, {adj:atmosphere} atmosphere, {composition}, {camera}",
                
                "{quality}, {style}, close-up portrait, {adj:character} {character:type} with "
                "{adj:material} {noun:feature}, {adj:lighting} lighting, {composition}"
            ],
            'abstract': [
                "{quality}, {style}, {adj:scale} abstract {noun:concept}, "
                "composed of {adj:material} {plural_noun}, {adj:lighting} lighting, {composition}",
                
                "{quality}, {style}, surreal {noun:concept} manifesting as "
                "{adj:material} {plural_noun}, {adj:atmosphere} atmosphere, {composition}"
            ]
        }
        
        # Expanded word categories for FLUX
        self.words = {
            'adj': {
                'scale': ['massive', 'colossal', 'microscopic', 'vast', 'intimate', 'expansive'],
                'atmosphere': ['ethereal', 'misty', 'hazy', 'clear', 'dense', 'foggy', 'mysterious'],
                'lighting': ['soft', 'harsh', 'dramatic', 'diffused', 'directional', 'ambient', 'natural'],
                'material': ['crystalline', 'metallic', 'organic', 'translucent', 'iridescent', 'textured'],
                'character': ['mysterious', 'elegant', 'powerful', 'serene', 'weathered', 'youthful'],
            },
            'composition': [
                'rule of thirds', 'central composition', 'symmetrical composition',
                'diagonal composition', 'leading lines', 'frame within frame'
            ],
            'camera': [
                '85mm lens', 'wide angle lens', 'telephoto lens',
                'macro lens', 'shallow depth of field', 'deep depth of field'
            ],
            'character': {
                'type': ['wanderer', 'warrior', 'scholar', 'mystic', 'artificer', 'sovereign'],
                'feature': ['eyes', 'expression', 'pose', 'garments', 'accessories']
            },
            'noun': {
                'concept': ['dimension', 'reality', 'dreamscape', 'consciousness', 'time'],
                'feature': ['eyes', 'face', 'expression', 'profile', 'silhouette']
            },
            'location': [
                'cathedral', 'quantum realm', 'crystal cave', 'ancient ruins',
                'floating islands', 'cybernetic city', 'ethereal forest'
            ],
            'plural_noun': [
                'fractals', 'particles', 'structures', 'patterns', 'geometries',
                'artifacts', 'elements', 'forms', 'shapes', 'constructs'
            ],
            'verb_ing': [
                'flowing', 'floating', 'drifting', 'shifting', 'transforming',
                'evolving', 'materializing', 'dissolving', 'emerging'
            ]
        }

    def _get_quality_tags(self) -> str:
        """Get a random selection of quality tags"""
        return ", ".join(random.sample(self.quality_tags, k=random.randint(2, 4)))

    def _get_style_tags(self, style_type: Optional[str] = None) -> str:
        """Get style tags either from a specific category or random"""
        if style_type and style_type in self.style_tags:
            tags = self.style_tags[style_type]
        else:
            # Randomly select from all style tags
            tags = [tag for sublist in self.style_tags.values() for tag in sublist]
        return ", ".join(random.sample(tags, k=random.randint(2, 3)))

    def _parse_template_tag(self, tag: str) -> tuple:
        parts = tag.split(':')
        return (parts[0], parts[1]) if len(parts) > 1 else (parts[0], None)

    def _select_word(self, category: str, subcategory: str = None) -> str:
        if subcategory and category in self.words and subcategory in self.words[category]:
            return random.choice(self.words[category][subcategory])
        elif category in self.words:
            if isinstance(self.words[category], dict):
                all_words = [word for subcat in self.words[category].values() 
                           for word in subcat]
                return random.choice(all_words)
            return random.choice(self.words[category])
        return f"<unknown-{category}>"

    def generate_prompt(self, 
                       template_type: str = None, 
                       style_type: str = None,
                       add_weights: bool = True) -> str:
        """
        Generate a prompt with specified template and style type.
        
        Args:
            template_type: Type of template to use ('scene', 'portrait', 'abstract')
            style_type: Type of style to apply ('photorealistic', 'artistic', 'atmosphere')
            add_weights: Whether to add ComfyUI-style weights to key terms
        """
        if not template_type:
            template_type = random.choice(list(self.templates.keys()))
            
        template = random.choice(self.templates[template_type])
        
        # Prepare base substitutions
        substitutions = {
            'quality': self._get_quality_tags(),
            'style': self._get_style_tags(style_type),
            'composition': random.choice(self.words['composition'])
        }
        
        # Fill in the template
        result = template
        while '{' in result:
            start = result.find('{')
            end = result.find('}', start)
            if start == -1 or end == -1:
                break
                
            tag = result[start+1:end]
            category, subcategory = self._parse_template_tag(tag)
            
            if category in substitutions:
                replacement = substitutions[category]
            else:
                replacement = self._select_word(category, subcategory)
                
            # Add weights to important terms if requested
            if add_weights and category in ['adj', 'noun', 'location']:
                replacement = f"({replacement}:1.2)"
                
            result = result[:start] + replacement + result[end+1:]
            
        return result

    def generate_negative_prompt(self) -> str:
        """Generate a standard negative prompt for FLUX"""
        negative_terms = [
            "worst quality", "low quality", "normal quality", "lowres", "blurry",
            "bad anatomy", "bad hands", "cropped", "poorly drawn", "out of frame",
            "mutation", "deformed", "artifact", "watermark", "signature", "extra limbs"
        ]
        return ", ".join(negative_terms)

# Example usage
"""
generator = FluxPromptGenerator()

# Generate different types of prompts
print("\nScene prompt:")
print(generator.generate_prompt('scene', 'photorealistic'))

print("\nPortrait prompt:")
print(generator.generate_prompt('portrait', 'artistic'))

print("\nAbstract prompt:")
print(generator.generate_prompt('abstract', 'atmosphere'))

print("\nNegative prompt:")
print(generator.generate_negative_prompt())
"""