import random

# Word lists (using the expanded lists from the previous version)
adjectives = [
    'purple', 'fluffy', 'transparent', 'melodic', 'curious', 'ethereal', 'quantum', 'whimsical',
    'iridescent', 'nebulous', 'effervescent', 'serendipitous', 'gossamer', 'phantasmagorical', 'labyrinthine',
    'clandestine', 'ephemeral', 'mercurial', 'quixotic', 'surreptitious', 'verdant', 'zany', 'bioluminescent',
    'chromatic', 'diaphanous', 'effulgent', 'frenetic', 'gossamer', 'holographic', 'incandescent', 'juxtaposed',
    'kaleidoscopic', 'luminescent', 'multifaceted', 'numinous', 'opalescent', 'prismatic', 'quiescent', 'rhapsodic'
]

nouns = [
    'photograph', 'teacup', 'galaxy', 'cucumber', 'notebook', 'elephant', 'bucket', 'apocalypse',
    'kaleidoscope', 'zephyr', 'quasar', 'epiphany', 'chrysalis', 'nebula', 'aurora',
    'anomaly', 'bioluminescence', 'cacophony', 'doppelganger', 'enigma', 'fractal', 'gossamer', 'hologram',
    'illusion', 'juxtaposition', 'kismet', 'labyrinth', 'miasma', 'nexus', 'obelisk', 'phantasm', 'quagmire',
    'reverie', 'synesthesia', 'talisman', 'umbra', 'vortex', 'wunderkammer', 'xenolith', 'yggdrasil', 'zeitgeist'
]

abstract_concepts = [
    'happiness', 'silence', 'dreams', 'time', 'nostalgia', 'serendipity',
    'entropy', 'synchronicity', 'infinity', 'déjà vu', 'zeitgeist', 'catharsis',
    'ambivalence', 'cognizance', 'duende', 'ephemera', 'frisson', 'gestalt', 'hiraeth', 'ineffable',
    'jouissance', 'kairos', 'liminality', 'melancholia', 'numinous', 'oneiric', 'petrichor', 'qualia',
    'saudade', 'tacit', 'ubuntu', 'verisimilitude', 'weltschmerz', 'xenial', 'yugen', 'zanshin'
]

verbs_ing = [
    'dancing', 'whispering', 'evaporating', 'shimmering', 'undulating', 'pirouetting',
    'oscillating', 'metamorphosing', 'percolating', 'effervescing', 'phosphorescing', 'transcending',
    'amalgamating', 'bifurcating', 'coalescing', 'dissipating', 'emanating', 'fluctuating', 'gyrating',
    'harmonizing', 'illuminating', 'juxtaposing', 'kaleidoscoping', 'levitating', 'meandering', 'nebulizing',
    'oscillating', 'pulsating', 'quickening', 'radiating', 'syncopating', 'tessellating', 'undulating'
]

plural_nouns = [
    'rainbows', 'whispers', 'echoes', 'melodies', 'constellations', 'paradoxes',
    'fractals', 'epiphanies', 'dimensions', 'paradigms', 'supernovae', 'hallucinations',
    'aberrations', 'bioluminescences', 'cadenzas', 'dichotomies', 'effulgences', 'fractals', 'glissandos',
    'harmonics', 'iridescences', 'juxtapositions', 'kinesthesias', 'luminescences', 'mnemonics', 'nebulae',
    'oscillations', 'phantasmagorias', 'quintessences', 'resonances', 'synapses', 'tessellations', 'umbrae'
]

locations = [
    'ocean', 'library', 'cloud', 'blackhole', 'labyrinth', 'mirage',
    'nebula', 'wormhole', 'quantum realm', 'parallel universe', 'dreamscape', 'tesseract',
    'astral plane', 'borealis', 'catacombs', 'dimension', 'etherscape', 'fractal forest', 'geode cavern',
    'holodeck', 'interdimensional nexus', 'jellyfish fields', 'kinetic sculpture garden', 'lost city',
    'möbius strip', 'neutron star', 'opalescent oasis', 'pocket universe', 'quantum foam', 'rift valley',
    'singularity', 'time vortex', 'umbral plane', 'void', 'warp zone', 'xenosphere', 'yggdrasil branches'
]

animals = [
    'octopus', 'phoenix', 'unicorn', 'dragon', 'chimera', 'kraken',
    'leviathan', 'basilisk', 'manticore', 'ouroboros', 'hydra', 'thunderbird',
    'axolotl', 'behemoth', 'cthulhu', 'djinn', 'eldritch horror', 'fae', 'gorgon', 'hippogriff',
    'ifrit', 'jabberwocky', 'kitsune', 'leviathan', 'mothman', 'naga', 'oni', 'pegasus',
    'quetzalcoatl', 'roc', 'selkie', 'typhon', 'undine', 'valkyrie', 'wendigo', 'xing tian', 'yeti'
]

verbs = [
    'paints', 'sculpts', 'weaves', 'distills', 'telepathically transmits', 'quantum entangles',
    'transmutes', 'conjures', 'manifests', 'harmonizes', 'transcribes', 'illuminates',
    'alchemizes', 'bifurcates', 'catalyzes', 'deconstructs', 'etherealizes', 'fractalizes', 'galvanizes',
    'harmonizes', 'illuminates', 'juxtaposes', 'kaleidoscopes', 'levitates', 'metamorphosizes', 'nebulizes',
    'oscillates', 'phantasmagorizes', 'quantizes', 'refracts', 'synergizes', 'tessellates', 'unravels'
]

# Multiple templates
templates = [
    "In a {adj1} {location}, {plural_noun1} of {abstract1} are {verb_ing}, creating a {noun1} of {adj2} {plural_noun2}.",
    
    "The {adj1} {animal} {verb} a {noun1} made of {plural_noun1}, while {adj2} {plural_noun2} {verb_ing} in the distance.",
    
    "A {adj1} {noun1} of {abstract1} {verb_ing} on {plural_noun1} in a {location} made of {plural_noun2}. "
    "The {abstract1} {plural_noun3} are {adj2} and {adj3}, {verb_ing2} the {plural_noun4} of {noun2}.",
    
    "{Adj1} {plural_noun1} {verb} the {noun1} of {abstract1}, as {adj2} {animals} {verb_ing} through a {location} of {plural_noun2}.",
    
    "In the depths of a {adj1} {location}, a {noun1} of {abstract1} {verb_ing} eternally, "
    "surrounded by {adj2} {plural_noun1} and {adj3} {plural_noun2} that {verb} the very fabric of {abstract2}."
]

def generate_nonsense_prompt():
    template = random.choice(templates)
    
    return template.format(
        adj1=random.choice(adjectives),
        adj2=random.choice(adjectives),
        adj3=random.choice(adjectives),
        noun1=random.choice(nouns),
        noun2=random.choice(nouns),
        abstract1=random.choice(abstract_concepts),
        abstract2=random.choice(abstract_concepts),
        verb_ing=random.choice(verbs_ing),
        verb_ing2=random.choice(verbs_ing),
        plural_noun1=random.choice(plural_nouns),
        plural_noun2=random.choice(plural_nouns),
        plural_noun3=random.choice(plural_nouns),
        plural_noun4=random.choice(plural_nouns),
        location=random.choice(locations),
        animal=random.choice(animals),
        animals=random.choice(animals),
        verb=random.choice(verbs),
        Adj1=random.choice(adjectives).capitalize()
    )

# Generate and print 5 nonsensical prompts
#for i in range(1):
    #print(f"Nonsensical Prompt {i+1}:")
    #print(generate_nonsense_prompt())
    #print()

def fetch_random_prompt():
    return f"{generate_nonsense_prompt()}"