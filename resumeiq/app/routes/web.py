from flask import Blueprint, render_template

web_bp = Blueprint("web", __name__)

@web_bp.route("/")
def index():
    return render_template("index.html")

@web_bp.route("/login")
def login():
    return render_template("login.html")

@web_bp.route("/upload")
def upload():
    return render_template("upload.html")

@web_bp.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@web_bp.route("/history")
def history():
    return render_template("history.html")

