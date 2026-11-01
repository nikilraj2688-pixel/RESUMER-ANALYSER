from resumeiq.app.services.extractor import ResumeExtractor

extractor = ResumeExtractor()

def test_extract_contact_info():
    sample_text = "Jane Doe\njane.doe@example.com | (555) 123-4567\nlinkedin.com/in/janedoe | github.com/janedoe"
    contact = extractor.extract_contact_info(sample_text)
    assert contact["email"] == "jane.doe@example.com"
    assert "555" in contact["phone"]
    assert "linkedin.com/in/janedoe" in contact["linkedin"]
    assert "github.com/janedoe" in contact["github"]

def test_extract_skills_canonical_and_aliases():
    sample_text = "Proficient in Python, JS, k8s, PostgreSQL, Docker, and React."
    skills_data = extractor.extract_skills(sample_text)
    skills = skills_data["all_skills"]
    assert "Python" in skills
    assert "JavaScript" in skills  # Aliased from JS
    assert "Kubernetes" in skills  # Aliased from k8s
    assert "PostgreSQL" in skills
    assert "Docker" in skills
    assert "React" in skills

def test_experience_seniority():
    text_senior = "Senior Lead Software Architect with 7+ years of experience (2018 - Present)."
    meta = extractor.extract_work_experience_metadata(text_senior)
    assert meta["seniority_level"] == "Senior"

    text_junior = "Computer science graduate, 2025 - 2026."
    meta_junior = extractor.extract_work_experience_metadata(text_junior)
    assert meta_junior["seniority_level"] in ("Fresher", "Junior")

