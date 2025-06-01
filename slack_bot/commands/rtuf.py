# commands/rtuf.py

import sys
sys.path.append('..')
import requests
import json
import os
from typing import List, Set, Tuple, Dict
from functools import lru_cache
from multiprocessing import Pool
from tqdm import tqdm
from analysis.detections import DetectionMethods

class DomainScanner(DetectionMethods):
    def __init__(self, target_terms: Set[str], max_levenshtein_distance: int = 2, public_suffix_list=None):
        self.target_terms = {self.normalize_text(term) for term in target_terms}
        self.max_levenshtein_distance = max_levenshtein_distance
        if public_suffix_list is not None:
            self.public_suffix_list = public_suffix_list
        else:
            self.public_suffix_list = self._get_public_suffix_list()
        self.substitutions = self._initialize_substitutions()
        self.target_variants = {target: self.generate_variants(target) for target in self.target_terms}

    @staticmethod
    @lru_cache(maxsize=1024)
    def _get_public_suffix_list() -> frozenset:
        try:
            response = requests.get('https://publicsuffix.org/list/public_suffix_list.dat')
            return frozenset(line.strip() for line in response.text.splitlines() if line and not line.startswith('//'))
        except Exception as e:
            print(f"Warning: Could not fetch public suffix list: {e}")
            return frozenset()

    def split_domain(self, fqdn: str) -> List[str]:
        dot_parts = fqdn.split('.')
        all_parts = []
        for part in dot_parts:
            hyphen_parts = part.split('-')
            all_parts.extend(hyphen_parts)
        return [part for part in all_parts if part]

    def extract_domain_parts(self, fqdn: str) -> Tuple[List[str], str]:
        dot_labels = fqdn.lower().split('.')
        for i in range(len(dot_labels)):
            if '.'.join(dot_labels[i:]) in self.public_suffix_list:
                remaining_parts = dot_labels[:-len(dot_labels[i:])]
                suffix = '.'.join(dot_labels[i:])
                detailed_parts = []
                for part in remaining_parts:
                    detailed_parts.extend(part.split('-'))
                return [part for part in detailed_parts if part], suffix
        remaining = dot_labels[:-1]
        detailed_parts = []
        for part in remaining:
            detailed_parts.extend(part.split('-'))
        return [part for part in detailed_parts if part], dot_labels[-1]

    def scan_domain(self, fqdn: str) -> List[Tuple[str, str, float]]:
        domain_parts, tld = self.extract_domain_parts(fqdn)
        if not domain_parts:
            return []
        results = []
        direct_matches = self.check_direct_match(domain_parts)
        if direct_matches:
            results.extend(direct_matches)
        subst_matches = self.check_substitutions(domain_parts)
        if subst_matches:
            results.extend(subst_matches)
        if not results:
            neighbor_matches = self.check_neighboring_labels(domain_parts)
            if neighbor_matches:
                results.extend(neighbor_matches)
            if not results:
                lev_matches = self.check_levenshtein_distance(domain_parts)
                if lev_matches:
                    results.extend(lev_matches)
        return sorted(results, key=lambda x: x[2], reverse=True)

def init_worker(target_terms, public_suffix_list):
    global scanner
    scanner = DomainScanner(target_terms, public_suffix_list=public_suffix_list)

def process_domain(domain):
    results = scanner.scan_domain(domain)
    return (domain, results)

def main():
    target_terms = {'bank'}
    public_suffix_list = DomainScanner._get_public_suffix_list()
    domains = []
    with open('noh.txt', 'r') as f:
        for line in f:
            data = json.loads(line)
            domain = data.get('domain')
            if domain:
                domains.append(domain)
    num_processes = os.cpu_count()
    chunksize = 100
    with open('rtufresults.txt', 'w', encoding='utf-8') as outfile:
        with Pool(processes=num_processes, initializer=init_worker, initargs=(target_terms, public_suffix_list)) as pool:
            results_iter = pool.imap_unordered(process_domain, domains, chunksize=chunksize)
            with tqdm(total=len(domains), desc='Scanning domains') as pbar:
                for domain, results in results_iter:
                    outfile.write(f"\nScanning domain: {domain}\n")
                    outfile.write("-" * 50 + "\n")
                    if results:
                        outfile.write("Potential matches found:\n")
                        for target, description, similarity in results:
                            outfile.write(f"- Target term: {target}\n")
                            outfile.write(f"  Description: {description}\n")
                            outfile.write(f"  Confidence: {similarity:.2%}\n")
                    else:
                        outfile.write("No suspicious patterns found.\n")
                    pbar.update(1)

if __name__ == "__main__":
    main()
