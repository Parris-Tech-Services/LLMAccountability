import re
import hashlib
from typing import List, Dict, Any

CLAIM_PATTERNS = {
    "tests-pass": [r"(?i)tests pass", r"(?i)all tests passed", r"(?i)automated tests passed"],
    "pushed": [r"(?i)pushed (?:to|v\\d+)", r"(?i)push to main", r"(?i)pushed (.*) to github"],
    "no-secrets": [r"(?i)no secrets were committed"],
    "security-reviewed": [r"(?i)secure", r"(?i)authentication is secure"],
    "fully-complete": [r"(?i)fully complete", r"(?i)production ready", r"(?i)every requirement is implemented"]
}

class ClaimExtractor:
    @staticmethod
    def extract(text: str, report_id: str = "default_report") -> List[Dict[str, Any]]:
        claims = []
        for claim_type, patterns in CLAIM_PATTERNS.items():
            # One semantic claim per type and report. Regexes overlap: for
            # example, "automated tests passed" matches several test patterns.
            # Only breaking the inner matches loop creates duplicate IDs and
            # inflates claimed success rates.
            match = next(
                (found for pattern in patterns
                 if (found := re.search(pattern, text)) is not None),
                None,
            )
            if match is None:
                continue
            raw_text = match.group(0)
            canonical = f"{report_id}:{claim_type}:{raw_text}:0"
            claim_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
            claims.append({"id": claim_id, "type": claim_type, "raw_text": raw_text})
        return claims
