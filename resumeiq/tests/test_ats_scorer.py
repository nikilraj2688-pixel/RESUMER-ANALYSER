from resumeiq.app.services.ats_scorer import ATSScorer

scorer = ATSScorer()

def test_ats_scoring_comprehensive():
    sample_text = """
    Jane Developer
    jane@example.com | (555) 321-4321 | linkedin.com/in/janedev
    
    Professional Summary
    Experienced software engineer with strong background in distributed systems.
    
    Technical Skills
    Python, Docker, Kubernetes, PostgreSQL, AWS, React, Git, CI/CD, Redis, Linux, REST APIs, Microservices
    
    Professional Experience
    Senior Software Engineer - Cloud Corp | 2021 - Present
    - Architected and deployed microservices reducing API latency by 45% across 2M users.
    - Spearheaded database migration saving $150K in cloud infrastructure costs.
    - Engineered automated CI/CD pipeline increasing release cadence by 3x.
    
    Education
    B.S. in Computer Science - University of Illinois (2017 - 2021)
    
    Projects
    - High Performance Cache: Built an in-memory storage engine in Go.
    """
    
    parsed_profile = {
        "contact": {"email": "jane@example.com", "phone": "555-321-4321", "linkedin": "linkedin.com/in/janedev"},
        "sections": {
            "experience": "Senior Software Engineer with strong background in building distributed microservices and databases...",
            "education": "B.S. in Computer Science - University of Illinois (2017 - 2021)",
            "skills": "Python, Docker, Kubernetes, PostgreSQL, AWS, React, Git, CI/CD, Redis, Linux, REST APIs, Microservices",
            "projects": "High Performance Cache: Built an in-memory storage engine in Go with Redis benchmarks."
        },
        "skills": {"total_skills_count": 12}
    }
    
    result = scorer.score_resume(sample_text, parsed_profile)
    assert result["overall_score"] >= 75
    assert len(result["strengths"]) >= 2
    assert "overall_score" in result
