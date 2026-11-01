import os
import json
import logging
from typing import Dict, List, Any, Optional

from .embedder import embedder_service

logger = logging.getLogger(__name__)

class RoleMatcher:
    """
    Computes suitability score for tech roles using a hybrid formula:
      final_score = 0.45 * semantic_similarity
                  + 0.40 * weighted_skill_overlap
                  + 0.15 * experience_relevance
    """
    def __init__(self, roles_data_path: Optional[str] = None):
        if roles_data_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            roles_data_path = os.path.join(base_dir, "data", "roles.json")
            
        self.roles = self._load_roles(roles_data_path)
        # Ensure role embeddings are precomputed
        embedder_service.precompute_role_embeddings(roles_data_path)

    def _load_roles(self, path: str) -> List[Dict[str, Any]]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        logger.warning(f"Roles file not found at {path}")
        return []

    def calculate_weighted_skill_overlap(self, candidate_skills: List[str], role: Dict[str, Any]) -> float:
        """
        Computes weighted skill overlap against role's required skills and nice-to-haves.
        """
        candidate_skills_lower = {s.lower() for s in candidate_skills}
        required_dict = role.get("required_skills", {})
        if not required_dict:
            return 0.0

        total_possible_weight = sum(required_dict.values())
        matched_weight = 0.0

        for req_skill, weight in required_dict.items():
            if req_skill.lower() in candidate_skills_lower:
                matched_weight += weight

        base_overlap = matched_weight / total_possible_weight if total_possible_weight > 0 else 0.0

        # Bonus for nice-to-have skills (up to 0.15 bonus capped at 1.0)
        nice_to_haves = role.get("nice_to_have_skills", [])
        matched_nice = sum(1 for n in nice_to_haves if n.lower() in candidate_skills_lower)
        bonus = min(0.15, (matched_nice / len(nice_to_haves)) * 0.15) if nice_to_haves else 0.0

        return min(1.0, base_overlap + bonus)

    def calculate_experience_relevance(self, resume_text: str, role: Dict[str, Any]) -> float:
        """
        Checks presence of role title, typical keywords, and domain markers in the resume.
        """
        text_lower = resume_text.lower()
        title_lower = role.get("title", "").lower()
        keywords = role.get("typical_keywords", [])

        # Direct title appearance
        has_title = 1.0 if title_lower in text_lower else 0.0
        
        # Keyword density match
        if keywords:
            keyword_hits = sum(1 for kw in keywords if kw.lower() in text_lower)
            keyword_ratio = min(1.0, keyword_hits / max(4, len(keywords) * 0.5))
        else:
            keyword_ratio = 0.0

        return min(1.0, 0.4 * has_title + 0.6 * keyword_ratio)

    def score_single_role(self, resume_embedding, resume_text: str, candidate_skills: List[str], role: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates the complete hybrid score for one role."""
        role_id = role["id"]
        role_embed = embedder_service.get_role_embedding(role_id)
        
        if role_embed is None:
            # Fallback on the fly if needed
            role_text = f"Role: {role.get('title')}. Description: {role.get('description')}"
            role_embed = embedder_service.encode(role_text)

        # 1. Semantic similarity (0.45 weight)
        sim_raw = embedder_service.cosine_similarity(resume_embedding, role_embed)
        # Rescale cosine similarity [-1, 1] to a realistic 0 to 1 domain for text
        semantic_score = max(0.0, min(1.0, (sim_raw - 0.15) / 0.70))

        # 2. Weighted skill overlap (0.40 weight)
        skill_score = self.calculate_weighted_skill_overlap(candidate_skills, role)

        # 3. Experience & title relevance (0.15 weight)
        exp_score = self.calculate_experience_relevance(resume_text, role)

        # Hybrid formula
        final_score = (0.45 * semantic_score) + (0.40 * skill_score) + (0.15 * exp_score)
        match_percentage = round(final_score * 100, 1)

        # Matched and missing breakdown
        candidate_skills_lower = {s.lower() for s in candidate_skills}
        matched_required = [s for s in role.get("required_skills", {}).keys() if s.lower() in candidate_skills_lower]
        missing_required = [s for s in role.get("required_skills", {}).keys() if s.lower() not in candidate_skills_lower]
        matched_nice = [s for s in role.get("nice_to_have_skills", []) if s.lower() in candidate_skills_lower]

        return {
            "role_id": role["id"],
            "title": role["title"],
            "match_percentage": match_percentage,
            "final_score": round(final_score, 4),
            "breakdown": {
                "semantic_similarity": round(semantic_score * 100, 1),
                "skill_overlap": round(skill_score * 100, 1),
                "experience_relevance": round(exp_score * 100, 1)
            },
            "matched_required": matched_required,
            "missing_required": missing_required,
            "matched_nice_to_have": matched_nice,
            "roadmap": role.get("roadmap", [])
        }

    def generate_explanation(self, best_role: Dict[str, Any], candidate_name: str, seniority: str) -> str:
        """
        Generates a transparent, plain-English explanation for WHY the best role fits
        and what skills or areas are holding it back.
        """
        title = best_role["title"]
        pct = best_role["match_percentage"]
        matched_req = best_role["matched_required"]
        missing_req = best_role["missing_required"]
        matched_nice = best_role.get("matched_nice_to_have", [])

        explanation = f"Your resume shows a strong {pct}% affinity for the {title} position at a {seniority} level. "
        
        if matched_req:
            top_matches = ", ".join(matched_req[:4])
            explanation += f"You demonstrate solid command of core requirements including {top_matches}. "
            if matched_nice:
                explanation += f"Additionally, your familiarity with {', '.join(matched_nice[:2])} provides high-value competitive edge. "
        else:
            explanation += "Your background shares conceptual alignment with this role's domain. "

        if missing_req:
            top_missing = ", ".join(missing_req[:3])
            explanation += f"To maximize competitiveness, focus on acquiring {top_missing}, which are primary requirements for modern {title} postings."
        else:
            explanation += f"You meet all primary baseline skill criteria for this profile!"

        return explanation

    def match_all_roles(self, resume_text: str, candidate_skills: List[str], candidate_name: str = "Candidate", seniority: str = "Junior") -> Dict[str, Any]:
        """
        Scores all 20+ roles, ranks them, and returns top 3, best fit role,
        and human explanation.
        """
        resume_embedding = embedder_service.encode(resume_text[:2500])
        scored_roles = []

        for role in self.roles:
            result = self.score_single_role(resume_embedding, resume_text, candidate_skills, role)
            scored_roles.append(result)

        # Sort descending by match percentage
        scored_roles.sort(key=lambda x: x["match_percentage"], reverse=True)

        top_3 = scored_roles[:3]
        best_fit = top_3[0] if top_3 else None
        
        headline = f"Best Fit Role: {best_fit['title']} ({best_fit['match_percentage']}% Match)" if best_fit else "No matching role identified."
        explanation = self.generate_explanation(best_fit, candidate_name, seniority) if best_fit else ""

        return {
            "best_fit_role": best_fit,
            "best_fit_headline": headline,
            "explanation": explanation,
            "top_3_roles": top_3,
            "all_role_scores": scored_roles
        }

