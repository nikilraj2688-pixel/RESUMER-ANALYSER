/**
 * Dashboard Visualizations: Chart.js Bar & Radar charts, ATS score gauge, roadmap, PDF export
 */

let rolesChartInstance = null;
let radarChartInstance = null;
let atsGaugeChartInstance = null;

document.addEventListener("DOMContentLoaded", async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const analysisId = urlParams.get("id");

  let data = null;

  // Check session storage first
  const cached = sessionStorage.getItem("latest_analysis");
  if (cached) {
    const parsed = JSON.parse(cached);
    if (!analysisId || parsed.analysis_id === analysisId) {
      data = parsed;
    }
  }

  // If not cached, fetch from API
  if (!data && analysisId) {
    try {
      data = await API.get(`/api/analyses/${analysisId}`);
    } catch (err) {
      showToast("Could not retrieve analysis.", "error");
    }
  }

  if (data) {
    renderDashboard(data);
  } else {
    document.getElementById("dashboard-content").innerHTML = `
      <div class="card" style="text-align: center; padding: 4rem;">
        <h2>No Resume Analysis Selected</h2>
        <p style="color: var(--text-secondary); margin: 1rem 0 2rem;">Please upload a resume first to view deep analytics and gap predictions.</p>
        <a href="/upload" class="btn btn-primary">Upload Resume Now</a>
      </div>
    `;
  }

  // PDF Export
  const exportBtn = document.getElementById("export-pdf-btn");
  if (exportBtn) {
    exportBtn.addEventListener("click", () => {
      window.print();
    });
  }
});

function renderDashboard(data) {
  const candidateName = data.profile?.candidate_name || "Candidate";
  const seniority = data.profile?.experience_metadata?.seniority_level || "Junior";
  const bestFit = data.role_prediction?.best_fit_role;
  const top3 = data.role_prediction?.top_3_roles || [];
  const gap = data.skill_gap_analysis || {};
  const ats = data.ats_score || {};
  const skillsByCat = data.profile?.skills_summary?.by_category || {};

  // Header
  document.getElementById("candidate-name-display").innerText = candidateName;
  document.getElementById("candidate-seniority-badge").innerText = `${seniority} Level`;
  document.getElementById("resume-filename").innerText = data.filename || "Resume Document";

  // Best Fit Role Headline Card
  if (bestFit) {
    document.getElementById("best-role-title").innerText = bestFit.title;
    document.getElementById("best-role-percentage").innerText = `${bestFit.match_percentage}% Match`;
    document.getElementById("best-role-explanation").innerText = data.role_prediction.explanation || "";
  }

  // Render Charts
  renderRolesBarChart(top3);
  renderSkillsRadarChart(skillsByCat);
  renderAtsGauge(ats.overall_score || 0);

  // ATS details & suggestions
  document.getElementById("ats-rating-label").innerText = ats.rating_label || "Score Analysis";
  renderAtsStrengthsAndSuggestions(ats);

  // Matched vs Missing Skills Chips
  renderSkillsChips(gap);

  // Learning Roadmap
  renderRoadmapTimeline(gap.roadmap || []);
}

function renderRolesBarChart(top3) {
  const ctx = document.getElementById("roles-bar-chart");
  if (!ctx || !top3.length) return;

  if (rolesChartInstance) rolesChartInstance.destroy();

  const labels = top3.map(r => r.title);
  const scores = top3.map(r => r.match_percentage);

  rolesChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "Suitability Match %",
        data: scores,
        backgroundColor: ["#4f46e5", "#06b6d4", "#8b5cf6"],
        borderRadius: 8
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          ticks: { callback: v => v + "%" }
        }
      }
    }
  });
}

function renderSkillsRadarChart(byCat) {
  const ctx = document.getElementById("skills-radar-chart");
  if (!ctx) return;

  if (radarChartInstance) radarChartInstance.destroy();

  const labels = Object.keys(byCat).map(c => c.replace("_", " ").toUpperCase());
  const counts = Object.values(byCat).map(list => list.length);

  radarChartInstance = new Chart(ctx, {
    type: "radar",
    data: {
      labels: labels,
      datasets: [{
        label: "Identified Skills",
        data: counts,
        backgroundColor: "rgba(79, 70, 229, 0.2)",
        borderColor: "#4f46e5",
        pointBackgroundColor: "#4f46e5"
      }]
    },
    options: {
      responsive: true,
      scales: {
        r: {
          beginAtZero: true,
          ticks: { stepSize: 2 }
        }
      }
    }
  });
}

function renderAtsGauge(score) {
  const ctx = document.getElementById("ats-gauge-chart");
  if (!ctx) return;

  if (atsGaugeChartInstance) atsGaugeChartInstance.destroy();

  const remaining = 100 - score;
  let color = "#ef4444";
  if (score >= 80) color = "#10b981";
  else if (score >= 60) color = "#4f46e5";
  else if (score >= 45) color = "#f59e0b";

  atsGaugeChartInstance = new Chart(ctx, {
    type: "doughnut",
    data: {
      datasets: [{
        data: [score, remaining],
        backgroundColor: [color, "#e2e8f0"],
        circumference: 180,
        rotation: 270,
        cutout: "75%"
      }]
    },
    options: {
      responsive: true,
      plugins: {
        tooltip: { enabled: false }
      }
    }
  });

  document.getElementById("ats-score-number").innerText = score;
}

function renderAtsStrengthsAndSuggestions(ats) {
  const suggestionsList = document.getElementById("ats-suggestions-list");
  if (!suggestionsList) return;

  let html = "";
  if (ats.suggestions && ats.suggestions.length) {
    html += "<h4 style='margin-bottom: 0.5rem;'>Actionable Improvements:</h4><ul style='padding-left: 1.2rem; margin-bottom: 1rem;'>";
    ats.suggestions.forEach(s => {
      html += `<li style='margin-bottom: 0.35rem; color: var(--text-secondary);'>${s.message}</li>`;
    });
    html += "</ul>";
  }

  if (ats.strengths && ats.strengths.length) {
    html += "<h4 style='margin-bottom: 0.5rem; color: var(--success);'>Key Strengths:</h4><ul style='padding-left: 1.2rem;'>";
    ats.strengths.forEach(st => {
      html += `<li style='margin-bottom: 0.35rem; color: var(--text-secondary);'>${st}</li>`;
    });
    html += "</ul>";
  }

  suggestionsList.innerHTML = html;
}

function renderSkillsChips(gap) {
  const container = document.getElementById("skills-chips-container");
  if (!container) return;

  let html = "";
  if (gap.matched_skills && gap.matched_skills.length) {
    html += "<div style='margin-bottom: 1rem;'><strong style='color: #065f46;'>Matched Skills:</strong><br>";
    gap.matched_skills.forEach(s => {
      html += `<span class='chip chip-matched'>✓ ${s}</span>`;
    });
    html += "</div>";
  }

  if (gap.missing_critical && gap.missing_critical.length) {
    html += "<div style='margin-bottom: 1rem;'><strong style='color: #991b1b;'>Missing Critical Skills:</strong><br>";
    gap.missing_critical.forEach(s => {
      html += `<span class='chip chip-missing-crit'>✕ ${s}</span>`;
    });
    html += "</div>";
  }

  if (gap.missing_nice_to_have && gap.missing_nice_to_have.length) {
    html += "<div style='margin-bottom: 1rem;'><strong style='color: #92400e;'>Bonus / Nice-to-Have Skills:</strong><br>";
    gap.missing_nice_to_have.forEach(s => {
      html += `<span class='chip chip-missing-nice'>+ ${s}</span>`;
    });
    html += "</div>";
  }

  container.innerHTML = html;
}

function renderRoadmapTimeline(roadmap) {
  const container = document.getElementById("roadmap-container");
  if (!container) return;

  if (!roadmap || !roadmap.length) {
    container.innerHTML = "<p style='color: var(--text-muted);'>No skill gaps identified for this role!</p>";
    return;
  }

  let html = "<div style='display: flex; flex-direction: column; gap: 1rem;'>";
  roadmap.forEach(step => {
    html += `
      <div style="border-left: 3px solid var(--primary); padding-left: 1rem; margin-left: 0.5rem;">
        <span class="badge badge-primary" style="margin-bottom: 0.3rem;">${step.week}</span>
        <h4 style="font-weight: 700; color: var(--text-primary); margin: 0.2rem 0;">${step.skill}</h4>
        <p style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 0.4rem;">${step.focus}</p>
        <div style="font-size: 0.85rem; color: var(--text-muted);">
          <strong>Suggested Free Resources:</strong> ${step.resources.join(" • ")}
        </div>
      </div>
    `;
  });
  html += "</div>";

  container.innerHTML = html;
}

