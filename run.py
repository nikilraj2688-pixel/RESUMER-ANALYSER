import os

# Ensure transformers and huggingface load cached weights completely offline
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from resumeiq.app import create_app
from resumeiq.app.config import DevelopmentConfig

app = create_app(DevelopmentConfig)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Starting ResumeIQ server on http://localhost:{port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
