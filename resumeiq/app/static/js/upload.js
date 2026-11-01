/**
 * Upload Page Interactions: Drag and Drop, Form Data, Role Dropdown, Analysis Dispatch
 * Syncs results directly to Cloud Firestore & Firebase Storage
 */

let selectedFile = null;

document.addEventListener("DOMContentLoaded", async () => {
  setupDragAndDrop();
  await loadRolesDropdown();
  setupFormSubmit();
});

function setupDragAndDrop() {
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const fileInfo = document.getElementById("selected-file-info");
  const fileNameDisplay = document.getElementById("file-name-display");
  const removeFileBtn = document.getElementById("remove-file-btn");

  if (!dropZone || !fileInput) return;

  dropZone.addEventListener("click", () => fileInput.click());

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.style.borderColor = "var(--primary)";
    dropZone.style.backgroundColor = "var(--primary-light)";
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.style.borderColor = "var(--border-color)";
    dropZone.style.backgroundColor = "var(--bg-subtle)";
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.style.borderColor = "var(--border-color)";
    dropZone.style.backgroundColor = "var(--bg-subtle)";
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  });

  if (removeFileBtn) {
    removeFileBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      selectedFile = null;
      fileInput.value = "";
      fileInfo.style.display = "none";
      dropZone.style.display = "block";
    });
  }

  function handleFile(file) {
    const ext = file.name.split('.').pop().toLowerCase();
    if (!["pdf", "docx"].includes(ext)) {
      showToast("Please upload a PDF or DOCX file.", "error");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      showToast("File size exceeds 5 MB limit.", "error");
      return;
    }

    selectedFile = file;
    fileNameDisplay.innerText = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    dropZone.style.display = "none";
    fileInfo.style.display = "flex";
  }
}

async function loadRolesDropdown() {
  const select = document.getElementById("target-role-select");
  if (!select) return;

  try {
    const data = await API.get("/api/roles");
    if (data.roles) {
      data.roles.forEach(role => {
        const opt = document.createElement("option");
        opt.value = role.id;
        opt.innerText = role.title;
        select.appendChild(opt);
      });
    }
  } catch (err) {
    console.warn("Could not load roles dropdown:", err);
  }
}

function setupFormSubmit() {
  const form = document.getElementById("analyze-form");
  const submitBtn = document.getElementById("submit-btn");
  const loadingOverlay = document.getElementById("loading-indicator");

  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (!selectedFile) {
      showToast("Please select a resume file first.", "error");
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);

    const targetRole = document.getElementById("target-role-select").value;
    if (targetRole) {
      formData.append("target_role", targetRole);
    }

    const customJd = document.getElementById("custom-jd-input").value;
    if (customJd) {
      formData.append("job_description", customJd);
    }

    // Show loading
    submitBtn.disabled = true;
    if (loadingOverlay) loadingOverlay.style.display = "flex";

    try {
      showToast("Parsing resume and analyzing skill gaps...", "info");
      const result = await API.postMultipart("/api/analyze", formData);

      // Save latest analysis in sessionStorage
      sessionStorage.setItem("latest_analysis", JSON.stringify(result));

      // Direct write to Cloud Firestore if client Firebase SDK is loaded
      if (typeof firebase !== "undefined" && firebase.firestore) {
        try {
          const db = firebase.firestore();
          const uid = Auth.currentUser?.uid || "guest_demo";
          await db.collection("users").doc(uid).collection("analyses").doc(result.analysis_id).set(result);
          console.log("Successfully written analysis to Cloud Firestore!");
        } catch (dbErr) {
          console.warn("Direct Firestore write notice:", dbErr);
        }
      }

      showToast("Analysis complete! Redirecting...", "success");

      setTimeout(() => {
        window.location.href = `/dashboard?id=${result.analysis_id}`;
      }, 500);

    } catch (err) {
      showToast(err.message || "Failed to analyze resume.", "error");
      submitBtn.disabled = false;
      if (loadingOverlay) loadingOverlay.style.display = "none";
    }
  });
}
