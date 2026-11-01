import re
from typing import Dict, List, Any

# High-impact strong action verbs across software & tech roles
STRONG_ACTION_VERBS = {
    "architected", "engineered", "developed", "deployed", "implemented", "designed",
    "optimized", "spearheaded", "accelerated", "scaled", "automated", "orchestrated",
    "refactored", "built", "created", "integrated", "constructed", "configured",
    "mentored", "led", "established", "reduced", "increased", "boosted", "delivered"
}

class ATSScorer:
    """
    Evaluates resumes against industry Applicant Tracking System (ATS) criteria (0 - 100):
    1. Section completeness (20 pts)
    2. Contact info & links (15 pts)
    3. Quantifiable achievements (25 pts)
    4. Action verb usage (15 pts)
    5. Keyword density & length (15 pts)
    6. Formatting & Red Flags (10 pts)
    """
    def score_resume(self, text: str, parsed_profile: Dict[str, Any]) -> Dict[str, Any]:
        suggestions: List[Dict[str, str]] = []
        strengths: List[str] = []
        
        # 1. Section Completeness (Max 20 pts)
        sections = parsed_profile.get("sections", {})
        sec_points = 0
        expected_sections = ["experience", "education", "skills", "projects"]
        present_sections = [s for s in expected_sections if sections.get(s) and len(sections[s].split()) > 10]
        
        sec_points = int((len(present_sections) / len(expected_sections)) * 20)
        if len(present_sections) == len(expected_sections):
            strengths.append("Contains all key resume sections (Experience, Education, Skills, and Projects).")
        else:
            missing = [s.capitalize() for s in expected_sections if s not in present_sections]
            suggestions.append({
                "type": "section",
                "message": f"Add missing key section(s): {', '.join(missing)} to improve ATS parsing clarity."
            })

        # 2. Contact Information & Links (Max 15 pts)
        contact = parsed_profile.get("contact", {})
        contact_points = 0
        if contact.get("email"):
            contact_points += 5
        else:
            suggestions.append({"type": "contact", "message": "Email address is missing or could not be recognized."})

        if contact.get("phone"):
            contact_points += 4
        else:
            suggestions.append({"type": "contact", "message": "Phone number is missing or poorly formatted."})

        if contact.get("linkedin") or contact.get("github"):
            contact_points += 6
            strengths.append("Includes professional portfolio links (LinkedIn/GitHub).")
        else:
            suggestions.append({"type": "contact", "message": "Include clickable LinkedIn or GitHub profiles."})

        # 3. Quantifiable Achievements (Numbers, %, $, metrics) (Max 25 pts)
        # Look for patterns like "25%", "$1.5M", "reduced latency by 40ms", "managed 10+ engineers"
        quant_patterns = re.findall(r'(?:\d+(?:\.\d+)?%|\$\d+(?:,\d+)*(?:\.\d+)?[kKmMbB]?|\b\d+\s*(?:ms|sec|x|users|clients|engineers|microservices|datasets)\b|\b\d{2,}\b)', text)
        quant_count = len(quant_patterns)
        
        if quant_count >= 6:
            quant_points = 25
            strengths.append(f"Excellent quantifiable metrics detected ({quant_count} metric instances found).")
        elif quant_count >= 3:
            quant_points = 18
            strengths.append(f"Good use of quantifiable metrics ({quant_count} instances).")
            suggestions.append({"type": "impact", "message": "Add more measurable business outcomes (e.g., % improvement, latency reduction, cost savings)."})
        elif quant_count >= 1:
            quant_points = 10
            suggestions.append({"type": "impact", "message": "Quantify your achievements with numbers, percentages, or scale metrics."})
        else:
            quant_points = 4
            suggestions.append({"type": "impact", "message": "Critical: No measurable achievements detected. Use the STAR method (Action + Metric)."})

        # 4. Action Verbs (Max 15 pts)
        words_lower = [w.strip(".,;:()[]{}").lower() for w in text.split()]
        found_action_verbs = set(words_lower).intersection(STRONG_ACTION_VERBS)
        verb_count = len(found_action_verbs)

        if verb_count >= 8:
            verb_points = 15
            strengths.append(f"Strong action-driven vocabulary with {verb_count} distinct power verbs.")
        elif verb_count >= 4:
            verb_points = 10
            strengths.append(f"Good use of action verbs ({verb_count} distinct power verbs).")
            suggestions.append({"type": "action_verbs", "message": "Replace passive language with power verbs like 'orchestrated', 'spearheaded', 'optimized'."})
        else:
            verb_points = 5
            suggestions.append({"type": "action_verbs", "message": "Avoid passive phrasing ('responsible for', 'worked on'); lead bullet points with strong action verbs."})

        # 5. Keyword Density & Length (Max 15 pts)
        word_count = len(text.split())
        skills_count = parsed_profile.get("skills", {}).get("total_skills_count", 0)

        length_points = 0
        if 250 <= word_count <= 1100:
            length_points += 8
            strengths.append(f"Ideal resume length ({word_count} words).")
        elif word_count < 250:
            length_points += 3
            suggestions.append({"type": "length", "message": f"Resume is brief ({word_count} words). Expand on project details and technical responsibilities."})
        else:
            length_points += 4
            suggestions.append({"type": "length", "message": f"Resume is quite long ({word_count} words). Condense to 1-2 focused pages."})

        if skills_count >= 12:
            length_points += 7
            strengths.append(f"High technical skill keyword density ({skills_count} recognized skills).")
        elif skills_count >= 6:
            length_points += 5
        else:
            length_points += 2
            suggestions.append({"type": "keywords", "message": "Keyword density is low. Explicitly list core frameworks, tools, and languages."})

        # 6. Formatting & Red Flags (Max 10 pts)
        formatting_points = 10
        # Red flag 1: Excessive personal pronouns (I, me, my, we)
        pronoun_hits = len(re.findall(r'\b(i|me|my|myself|we|our)\b', text, re.IGNORECASE))
        if pronoun_hits > 6:
            formatting_points -= 4
            suggestions.append({"type": "formatting", "message": f"Found {pronoun_hits} first-person pronouns (I, me, my). Modern resumes use telegraphic third-person phrasing."})

        # Red flag 2: Generic cliché buzzwords
        cliches = len(re.findall(r'\b(hardworking|go-getter|synergy|detail-oriented|team player|dynamic)\b', text, re.IGNORECASE))
        if cliches > 2:
            formatting_points -= 3
            suggestions.append({"type": "formatting", "message": "Remove subjective buzzwords ('hardworking', 'team player'); demonstrate these qualities through concrete projects."})

        formatting_points = max(0, formatting_points)

        # Total Calculation
        total_score = sec_points + contact_points + quant_points + verb_points + length_points + formatting_points
        total_score = max(10, min(100, total_score))

        # Overall rating band
        if total_score >= 85:
            rating_label = "Excellent (ATS Ready)"
            badge_color = "success"
        elif total_score >= 70:
            rating_label = "Good (Competitive)"
            badge_color = "primary"
        elif total_score >= 50:
            rating_label = "Average (Needs Polish)"
            badge_color = "warning"
        else:
            rating_label = "Low (Needs Immediate Revision)"
            badge_color = "danger"

        return {
            "overall_score": total_score,
            "rating_label": rating_label,
            "badge_color": badge_color,
            "category_scores": {
                "section_completeness": {"score": sec_points, "max": 20},
                "contact_info": {"score": contact_points, "max": 15},
                "quantifiable_impact": {"score": quant_points, "max": 25},
                "action_verbs": {"score": verb_points, "max": 15},
                "keyword_density_and_length": {"score": length_points, "max": 15},
                "formatting_and_style": {"score": formatting_points, "max": 10}
            },
            "strengths": strengths,
            "suggestions": suggestions
        }

