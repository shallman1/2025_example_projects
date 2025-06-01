# analysis/detections.py

import json
from typing import List, Tuple, Dict, Set
from pathlib import Path
from functools import lru_cache
import jellyfish
import unicodedata
import idna

class DetectionMethods:
    def _initialize_substitutions(self) -> Dict[str, Set[str]]:
        """Initialize character substitution mappings from file without using confusables."""
        try:
            script_dir = Path(__file__).parent
            subs_file = script_dir / 'character_substitutions.txt'
            
            with open(subs_file, 'r', encoding='utf-8') as f:
                basic_subs = json.load(f)
            basic_subs = {k: set(v) for k, v in basic_subs.items()}
        except Exception as e:
            print(f"Warning: Could not load substitutions file: {e}")
            basic_subs = {
                'a': {'4', '@'},
                'i': {'1', '!'},
                'o': {'0'},
                'l': {'1', '|'},
                's': {'5', '$'}
            }
        
        complete_subs = {}
        for char, substitutes in basic_subs.items():
            valid_subs = {s for s in substitutes if s}
            complete_subs[char] = valid_subs

            for sub in valid_subs:
                if sub not in complete_subs:
                    complete_subs[sub] = {char}
                else:
                    complete_subs[sub].add(char)
        
        return complete_subs

    @staticmethod
    @lru_cache(maxsize=1024)
    def normalize_text(text: str) -> str:
        """Normalize text with caching."""
        try:
            if text.startswith('xn--'):
                text = idna.decode(text)
            text = unicodedata.normalize('NFKD', text)
            text = ''.join(c for c in text if not unicodedata.combining(c))
            return text.lower()
        except Exception:
            return text.lower()

    def generate_variants(self, text: str) -> frozenset:
        """Generate variants using selective substitution."""
        substitutions = self.substitutions

        @lru_cache(maxsize=1024)
        def _generate_variants_cached(text: str) -> frozenset:
            if not text:
                return frozenset([''])
            char = text[0]
            rest_variants = _generate_variants_cached(text[1:])

            if len(rest_variants) > 1000:
                return frozenset(char + variant for variant in rest_variants)

            if char not in substitutions:
                return frozenset(char + variant for variant in rest_variants)

            return frozenset(
                sub + rest
                for sub in substitutions[char] | {char}
                for rest in rest_variants
                if len(sub + rest) <= len(text) + 3
            )

        return _generate_variants_cached(text)

    def check_substitutions(self, labels: List[str]) -> List[Tuple[str, str, float]]:
        """Optimized substitution checking."""
        results = []
        normalized_labels = [self.normalize_text(label) for label in labels]

        for i, label in enumerate(normalized_labels):
            label_variants = self.generate_variants(label)

            for target, target_variants in self.target_variants.items():
                if label_variants & target_variants:
                    results.append((
                        target,
                        f"Character substitution match in label: {labels[i]} ↔ {target}",
                        0.9
                    ))
                    break

        return results

    def check_direct_match(self, labels: List[str]) -> List[Tuple[str, str, float]]:
        """Optimized direct matching."""
        results = []
        normalized_labels = [self.normalize_text(label) for label in labels]

        for i, label in enumerate(normalized_labels):
            for target in self.target_terms:
                if target in label:
                    results.append((target, f"Direct match in label: {labels[i]}", 1.0))

        return results

    @lru_cache(maxsize=1024)
    def levenshtein_distance(self, s1: str, s2: str) -> int:
        """Cached Levenshtein distance calculation."""
        return jellyfish.levenshtein_distance(s1, s2)

    def check_levenshtein_distance(self, labels: List[str]) -> List[Tuple[str, str, float]]:
        """Optimized Levenshtein distance checking."""
        results = []
        normalized_labels = [self.normalize_text(label) for label in labels]

        for i, label in enumerate(normalized_labels):
            for target in self.target_terms:
                distance = self.levenshtein_distance(label, target)
                if distance <= self.max_levenshtein_distance:
                    similarity = 1 - (distance / max(len(label), len(target)))
                    results.append((
                        target,
                        f"Similar to {labels[i]} (Levenshtein distance: {distance})",
                        similarity
                    ))

        return results

    def check_neighboring_labels(self, labels: List[str]) -> List[Tuple[str, str, float]]:
        """
        Check for matches in groups of neighboring labels with improved accuracy.
        Only combines adjacent labels that might form a legitimate compound term.
        """
        if len(labels) < 2:
            return []

        results = []
        normalized_labels = [self.normalize_text(label) for label in labels]

        # First pass: look for exact matches across neighboring labels
        for size in [2, 3]:
            for i in range(len(normalized_labels) - size + 1):
                group_labels = labels[i:i + size]
                group_normalized = normalized_labels[i:i + size]

                # Try different combination patterns
                combinations = [
                    ''.join(group_normalized),  # Direct combination
                    '.'.join(group_normalized),  # With dots
                    '-'.join(group_normalized)   # With hyphens
                ]

                original_group = '.'.join(group_labels)

                for target in self.target_terms:
                    # Only consider it a match if the entire target is found
                    # and the boundaries align with label boundaries
                    for combo in combinations:
                        if target == combo:  # Exact match only
                            results.append((
                                target,
                                f"Found in neighboring labels: {original_group}",
                                1.0
                            ))
                            break

        return results
