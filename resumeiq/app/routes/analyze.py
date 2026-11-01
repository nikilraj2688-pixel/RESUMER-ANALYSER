import uuid
import datetime
import logging
from flask import Blueprint, request, jsonify

from ..services.parser import parse_resume, ParserError
from ..services.extractor import ResumeExtractor
from ..services.role_matcher import RoleMatcher
from ..services.gap_analyzer import SkillGapAnalyzer
from ..services.ats_scorer import ATSScorer
from ..services.firebase_service import firebase_service, require_auth

logger = logging.getLogger(__name__)
analyze_bp = Blueprint("analyze", __name__)

# Singletons for request handling
extractor_service = ResumeExtractor()
role_matcher_service = RoleMatcher()
gap_analyzer_service = SkillGapAnalyzer()
ats_scorer_service = ATSScorer()

@analyze_bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "ResumeIQ API",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }), 200

@analyze_bp.route("/analyze", methods=["POST"])
@require_auth
def analyze_resume():
    """
    POST /api/analyze
    Multipart form-data:
      - file: resume (PDF or DOCX, max 5 MB)
      - target_role: optional role_id or title
      - job_description: optional pasted job description text
    """
    if "file" not in request.files:
        return jsonify({"error": "Bad Request", "message": "No resume file provided in 'file' field."}), 400

    uploaded_file = request.files["file"]
    filename = uploaded_file.filename
    file_bytes = uploaded_file.read()

    target_role = request.form.get("target_role", "").strip()
    custom_jd = request.form.get("job_description", "").strip()

    try:
        # 1. Parse text from file
        parsed_doc = parse_resume(filename, file_bytes)
        resume_text = parsed_doc["text"]

        # 2. Extract profile, contact, sections, experience metadata, and skills
        profile = extractor_service.extract_full_profile(resume_text)
        candidate_name = profile["candidate_name"]
        seniority = profile["experience_metadata"]["seniority_level"]
        all_skills = profile["skills"]["all_skills"]

        # 3. Match against all 20+ roles
        role_matching_results = role_matcher_service.match_all_roles(
            resume_text=resume_text,
            candidate_skills=all_skills,
            candidate_name=candidate_name,
            seniority=seniority
        )
        best_fit = role_matching_results["best_fit_role"]

        # 4. Perform skill gap analysis
        if custom_jd and len(custom_jd.split()) > 10:
            gap_results = gap_analyzer_service.analyze_custom_jd_gap(
                candidate_skills=all_skills,
                jd_text=custom_jd,
                extractor_service=extractor_service
            )
        elif target_role:
            gap_results = gap_analyzer_service.analyze_role_gap(all_skills, target_role)
        else:
            # Default to best-fit role
            target_id = best_fit["role_id"] if best_fit else "backend_developer"
            gap_results = gap_analyzer_service.analyze_role_gap(all_skills, target_id)

        # 5. Score resume ATS compatibility
        ats_results = ats_scorer_service.score_resume(resume_text, profile)

        # 6. Build response payload
        analysis_id = str(uuid.uuid4())
        created_at = datetime.datetime.utcnow().isoformat()
        current_user = getattr(request, "current_user", {"uid": "guest_demo"})
        uid = current_user.get("uid", "guest_demo")

        result_payload = {
            "analysis_id": analysis_id,
            "uid": uid,
            "filename": filename,
            "created_at": created_at,
            "profile": {
                "candidate_name": candidate_name,
                "contact": profile["contact"],
                "experience_metadata": profile["experience_metadata"],
                "skills_summary": profile["skills"]
            },
            "role_prediction": {
                "best_fit_role": best_fit,
                "best_fit_headline": role_matching_results["best_fit_headline"],
                "explanation": role_matching_results["explanation"],
                "top_3_roles": role_matching_results["top_3_roles"],
                "all_role_scores": role_matching_results["all_role_scores"]
            },
            "skill_gap_analysis": gap_results,
            "ats_score": ats_results,
            "file_meta": {
                "word_count": parsed_doc["word_count"],
                "page_count": parsed_doc["page_count"],
                "size_kb": round(parsed_doc["file_size"] / 1024, 1)
            }
        }

        # 7. Persist to Firestore / Storage
        firebase_service.save_analysis(uid, analysis_id, result_payload)

        return jsonify(result_payload), 200

    except ParserError as pe:
        return jsonify({"error": "Parsing Error", "message": pe.message}), pe.status_code
    except Exception as e:
        logger.exception("Unexpected error during resume analysis")
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

