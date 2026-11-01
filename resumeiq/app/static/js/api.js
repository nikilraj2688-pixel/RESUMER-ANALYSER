/**
 * ResumeIQ API Client & Global Helpers
 */

const API = {
  getToken() {
    return localStorage.getItem("resumeiq_token") || "";
  },

  setToken(token) {
    localStorage.setItem("resumeiq_token", token);
  },

  removeToken() {
    localStorage.removeItem("resumeiq_token");
    localStorage.removeItem("resumeiq_user_email");
  },

  async request(endpoint, options = {}) {
    const headers = options.headers || {};
    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const config = {
      ...options,
      headers
    };

    try {
      const response = await fetch(endpoint, config);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || data.error || `HTTP error ${response.status}`);
      }
      return data;
    } catch (err) {
      console.error(`API Error on ${endpoint}:`, err);
      throw err;
    }
  },

  get(endpoint) {
    return this.request(endpoint, { method: "GET" });
  },

  postMultipart(endpoint, formData) {
    return this.request(endpoint, {
      method: "POST",
      body: formData
    });
  },

  delete(endpoint) {
    return this.request(endpoint, { method: "DELETE" });
  }
};

// UI Notifications (Toast)
function showToast(message, type = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerText = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Dark/Light Theme Handler
function initTheme() {
  const saved = localStorage.getItem("resumeiq_theme") || "light";
  document.documentElement.setAttribute("data-theme", saved);
  updateThemeIcon(saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "light";
  const target = current === "light" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", target);
  localStorage.setItem("resumeiq_theme", target);
  updateThemeIcon(target);
}

function updateThemeIcon(theme) {
  const btn = document.getElementById("theme-toggle-btn");
  if (btn) {
    btn.innerHTML = theme === "dark" ? "☀️" : "🌙";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  const btn = document.getElementById("theme-toggle-btn");
  if (btn) {
    btn.addEventListener("click", toggleTheme);
  }
});
