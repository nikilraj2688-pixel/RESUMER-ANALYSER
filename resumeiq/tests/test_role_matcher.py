from resumeiq.app.services.role_matcher import RoleMatcher

matcher = RoleMatcher()

def test_role_matching_top_ranking():
    swe_text = """
    Alex Johnson - Senior Backend Engineer
    Skilled in Python, REST APIs, SQL, PostgreSQL, Docker, Redis, and Git.
    Architected high-throughput microservices and distributed caching systems.
    """
    swe_skills = ["Python", "REST APIs", "SQL", "PostgreSQL", "Docker", "Git", "Redis"]
    res = matcher.match_all_roles(swe_text, swe_skills, "Alex Johnson", "Senior")
    
    assert len(res["top_3_roles"]) == 3
    best_role = res["best_fit_role"]
    assert best_role["role_id"] in ["backend_developer", "fullstack_developer"]
    assert best_role["match_percentage"] > 60
    assert "Backend Developer" in res["best_fit_headline"] or "Full-Stack Developer" in res["best_fit_headline"]
    assert len(res["explanation"]) > 20

