import os
import json
import re
import logging
from typing import Dict, List, Any, Optional
import spacy
from spacy.matcher import PhraseMatcher

from .embedder import embedder_service

logger = logging.getLogger(__name__)

class ResumeExtractor:
    """
    Extracts structured entities, sections, and canonical skills from resume text.
    Combines spaCy NLP with PhraseMatcher and semantic embedding matching.
    Optimized with disabled unneeded components (parser, lemmatizer) to conserve RAM on free cloud instances.
    """
    def __init__(self, skills_json_path: Optional[str] = None):
        logger.info("Initializing spaCy 'en_core_web_md' model (optimized pipeline)...")
        # Disable heavy parser and lemmatizer; only ner is needed for names
        self.nlp = spacy.load("en_core_web_md", disable=["parser", "lemmatizer"])
        
        # Base paths
        if skills_json_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            skills_json_path = os.path.join(base_dir, "data", "skills.json")
            
        self.skills_taxonomy = self._load_skills(skills_json_path)
        self.matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        self.term_to_canonical: Dict[str, Dict[str, str]] = {}
        self._build_phrase_matcher()

    def _load_skills(self, path: str) -> Dict[str, List[Dict[str, Any]]]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        logger.warning(f"Skills taxonomy file not found at {path}")
        return {}

    def _build_phrase_matcher(self) -> None:
        """Indexes skills and aliases for exact & lower-case PhraseMatching."""
        for category, skill_list in self.skills_taxonomy.items():
            for item in skill_list:
                canonical_name = item["name"]
                all_terms = [canonical_name] + item.get("aliases", [])
                
                for term in all_terms:
                    normalized = term.strip().lower()
                    if not normalized:
                        continue
                    self.term_to_canonical[normalized] = {
                        "name": canonical_name,
                        "category": category
                    }
                    doc = self.nlp.make_doc(term)
                    self.matcher.add("SKILL", [doc])

    def extract_contact_info(self, text: str) -> Dict[str, Optional[str]]:
        """Extracts email, phone, LinkedIn, GitHub, and websites using robust regex patterns."""
        email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
        email = email_match.group(0) if email_match else None

        # International and national phone patterns
        phone_match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
        phone = phone_match.group(0).strip() if phone_match else None

        # Social / Portfolio links
        linkedin_match = re.search(r'linkedin\.com/in/[a-zA-Z0-9_-]+', text, re.IGNORECASE)
        linkedin = f"https://{linkedin_match.group(0)}" if linkedin_match else None

        github_match = re.search(r'github\.com/[a-zA-Z0-9_-]+', text, re.IGNORECASE)
        github = f"https://{github_match.group(0)}" if github_match else None

        return {
            "email": email,
            "phone": phone,
            "linkedin": linkedin,
            "github": github
        }

    def extract_candidate_name(self, text: str) -> str:
        """
        Infers candidate name from the top lines using spaCy PERSON entities
        and clean title heuristics.
        """
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        candidate_lines = lines[:6]  # Look in the header region
        header_text = " . ".join(candidate_lines)
        doc = self.nlp(header_text)

        for ent in doc.ents:
            if ent.label_ == "PERSON":
                cleaned = ent.text.strip(" . , | /")
                # Filter out obvious non-name words or headers
                if len(cleaned.split()) in (2, 3, 4) and not any(kw in cleaned.lower() for kw in ["resume", "curriculum", "vitae", "profile", "summary", "engineer", "developer", "contact"]):
                    return cleaned

        # Heuristic fallback: First non-empty line with 2-3 capitalized words
        for line in candidate_lines:
            words = line.split()
            if 2 <= len(words) <= 3 and all(w[0].isupper() for w in words if w.isalpha()):
                return line
                
        return "Candidate"

    def segment_sections(self, text: str) -> Dict[str, str]:
        """
        Segments the resume into standard sections:
        experience, education, skills, projects, certifications, summary.
        """
        section_headers = {
            "experience": ["work experience", "experience", "employment history", "work history", "professional experience"],
            "education": ["education", "academic background", "qualifications", "academics"],
            "skills": ["skills", "technical skills", "core competencies", "technologies", "tech stack", "tools"],
            "projects": ["projects", "personal projects", "academic projects", "key projects"],
            "certifications": ["certifications", "certificates", "licenses", "courses"],
            "summary": ["summary", "professional summary", "about me", "profile", "objective"]
        }

        # Build combined pattern for splitting
        all_header_kws = []
        header_map = {}
        for sec, kws in section_headers.items():
            for kw in kws:
                all_header_kws.append(re.escape(kw))
                header_map[kw] = sec

        pattern = r'(?i)^[ \t]*(?:' + '|'.join(all_header_kws) + r')[ \t]*(?::|\n|$)'
        lines = text.split("\n")
        
        sections = {sec: [] for sec in section_headers.keys()}
        sections["header"] = []
        
        current_section = "header"
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
                
            matched_sec = None
            for kw, sec in header_map.items():
                if re.match(r'(?i)^[ \t]*' + re.escape(kw) + r'[ \t]*(?::|$)', stripped):
                    matched_sec = sec
                    break
                    
            if matched_sec:
                current_section = matched_sec
            else:
                sections[current_section].append(line)

        return {k: "\n".join(v).strip() for k, v in sections.items()}

    def extract_work_experience_metadata(self, text: str) -> Dict[str, Any]:
        """
        Extracts duration, company names, and estimates total years of experience.
        """
        # Look for date ranges e.g., "2020 - 2023", "Jan 2019 - Present", "05/2018 - 09/2021"
        date_pattern = r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?[a-z]*[\s./-]*(?:19\d{2}|20\d{2}))\s*(?:-|–|—|to)\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?[a-z]*[\s./-]*(?:19\d{2}|20\d{2}|Present|Current))'
        matches = re.findall(date_pattern, text, re.IGNORECASE)
        
        years_found = []
        for start, end in matches:
            start_yr = re.search(r'(19\d{2}|20\d{2})', start)
            end_yr = re.search(r'(19\d{2}|20\d{2})', end)
            
            if start_yr:
                s_val = int(start_yr.group(1))
                e_val = int(end_yr.group(1)) if end_yr else 2026 # Reference current year
                if 1980 <= s_val <= 2026 and s_val <= e_val:
                    years_found.append(e_val - s_val)

        total_years = sum(years_found) if years_found else 0
        
        # Check direct mentions like "5+ years of experience"
        direct_exp = re.search(r'(\d+)\+?\s*years?(?:\s+of)?\s+experience', text, re.IGNORECASE)
        if direct_exp:
            total_years = max(total_years, int(direct_exp.group(1)))

        # Seniority classification
        if total_years >= 6:
            seniority = "Senior"
        elif total_years >= 3:
            seniority = "Mid-Level"
        elif total_years >= 1:
            seniority = "Junior"
        else:
            seniority = "Fresher"

        return {
            "estimated_years_experience": total_years,
            "seniority_level": seniority,
            "date_ranges_detected": len(matches)
        }

    def extract_skills(self, text: str) -> Dict[str, Any]:
        """
        Identifies skills using:
        1. spaCy PhraseMatcher with aliases
        2. Category organization
        3. Near-miss fuzzy detection
        """
        doc = self.nlp.make_doc(text)
        matches = self.matcher(doc)
        
        matched_canonical = {}
        by_category = {cat: set() for cat in self.skills_taxonomy.keys()}

        for match_id, start, end in matches:
            span = doc[start:end]
            term = span.text.strip().lower()
            if term in self.term_to_canonical:
                meta = self.term_to_canonical[term]
                name = meta["name"]
                cat = meta["category"]
                matched_canonical[name] = cat
                if cat in by_category:
                    by_category[cat].add(name)

        # Convert sets to sorted lists
        category_breakdown = {k: sorted(list(v)) for k, v in by_category.items()}
        all_skills_list = sorted(list(matched_canonical.keys()))

        return {
            "all_skills": all_skills_list,
            "total_skills_count": len(all_skills_list),
            "by_category": category_breakdown
        }

    def extract_full_profile(self, text: str) -> Dict[str, Any]:
        """Runs the complete extraction pipeline on resume text."""
        contact = self.extract_contact_info(text)
        candidate_name = self.extract_candidate_name(text)
        sections = self.segment_sections(text)
        exp_meta = self.extract_work_experience_metadata(text)
        skills = self.extract_skills(text)

        return {
            "candidate_name": candidate_name,
            "contact": contact,
            "sections": sections,
            "experience_metadata": exp_meta,
            "skills": skills,
            "raw_text": text
        }
