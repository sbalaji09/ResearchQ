from dataclasses import dataclass, field
from typing import List, Dict, Set

@dataclass
class DomainConfig:
    name: str

    section_patterns: List[tuple] = field(default_factory=list)

    skip_sections: Set[str] = field(default_factory=set)

    abbreviations: Set[str] = field(default_factory=set)

    important_keywords: Set[str] = field(default_factory=set)

    min_chunk_size: int = 100
    max_chunk_size: int = 400

    preserve_tables: bool = True
    preserve_equations: bool = False
    preserve_code_blocks: bool = False

    synthetic_sections: List[str] = field(default_factory=list)

MEDICAL_CONFIG = DomainConfig(
    name="medical",
    section_patterns=[
        (r'^\s*patient\s+demographics?\s*$', 'Patient Demographics'),
        (r'^\s*clinical\s+findings?\s*$', 'Clinical Findings'),
        (r'^\s*diagnosis\s*$', 'Diagnosis'),
        (r'^\s*treatment\s*$', 'Treatment'),
        (r'^\s*prognosis\s*$', 'Prognosis'),
        (r'^\s*follow[- ]?up\s*$', 'Follow-up'),
        (r'^\s*adverse\s+events?\s*$', 'Adverse Events'),
        (r'^\s*safety\s*$', 'Safety'),
        (r'^\s*efficacy\s*$', 'Efficacy'),
        (r'^\s*dosage\s*$', 'Dosage'),
        (r'^\s*inclusion\s+criteria\s*$', 'Inclusion Criteria'),
        (r'^\s*exclusion\s+criteria\s*$', 'Exclusion Criteria'),
        (r'^\s*statistical\s+analysis\s*$', 'Statistical Analysis'),
        (r'^\s*ethics?\s*$', 'Ethics'),
        (r'^\s*informed\s+consent\s*$', 'Informed Consent'),
    ],
    skip_sections={'Acknowledgements', 'Funding', 'Disclosures'},
    abbreviations={
        'mg', 'kg', 'ml', 'mcg', 'mmol', 'umol',
        'bid', 'tid', 'qid', 'prn', 'po', 'iv', 'im', 'sc',
        'bp', 'hr', 'rr', 'temp', 'spo2', 'bmi',
        'ct', 'mri', 'ecg', 'ekg', 'eeg',
        'hba1c', 'ldl', 'hdl', 'ast', 'alt', 'gfr',
        'ci', 'or', 'rr', 'hr', 'auc', 'itt', 'pp',
    },
    important_keywords={
        'significant', 'p-value', 'p <', 'confidence interval',
        'primary endpoint', 'secondary endpoint',
        'adverse event', 'side effect', 'mortality', 'survival',
        'efficacy', 'safety', 'dosage', 'treatment',
    },
    preserve_tables=True,
    synthetic_sections=['Clinical Findings', 'Treatment', 'Efficacy', 'Safety'],
)


COMPUTER_SCIENCE_CONFIG = DomainConfig(
    name="computer_science",
    section_patterns=[
        (r'^\s*algorithm\s*$', 'Algorithm'),
        (r'^\s*implementation\s*$', 'Implementation'),
        (r'^\s*evaluation\s*$', 'Evaluation'),
        (r'^\s*benchmarks?\s*$', 'Benchmarks'),
        (r'^\s*experiments?\s*$', 'Experiments'),
        (r'^\s*architecture\s*$', 'Architecture'),
        (r'^\s*system\s+design\s*$', 'System Design'),
        (r'^\s*performance\s*$', 'Performance'),
        (r'^\s*complexity\s*$', 'Complexity'),
        (r'^\s*datasets?\s*$', 'Datasets'),
        (r'^\s*baselines?\s*$', 'Baselines'),
        (r'^\s*ablation\s+stud(y|ies)\s*$', 'Ablation Study'),
        (r'^\s*hyperparameters?\s*$', 'Hyperparameters'),
        (r'^\s*training\s*$', 'Training'),
        (r'^\s*inference\s*$', 'Inference'),
    ],
    skip_sections={'Acknowledgements', 'Appendix'},
    abbreviations={
        'api', 'gpu', 'cpu', 'ram', 'ssd', 'hdd',
        'ml', 'dl', 'nn', 'cnn', 'rnn', 'lstm', 'gru', 'bert', 'gpt',
        'llm', 'nlp', 'cv', 'rl', 'gan', 'vae', 'ae',
        'lr', 'sgd', 'adam', 'relu', 'bn', 'ln',
        'acc', 'f1', 'auc', 'mse', 'mae', 'rmse',
        'flops', 'fps', 'ms', 'gb', 'mb', 'kb',
    },
    important_keywords={
        'state-of-the-art', 'sota', 'benchmark', 'baseline',
        'accuracy', 'precision', 'recall', 'f1',
        'training time', 'inference time', 'latency',
        'parameters', 'flops', 'memory',
        'outperforms', 'improves', 'achieves',
    },
    preserve_code_blocks=True,
    preserve_equations=True,
    max_chunk_size=500,  # Larger for code blocks
    synthetic_sections=['Algorithm', 'Performance', 'Evaluation'],
)


LEGAL_CONFIG = DomainConfig(
    name="legal",
    section_patterns=[
        (r'^\s*facts?\s*$', 'Facts'),
        (r'^\s*issue[s]?\s*$', 'Issues'),
        (r'^\s*holding\s*$', 'Holding'),
        (r'^\s*reasoning\s*$', 'Reasoning'),
        (r'^\s*rule\s*$', 'Rule'),
        (r'^\s*analysis\s*$', 'Analysis'),
        (r'^\s*conclusion\s*$', 'Conclusion'),
        (r'^\s*background\s*$', 'Background'),
        (r'^\s*procedural\s+history\s*$', 'Procedural History'),
        (r'^\s*standard\s+of\s+review\s*$', 'Standard of Review'),
        (r'^\s*dissent\s*$', 'Dissent'),
        (r'^\s*concurrence\s*$', 'Concurrence'),
    ],
    skip_sections={'Footnotes'},
    abbreviations={
        'v', 'vs', 'cf', 'id', 'ibid', 'supra', 'infra',
        'u.s', 'f.2d', 'f.3d', 's.ct', 'l.ed',
        'p', 'pp', 'no', 'nos', 'vol',
        'art', 'sec', 'para', 'cl',
        'corp', 'inc', 'llc', 'llp',
    },
    important_keywords={
        'held', 'ruling', 'decision', 'judgment',
        'plaintiff', 'defendant', 'appellant', 'appellee',
        'statute', 'regulation', 'precedent',
        'affirmed', 'reversed', 'remanded',
    },
    min_chunk_size=150,  # Legal text needs more context
    max_chunk_size=500,
    synthetic_sections=['Holding', 'Rule', 'Reasoning'],
)


SCIENTIFIC_CONFIG = DomainConfig(
    name="scientific",
    section_patterns=[
        (r'^\s*hypothesis\s*$', 'Hypothesis'),
        (r'^\s*experimental\s+design\s*$', 'Experimental Design'),
        (r'^\s*data\s+collection\s*$', 'Data Collection'),
        (r'^\s*data\s+analysis\s*$', 'Data Analysis'),
        (r'^\s*observations?\s*$', 'Observations'),
        (r'^\s*measurements?\s*$', 'Measurements'),
        (r'^\s*calculations?\s*$', 'Calculations'),
        (r'^\s*error\s+analysis\s*$', 'Error Analysis'),
        (r'^\s*conclusions?\s*$', 'Conclusion'),
    ],
    abbreviations={
        'mol', 'mmol', 'umol', 'nm', 'um', 'mm', 'cm', 'm', 'km',
        'mg', 'g', 'kg', 'ml', 'l', 'pa', 'kpa', 'mpa',
        'j', 'kj', 'mj', 'w', 'kw', 'mw', 'hz', 'khz', 'mhz', 'ghz',
        'k', 'c', 'f', 'ph', 'ppm', 'ppb',
        'std', 'sd', 'se', 'sem', 'anova', 'ci',
    },
    important_keywords={
        'significant', 'p <', 'p-value', 'hypothesis',
        'correlation', 'coefficient', 'r-squared',
        'standard deviation', 'error', 'uncertainty',
        'concentration', 'temperature', 'pressure',
    },
    preserve_tables=True,
    preserve_equations=True,
    synthetic_sections=['Hypothesis', 'Results', 'Conclusion'],
)


# Default config for general academic papers
DEFAULT_CONFIG = DomainConfig(
    name="general",
    section_patterns=[],
    synthetic_sections=['Key Findings', 'Methods Summary'],
)


# Registry of all configs
DOMAIN_CONFIGS = {
    "medical": MEDICAL_CONFIG,
    "computer_science": COMPUTER_SCIENCE_CONFIG,
    "cs": COMPUTER_SCIENCE_CONFIG,
    "legal": LEGAL_CONFIG,
    "law": LEGAL_CONFIG,
    "scientific": SCIENTIFIC_CONFIG,
    "science": SCIENTIFIC_CONFIG,
    "general": DEFAULT_CONFIG,
    "default": DEFAULT_CONFIG,
}

def get_domain_config(domain: str) -> DomainConfig:
    return DOMAIN_CONFIGS.get(domain.lower(), DEFAULT_CONFIG)

def detect_domain(text: str) -> str:
    text_lower = text.lower()

    scores = {
        "medical": 0,
        "computer_science": 0,
        "legal": 0,
        "scientific": 0,
    }

    # medial indicators
    medical_terms = ['patient', 'clinical', 'treatment', 'diagnosis', 'mg', 'dosage', 
                     'adverse event', 'efficacy', 'placebo', 'randomized']
    for term in medical_terms:
        scores["medical"] += text_lower.count(term)

    # CS indicators
    cs_terms = ['algorithm', 'neural network', 'training', 'model', 'dataset',
                'accuracy', 'benchmark', 'gpu', 'parameters', 'epoch']
    for term in cs_terms:
        scores["computer_science"] += text_lower.count(term)
    
    # Legal indicators
    legal_terms = ['plaintiff', 'defendant', 'court', 'statute', 'ruling',
                   'judgment', 'appeal', 'held', 'law', 'legal']
    for term in legal_terms:
        scores["legal"] += text_lower.count(term)
    
    # Scientific indicators
    science_terms = ['experiment', 'hypothesis', 'measurement', 'concentration',
                     'reaction', 'sample', 'specimen', 'laboratory']
    for term in science_terms:
        scores["scientific"] += text_lower.count(term)
    
    # return domain with the highest score or if they are all low, return general
    max_domain = max(scores, key=scores.get)
    if scores[max_domain] < 5:
        return "general"
    return max_domain
