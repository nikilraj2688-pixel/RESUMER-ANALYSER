import os
import json
from flask import Blueprint, jsonify

roles_bp = Blueprint("roles", __name__)

@roles_bp.route("/roles", methods=["GET"])
def get_roles():
    """Returns list of 20+ tech roles for dropdowns and role exploration."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    roles_path = os.path.join(base_dir, "data", "roles.json")
    
    if os.path.exists(roles_path):
        with open(roles_path, "r", encoding="utf-8") as f:
            roles = json.load(f)
        return jsonify({
            "roles": [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "description": r["description"],
                    "required_skills": list(r.get("required_skills", {}).keys()),
                    "nice_to_have_skills": r.get("nice_to_have_skills", [])
                }
                for r in roles
            ],
            "total_count": len(roles)
        }), 200
    return jsonify({"error": "Roles taxonomy not found", "roles": []}), 404

