import os

# Limit PyTorch to single-thread to operate comfortably within 512MB RAM
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

# Ensure offline loading if pre-cached, but allow fallback if needed
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

from resumeiq.app import create_app
from resumeiq.app.config import DevelopmentConfig

app = create_app(DevelopmentConfig)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Starting ResumeIQ server on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
