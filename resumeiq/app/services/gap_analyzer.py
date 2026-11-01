import os
import json
import logging
from typing import Dict, List, Any, Optional

from .embedder import embedder_service

logger = logging.getLogger(__name__)

class SkillGapAnalyzer:
    """
    Performs deep gap analysis between a candidate's resume and a target role
    or an arbitrary pasted Job Description (JD).
    """
    def __init__(self, roles_data_path: Optional[str] = None):
        if roles_data_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            roles_data_path = os.path.join(base_dir, "data", "roles.json")
        self.roles_map = self._load_roles(roles_data_path)

    def _load_roles(self, path: str) -> Dict[str, Dict[str, Any]]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                roles = json.load(f)
                return {r["id"]: r for r in roles}
        return {}

    def analyze_role_gap(self, candidate_skills: List[str], target_role_id: str) -> Dict[str, Any]:
        """
        Analyzes skill gaps against a predefined role from data/roles.json.
        """
        role = self.roles_map.get(target_role_id)
        if not role:
            # Fallback: search by title
            for r in self.roles_map.values():
                if r["title"].lower() == target_role_id.lower():
                    role = r
                    break
                    
        if not role:
            return {
                "target_role": target_role_id,
                "error": f"Role '{target_role_id}' not found in taxonomy."
            }

        candidate_lower = {s.lower() for s in candidate_skills}
        required_dict = role.get("required_skills", {})
        nice_to_haves = role.get("nice_to_have_skills", [])

        matched_skills = []
        missing_critical = []
        missing_nice_to_have = []

        for skill, weight in required_dict.items():
            if skill.lower() in candidate_lower:
                matched_skills.append({"name": skill, "weight": weight, "type": "critical"})
            else:
                missing_critical.append({"name": skill, "weight": weight, "type": "critical"})

        for skill in nice_to_haves:
            if skill.lower() in candidate_lower:
                matched_skills.append({"name": skill, "weight": 0.5, "type": "nice_to_have"})
            else:
                missing_nice_to_have.append({"name": skill, "weight": 0.5, "type": "nice_to_have"})

        total_critical = len(required_dict)
        missing_count = len(missing_critical)
        severity_ratio = (missing_count / total_critical) if total_critical > 0 else 0.0

        if severity_ratio > 0.6:
            severity = "High"
            severity_desc = "Significant skill gaps present; substantial upskilling required."
        elif severity_ratio > 0.3:
            severity = "Moderate"
            severity_desc = "Moderate gaps; candidate possesses strong foundational skills."
        else:
            severity = "Low"
            severity_desc = "Minor gaps; candidate is highly qualified with near-complete overlap."

        roadmap = role.get("roadmap", [])

        return {
            "target_role": role["title"],
            "target_role_id": role["id"],
            "matched_skills": [m["name"] for m in matched_skills],
            "missing_critical": [m["name"] for m in missing_critical],
            "missing_nice_to_have": [m["name"] for m in missing_nice_to_have],
            "gap_severity": severity,
            "gap_severity_score": round(severity_ratio * 100, 1),
            "severity_description": severity_desc,
            "roadmap": roadmap
        }

    def analyze_custom_jd_gap(self, candidate_skills: List[str], jd_text: str, extractor_service) -> Dict[str, Any]:
        """
        Analyzes skill gaps against an arbitrary pasted job description.
        Extracts JD skills using the same extractor pipeline and semantic fuzzy matching.
        """
        jd_profile = extractor_service.extract_skills(jd_text)
        jd_skills = jd_profile.get("all_skills", [])

        if not jd_skills:
            return {
                "target_role": "Custom Job Description",
                "matched_skills": [],
                "missing_critical": [],
                "missing_nice_to_have": [],
                "gap_severity": "Low",
                "gap_severity_score": 0.0,
                "severity_description": "No recognizable technical skills were detected in the provided job description.",
                "roadmap": []
            }

        candidate_lower = {s.lower() for s in candidate_skills}
        matched = []
        missing = []

        # Exact / alias match check
        for skill in jd_skills:
            if skill.lower() in candidate_lower:
                matched.append(skill)
            else:
                # Semantic fuzzy match check (e.g. "REST APIs" vs "RESTful services")
                skill_vec = embedder_service.encode(skill)
                best_sim = 0.0
                best_match = None
                for c_skill in candidate_skills:
                    c_vec = embedder_service.encode(c_skill)
                    sim = embedder_service.cosine_similarity(skill_vec, c_vec)
                    if sim > best_sim:
                        best_sim = sim
                        best_match = c_skill

                if best_sim >= 0.82:  # High semantic threshold
                    matched.append(f"{skill} (~ {best_match})")
                else:
                    missing.append(skill)

        # Split into critical vs nice-to-have heuristically
        critical_count = max(1, int(len(missing) * 0.6))
        missing_critical = missing[:critical_count]
        missing_nice = missing[critical_count:]

        severity_ratio = len(missing) / len(jd_skills) if jd_skills else 0.0
        severity = "High" if severity_ratio > 0.5 else ("Moderate" if severity_ratio > 0.25 else "Low")

        # Dynamically generate structured roadmap for missing skills
        roadmap = []
        for i, skill in enumerate(missing_critical[:4]):
            week_num = f"Week {i*2 + 1}-{i*2 + 2}"
            roadmap.append({
                "week": week_num,
                "skill": skill,
                "focus": f"Master core concepts, syntax, project integration and best practices for {skill}.",
                "resources": [f"{skill} Official Documentation", f"GitHub {skill} Starter Examples"]
            })

        return {
            "target_role": "Custom Job Description",
            "matched_skills": matched,
            "missing_critical": missing_critical,
            "missing_nice_to_have": missing_nice,
            "gap_severity": severity,
            "gap_severity_score": round(severity_ratio * 100, 1),
            "severity_description": f"Target job requires {len(jd_skills)} skills; you match {len(matched)}.",
            "roadmap": roadmap
        }

