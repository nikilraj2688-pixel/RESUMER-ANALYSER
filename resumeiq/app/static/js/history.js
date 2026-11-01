/**
 * History Page Interactions: List past analyses, trend chart, delete actions
 * Strictly isolated per authenticated account
 */

let trendChartInstance = null;

document.addEventListener("DOMContentLoaded", async () => {
  const token = API.getToken();
  if (!token) {
    showToast("Please sign in to view your scan history.", "info");
    const emptyState = document.getElementById("history-empty-state");
    const historyContent = document.getElementById("history-content");
    if (emptyState) {
      emptyState.style.display = "block";
      emptyState.innerHTML = `
        <div style="font-size: 3rem; margin-bottom: 1rem;">🔒</div>
        <h3 style="font-weight: 700; margin-bottom: 0.5rem;">Sign In Required</h3>
        <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">Sign in to view and save your private resume scans.</p>
        <a href="/login" class="btn btn-primary">Sign In</a>
      `;
    }
    if (historyContent) historyContent.style.display = "none";
    return;
  }

  await loadHistory();
});

async function loadHistory() {
  const tableBody = document.getElementById("history-table-body");
  const emptyState = document.getElementById("history-empty-state");
  const historyContent = document.getElementById("history-content");

  try {
    const data = await API.get("/api/analyses");
    const analyses = data.analyses || [];

    if (!analyses.length) {
      if (emptyState) emptyState.style.display = "block";
      if (historyContent) historyContent.style.display = "none";
      return;
    }

    if (emptyState) emptyState.style.display = "none";
    if (historyContent) historyContent.style.display = "block";

    renderHistoryTable(analyses);
    renderTrendChart(analyses);

  } catch (err) {
    console.error("Failed to load past analyses:", err);
    if (emptyState) {
      emptyState.style.display = "block";
      emptyState.innerHTML = `
        <div style="font-size: 3rem; margin-bottom: 1rem;">📂</div>
        <h3 style="font-weight: 700; margin-bottom: 0.5rem;">No Past Analyses Found for this Account</h3>
        <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">You have not scanned any resumes under this account yet.</p>
        <a href="/upload" class="btn btn-primary">Scan Resume Now</a>
      `;
    }
    if (historyContent) historyContent.style.display = "none";
  }
}

function renderHistoryTable(analyses) {
  const tbody = document.getElementById("history-table-body");
  if (!tbody) return;

  tbody.innerHTML = "";
  analyses.forEach(item => {
    const tr = document.createElement("tr");
    tr.style.borderBottom = "1px solid var(--border-color)";

    const dateStr = item.created_at ? new Date(item.created_at).toLocaleDateString() : "Recent";
    const bestFit = item.role_prediction?.best_fit_role?.title || "N/A";
    const matchPct = item.role_prediction?.best_fit_role?.match_percentage || 0;
    const atsScore = item.ats_score?.overall_score || 0;

    tr.innerHTML = `
      <td style="padding: 1rem 0.5rem; font-weight: 500;">${item.filename || "Resume"}</td>
      <td style="padding: 1rem 0.5rem; color: var(--text-secondary);">${dateStr}</td>
      <td style="padding: 1rem 0.5rem;"><span class="badge badge-primary">${bestFit} (${matchPct}%)</span></td>
      <td style="padding: 1rem 0.5rem;"><strong>${atsScore}/100</strong></td>
      <td style="padding: 1rem 0.5rem; text-align: right;">
        <button onclick="reopenAnalysis('${item.analysis_id}')" class="btn btn-outline" style="padding: 0.3rem 0.7rem; font-size: 0.85rem; margin-right: 0.5rem;">View</button>
        <button onclick="deleteAnalysisItem('${item.analysis_id}')" class="btn btn-outline" style="padding: 0.3rem 0.7rem; font-size: 0.85rem; color: var(--danger);">Delete</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderTrendChart(analyses) {
  const ctx = document.getElementById("history-trend-chart");
  if (!ctx || !analyses.length) return;

  if (trendChartInstance) trendChartInstance.destroy();

  // Reverse so chronological order (oldest -> newest)
  const reversed = [...analyses].reverse();
  const labels = reversed.map((a, idx) => `Scan #${idx + 1} (${a.filename ? a.filename.substring(0, 10) : 'v' + (idx+1)})`);
  const atsScores = reversed.map(a => a.ats_score?.overall_score || 0);
  const matchScores = reversed.map(a => a.role_prediction?.best_fit_role?.match_percentage || 0);

  trendChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "ATS Score",
          data: atsScores,
          borderColor: "#4f46e5",
          backgroundColor: "rgba(79, 70, 229, 0.1)",
          tension: 0.3,
          fill: true
        },
        {
          label: "Best Fit Match %",
          data: matchScores,
          borderColor: "#06b6d4",
          backgroundColor: "rgba(6, 182, 212, 0.1)",
          tension: 0.3,
          fill: true
        }
      ]
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true,
          max: 100
        }
      }
    }
  });
}

async function reopenAnalysis(analysisId) {
  try {
    const data = await API.get(`/api/analyses/${analysisId}`);
    sessionStorage.setItem("latest_analysis", JSON.stringify(data));
    window.location.href = `/dashboard?id=${analysisId}`;
  } catch (err) {
    showToast("Could not load analysis details.", "error");
  }
}

async function deleteAnalysisItem(analysisId) {
  if (!confirm("Are you sure you want to delete this resume analysis record?")) return;

  try {
    await API.delete(`/api/analyses/${analysisId}`);
    showToast("Record deleted successfully.", "success");
    await loadHistory();
  } catch (err) {
    showToast("Failed to delete record.", "error");
  }
}
