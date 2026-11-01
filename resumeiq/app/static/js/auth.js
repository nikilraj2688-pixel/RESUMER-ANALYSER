/**
 * Firebase Client Authentication Wrapper
 * Connected to Firebase project: resume--analyser-96
 * Includes graceful handling for unconfigured Firebase providers (fallback to instant sign-in).
 */

const firebaseConfig = {
  apiKey: "AIzaSyCk44mzknE0NHMg2MhlbI00eDusuAIv7PE",
  authDomain: "resume--analyser-96.firebaseapp.com",
  projectId: "resume--analyser-96",
  storageBucket: "resume--analyser-96.firebasestorage.app",
  messagingSenderId: "719732663203",
  appId: "1:719732663203:web:0c5400919b2c8543c6b016",
  measurementId: "G-26LEY1GZ3L"
};

// Initialize Firebase App
if (typeof firebase !== "undefined" && !firebase.apps.length) {
  try {
    firebase.initializeApp(firebaseConfig);
    if (firebase.analytics) {
      try {
        firebase.analytics();
      } catch (e) {}
    }
  } catch (e) {
    console.warn("Firebase initialize warning:", e);
  }
}

const Auth = {
  currentUser: null,

  init() {
    if (typeof firebase !== "undefined" && firebase.auth) {
      try {
        firebase.auth().onAuthStateChanged(async (user) => {
          if (user) {
            const token = await user.getIdToken();
            localStorage.setItem("resumeiq_token", token);
            localStorage.setItem("resumeiq_user_email", user.email || "user@resumeiq.ai");
            this.currentUser = { email: user.email, token: token, uid: user.uid };
          } else {
            const localToken = localStorage.getItem("resumeiq_token");
            const localEmail = localStorage.getItem("resumeiq_user_email");
            if (localToken && localEmail) {
              this.currentUser = { email: localEmail, token: localToken };
            } else {
              this.currentUser = null;
            }
          }
          this.updateNavbar();
        });
      } catch (e) {
        console.warn("Auth state observer error:", e);
      }
    } else {
      const localToken = localStorage.getItem("resumeiq_token");
      const localEmail = localStorage.getItem("resumeiq_user_email");
      if (localToken && localEmail) {
        this.currentUser = { email: localEmail, token: localToken };
        this.updateNavbar();
      }
    }
  },

  async loginWithEmail(email, password) {
    if (typeof firebase !== "undefined" && firebase.auth) {
      try {
        const userCredential = await firebase.auth().signInWithEmailAndPassword(email, password);
        const token = await userCredential.user.getIdToken();
        localStorage.setItem("resumeiq_token", token);
        localStorage.setItem("resumeiq_user_email", userCredential.user.email);
        this.currentUser = { email: userCredential.user.email, token: token, uid: userCredential.user.uid };
        showToast("Signed in successfully with Firebase!", "success");
        window.location.href = "/upload";
        return;
      } catch (err) {
        // If provider not yet turned on in console or user not found, provide helpful notice & seamlessly proceed
        if (err.code === "auth/configuration-not-found" || err.code === "auth/operation-not-allowed") {
          showToast("Email/Password not yet toggled ON in Firebase Console. Signing in via local session...", "info");
          setTimeout(() => {
            this.loginDemo(email);
          }, 1000);
          return;
        }

        if (err.code === "auth/user-not-found" || err.code === "auth/invalid-credential") {
          try {
            const signupCredential = await firebase.auth().createUserWithEmailAndPassword(email, password);
            const token = await signupCredential.user.getIdToken();
            localStorage.setItem("resumeiq_token", token);
            localStorage.setItem("resumeiq_user_email", signupCredential.user.email);
            showToast("Firebase Account created and signed in!", "success");
            window.location.href = "/upload";
            return;
          } catch (signupErr) {
            if (signupErr.code === "auth/configuration-not-found" || signupErr.code === "auth/operation-not-allowed") {
              this.loginDemo(email);
              return;
            }
            showToast(signupErr.message || err.message, "error");
            return;
          }
        }
        showToast(err.message, "error");
      }
    } else {
      this.loginDemo(email);
    }
  },

  async loginWithGoogle() {
    if (typeof firebase !== "undefined" && firebase.auth) {
      try {
        const provider = new firebase.auth.GoogleAuthProvider();
        const result = await firebase.auth().signInWithPopup(provider);
        const token = await result.user.getIdToken();
        localStorage.setItem("resumeiq_token", token);
        localStorage.setItem("resumeiq_user_email", result.user.email);
        this.currentUser = { email: result.user.email, token: token, uid: result.user.uid };
        showToast(`Signed in with Google as ${result.user.email}`, "success");
        window.location.href = "/upload";
      } catch (err) {
        console.error("Google Sign-In Error:", err);
        if (err.code === "auth/configuration-not-found" || err.code === "auth/operation-not-allowed") {
          showToast("Google Auth not enabled in Firebase Console. Using local demo account...", "info");
          setTimeout(() => {
            this.loginDemo("google.user@resumeiq.ai");
          }, 1000);
        } else {
          showToast(err.message || "Google Sign-In cancelled or failed.", "error");
        }
      }
    } else {
      this.loginDemo("google.user@resumeiq.ai");
    }
  },

  loginDemo(email = "demo@resumeiq.ai") {
    const token = "demo_token_" + btoa(email).substring(0, 10);
    localStorage.setItem("resumeiq_token", token);
    localStorage.setItem("resumeiq_user_email", email);
    this.currentUser = { email, token };
    this.updateNavbar();
    showToast(`Signed in as ${email}`, "success");
    window.location.href = "/upload";
  },

  async logout() {
    if (typeof firebase !== "undefined" && firebase.auth) {
      try {
        await firebase.auth().signOut();
      } catch (e) {}
    }
    localStorage.removeItem("resumeiq_token");
    localStorage.removeItem("resumeiq_user_email");
    this.currentUser = null;
    this.updateNavbar();
    showToast("Signed out successfully.", "info");
    window.location.href = "/";
  },

  updateNavbar() {
    const authActions = document.getElementById("auth-actions");
    if (!authActions) return;

    if (this.currentUser) {
      authActions.innerHTML = `
        <span style="font-size: 0.9rem; color: var(--text-secondary); margin-right: 0.5rem;">${this.currentUser.email}</span>
        <button onclick="Auth.logout()" class="btn btn-outline" style="padding: 0.4rem 0.8rem; font-size: 0.85rem;">Logout</button>
      `;
    } else {
      authActions.innerHTML = `
        <a href="/login" class="btn btn-primary" style="padding: 0.4rem 0.9rem; font-size: 0.85rem;">Sign In</a>
      `;
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  Auth.init();
});
