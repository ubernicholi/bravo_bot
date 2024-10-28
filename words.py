import random
from typing import Dict, List

# Word lists (using the expanded lists from the previous version)
o_adjectives = [
    'purple', 'fluffy', 'transparent', 'melodic', 'curious', 'ethereal', 'quantum', 'whimsical',
    'iridescent', 'nebulous', 'effervescent', 'serendipitous', 'gossamer', 'phantasmagorical', 'labyrinthine',
    'clandestine', 'ephemeral', 'mercurial', 'quixotic', 'surreptitious', 'verdant', 'zany', 'bioluminescent',
    'chromatic', 'diaphanous', 'effulgent', 'frenetic', 'gossamer', 'holographic', 'incandescent', 'juxtaposed',
    'kaleidoscopic', 'luminescent', 'multifaceted', 'numinous', 'opalescent', 'prismatic', 'quiescent', 'rhapsodic'
]

o_nouns = [
    'photograph', 'teacup', 'galaxy', 'cucumber', 'notebook', 'elephant', 'bucket', 'apocalypse',
    'kaleidoscope', 'zephyr', 'quasar', 'epiphany', 'chrysalis', 'nebula', 'aurora',
    'anomaly', 'bioluminescence', 'cacophony', 'doppelganger', 'enigma', 'fractal', 'gossamer', 'hologram',
    'illusion', 'juxtaposition', 'kismet', 'labyrinth', 'miasma', 'nexus', 'obelisk', 'phantasm', 'quagmire',
    'reverie', 'synesthesia', 'talisman', 'umbra', 'vortex', 'wunderkammer', 'xenolith', 'yggdrasil', 'zeitgeist'
]


o_plural_nouns = [
    'rainbows', 'whispers', 'echoes', 'melodies', 'constellations', 'paradoxes',
    'fractals', 'epiphanies', 'dimensions', 'paradigms', 'supernovae', 'hallucinations',
    'aberrations', 'bioluminescences', 'cadenzas', 'dichotomies', 'effulgences', 'fractals', 'glissandos',
    'harmonics', 'iridescences', 'juxtapositions', 'kinesthesias', 'luminescences', 'mnemonics', 'nebulae',
    'oscillations', 'phantasmagorias', 'quintessences', 'resonances', 'synapses', 'tessellations', 'umbrae'
]

o_verbs = [
    'paints', 'sculpts', 'weaves', 'distills', 'telepathically transmits', 'quantum entangles',
    'transmutes', 'conjures', 'manifests', 'harmonizes', 'transcribes', 'illuminates',
    'alchemizes', 'bifurcates', 'catalyzes', 'deconstructs', 'etherealizes', 'fractalizes', 'galvanizes',
    'harmonizes', 'illuminates', 'juxtaposes', 'kaleidoscopes', 'levitates', 'metamorphosizes', 'nebulizes',
    'oscillates', 'phantasmagorizes', 'quantizes', 'refracts', 'synergizes', 'tessellates', 'unravels'
]


class PromptGenerator:
    def __init__(self):
        # Template categories for different types of scenes
        self.templates = {
            'landscape': [
                "In a {adj:mystical} {location}, {plural_noun} of {abstract} {verb_ing} beneath {adj:celestial} {noun:natural}.",
                "A vast {location} where {adj:ethereal} {plural_noun} {verb} through veils of {abstract}.",
            ],
            'character': [
                "A {adj:personality} {character:being} wielding {adj:material} {noun:object}, surrounded by {adj:atmospheric} {plural_noun}.",
                "{character:profession} with {adj:physical} features {verb_ing} among {adj:emotional} {noun:scene}.",
            ],
            'abstract': [
                "Fragments of {abstract} {verb_ing} into {adj:visual} {plural_noun}, creating {adj:emotional} {noun:concept}.",
                "The essence of {abstract} manifested as {adj:material} {plural_noun} {verb_ing} through {adj:ethereal} space.",
            ],
            'surreal': [
                "{adj:size} {noun:object} floating in a {adj:atmospheric} void, {verb_ing} {abstract} into existence.",
                "A realm where {adj:material} {plural_noun} {verb} the laws of {abstract}.",
            ]
        }
        
        # Enhanced word categories with subcategories
        self.words = {
            'adj': {
                'mystical': ['ethereal', 'arcane', 'mystic', 'enchanted', 'otherworldly'],
                'celestial': ['starlit', 'cosmic', 'celestial', 'astral', 'luminous'],
                'material': ['crystalline', 'metallic', 'wooden', 'golden', 'obsidian'],
                'atmospheric': ['misty', 'foggy', 'stormy', 'serene', 'turbulent'],
                'emotional': ['melancholic', 'joyous', 'peaceful', 'chaotic', 'tranquil'],
                'visual': ['iridescent', 'prismatic', 'glowing', 'shadowy', 'vibrant'],
                'size': ['colossal', 'microscopic', 'towering', 'diminutive', 'vast'],
                'personality': ['wise', 'mysterious', 'ancient', 'youthful', 'powerful'],
                'physical': ['angular', 'fluid', 'fractured', 'seamless', 'organic']
            },
            'noun': {
                'natural': ['mountains', 'oceans', 'forests', 'crystals', 'clouds'],
                'object': ['sphere', 'portal', 'mirror', 'chalice', 'tome'],
                'concept': ['dreamscape', 'memory', 'dimension', 'reality', 'void'],
                'scene': ['sanctuary', 'ruins', 'garden', 'laboratory', 'nexus']
            },
            'character': {
                'profession': ['Alchemist', 'Oracle', 'Wanderer', 'Guardian', 'Scholar'],
                'being': ['Spirit', 'Entity', 'Celestial', 'Shapeshifter', 'Elemental',
                'octopus',  'dragon', 'chimera', 'kraken', 'leviathan', 'basilisk', 
                'axolotl','phoenix', 'unicorn','ouroboros', 'hydra', 'thunderbird','yeti',
                'manticore', 'behemoth', 'cthulhu', 'djinn', 'eldritch horror', 
                'fae', 'gorgon', 'hippogriff', 'ifrit', 'jabberwocky', 'kitsune', 'leviathan', 
                'mothman', 'naga', 'oni', 'pegasus','quetzalcoatl', 'roc', 'selkie', 
                'typhon', 'undine', 'valkyrie', 'wendigo', 'xing tian']
            },
            'location': [
                'crystal cave', 'floating island', 'ancient temple', 'cosmic void', 
                'dream forest', 'quantum realm', 'astral plane', 'forgotten city',
                'ocean', 'library', 'cloud', 'blackhole', 'labyrinth', 'mirage',
                'nebula', 'wormhole', 'quantum realm', 'parallel universe', 'dreamscape', 'tesseract',
                'astral plane', 'borealis', 'catacombs', 'dimension', 'etherscape', 'fractal forest', 'geode cavern',
                'holodeck', 'interdimensional nexus', 'jellyfish fields', 'kinetic sculpture garden', 'lost city',
                'möbius strip', 'neutron star', 'opalescent oasis', 'pocket universe', 'quantum foam', 'rift valley',
                'singularity', 'time vortex', 'umbral plane', 'void', 'warp zone', 'xenosphere', 'yggdrasil branches'
            ],
            'abstract': [
                'time', 'dreams', 'memory', 'consciousness', 'infinity',
                'creation', 'harmony', 'chaos', 'evolution', 'transcendence'
                'happiness', 'silence', 'dreams', 'time', 'nostalgia', 'serendipity',
                'entropy', 'synchronicity', 'infinity', 'déjà vu', 'zeitgeist', 'catharsis',
                'ambivalence', 'cognizance', 'duende', 'ephemera', 'frisson', 'gestalt', 'hiraeth', 'ineffable',
                'jouissance', 'kairos', 'liminality', 'melancholia', 'numinous', 'oneiric', 'petrichor', 'qualia',
                'saudade', 'tacit', 'ubuntu', 'verisimilitude', 'weltschmerz', 'xenial', 'yugen', 'zanshin'
            ],
            'verb_ing': [
                'flowing', 'transforming', 'crystallizing', 'dissolving', 'emanating',
                'resonating', 'materializing', 'fracturing', 'merging', 'ascending',
                'dancing', 'whispering', 'evaporating', 'shimmering', 'undulating', 
                'pirouetting', 'oscillating', 'metamorphosing', 'percolating', 'effervescing',
                'phosphorescing', 'transcending','amalgamating', 'bifurcating', 'coalescing', 
                'dissipating', 'emanating', 'fluctuating', 'gyrating', 'harmonizing', 
                'illuminating', 'juxtaposing', 'kaleidoscoping', 'levitating', 'meandering', 
                'nebulizing', 'oscillating', 'pulsating', 'quickening', 'radiating', 
                'syncopating', 'tessellating', 'undulating'
            ],
            'verb': [
                'transcend', 'manifest', 'embrace', 'weave', 'conjure',
                'illuminate', 'transmute', 'harmonize', 'evolve', 'reshape'
            ],
            'plural_noun': [
                'fractals', 'geometries', 'essences', 'wavelengths', 'dimensions',
                'frequencies', 'paradigms', 'phenomena', 'apparitions', 'metamorphoses'
            ]
        }

    def _parse_template_tag(self, tag: str) -> tuple:
        """Parse template tags like {adj:mystical} or {noun}"""
        parts = tag.split(':')
        return (parts[0], parts[1]) if len(parts) > 1 else (parts[0], None)

    def _select_word(self, category: str, subcategory: str = None) -> str:
        """Select a word from the specified category and subcategory"""
        if subcategory and category in self.words and subcategory in self.words[category]:
            return random.choice(self.words[category][subcategory])
        elif category in self.words:
            if isinstance(self.words[category], dict):
                # If it's a dict of subcategories, flatten and choose from all words
                all_words = [word for subcat in self.words[category].values() 
                           for word in subcat]
                return random.choice(all_words)
            return random.choice(self.words[category])
        return f"<unknown-{category}>"

    def generate_prompt(self, style: str = None) -> str:
        """Generate a prompt with the specified style"""
        # If no style specified, choose random style
        if not style:
            style = random.choice(list(self.templates.keys()))
            
        # Select template from specified style
        template = random.choice(self.templates[style])
        
        # Fill in the template
        result = template
        while '{' in result:
            start = result.find('{')
            end = result.find('}', start)
            if start == -1 or end == -1:
                break
                
            tag = result[start+1:end]
            category, subcategory = self._parse_template_tag(tag)
            replacement = self._select_word(category, subcategory)
            
            result = result[:start] + replacement + result[end+1:]
            
        return result

# Example usage
#generator = PromptGenerator()
#print("Random style prompt:", generator.generate_prompt())