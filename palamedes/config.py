GLOBAL_ALIGN_MODE = "global"

# default alignment params, meant to favor a single Substitution vs some Indel
DEFAULT_MATCH_SCORE = 1
DEFAULT_MISMATCH_SCORE = -1
DEFAULT_OPEN_GAP_SCORE = -1
DEFAULT_EXTEND_GAP_SCORE = -0.1

REF_SEQUENCE_ID = "ref"
ALT_SEQUENCE_ID = "alt"

ALIGNMENT_GAP_CHAR = "-"

VARIANT_BASE_MATCH = "M"
VARIANT_BASE_MISMATCH = "m"
VARIANT_BASE_DELETION = "d"
VARIANT_BASE_INSERTION = "i"

HGVS_VARIANT_TYPE_SUBSTITUTION = "substitution"
HGVS_VARIANT_TYPE_DELETION = "deletion"
HGVS_VARIANT_TYPE_EXTENSION = "extension"
HGVS_VARIANT_TYPE_DUPLICATION = "duplication"
HGVS_VARIANT_TYPE_REPEAT = "repeat"
HGVS_VARIANT_TYPE_INSERTION = "insertion"
HGVS_VARIANT_TYPE_DELETION_INSERTION = "deletion_insertion"

MOLECULE_TYPE_ANNOTATION_KEY = "molecule_type"
MOLECULE_TYPE_PROTEIN = "protein"
HGVS_TYPE_PROTEIN = "p"
MOLCULE_TO_HGVS_TYPE_MAP = {MOLECULE_TYPE_PROTEIN: HGVS_TYPE_PROTEIN}
