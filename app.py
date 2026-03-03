from __future__ import annotations

import os
import pathlib
import subprocess
from datetime import datetime
from urllib.parse import urlparse

from flask import Flask, flash, redirect, render_template, request, send_file, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = pathlib.Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
USERS_DIR = STORAGE_DIR / "users"
GLOBAL_DIR = STORAGE_DIR / "global"


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-in-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'app.db').as_posix()}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SHARE_TTL_SECONDS"] = int(os.getenv("SHARE_TTL_SECONDS", "3600"))

    USERS_DIR.mkdir(parents=True, exist_ok=True)
    GLOBAL_DIR.mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "login"

    with app.app_context():
        db.create_all()

    register_routes(app)
    return app


db = SQLAlchemy()
login_manager = LoginManager()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


def user_root(user: User) -> pathlib.Path:
    path = USERS_DIR / str(user.id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_path(root: pathlib.Path, rel_path: str) -> pathlib.Path:
    rel = pathlib.Path(rel_path or ".")
    candidate = (root / rel).resolve()
    if root.resolve() not in candidate.parents and candidate != root.resolve():
        raise ValueError("Invalid path")
    return candidate


def list_entries(root: pathlib.Path, rel_path: str):
    current = safe_path(root, rel_path)
    entries = []
    for entry in sorted(current.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
        entries.append(
            {
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if entry.is_file() else None,
                "modified": datetime.fromtimestamp(entry.stat().st_mtime),
            }
        )
    return current, entries


def register_routes(app: Flask) -> None:
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("files"))
        return redirect(url_for("login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form["username"].strip()
            password = request.form["password"].strip()
            if not username or not password:
                flash("Username and password are required", "danger")
                return redirect(url_for("register"))
            if User.query.filter_by(username=username).first():
                flash("Username already exists", "danger")
                return redirect(url_for("register"))

            user = User(username=username, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            user_root(user)
            flash("Account created. Please sign in.", "success")
            return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form["username"].strip()
            password = request.form["password"].strip()
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                return redirect(url_for("files"))
            flash("Invalid credentials", "danger")
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.route("/files")
    @login_required
    def files():
        location = request.args.get("location", "user")
        rel_path = request.args.get("path", "")
        root = user_root(current_user) if location == "user" else GLOBAL_DIR
        try:
            current_dir, entries = list_entries(root, rel_path)
        except (FileNotFoundError, ValueError):
            flash("Invalid path", "danger")
            return redirect(url_for("files", location=location))

        root_resolved = root.resolve()
        rel_current = str(current_dir.resolve().relative_to(root_resolved))
        if rel_current == ".":
            rel_current = ""

        return render_template(
            "files.html",
            entries=entries,
            location=location,
            rel_path=rel_current,
            parent_path=str(pathlib.Path(rel_current).parent) if rel_current else "",
            ttl=app.config["SHARE_TTL_SECONDS"],
        )

    @app.route("/download-url", methods=["POST"])
    @login_required
    def download_url():
        url = request.form.get("url", "").strip()
        rel_path = request.form.get("path", "")
        if not urlparse(url).scheme:
            flash("Please provide a valid URL", "danger")
            return redirect(url_for("files", location="user", path=rel_path))

        try:
            output_dir = safe_path(user_root(current_user), rel_path)
        except ValueError:
            flash("Invalid destination", "danger")
            return redirect(url_for("files", location="user"))

        proc = subprocess.run(
            ["python", str(BASE_DIR / "downloader.py"), url, str(output_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            flash(f"Download failed: {proc.stderr.strip()}", "danger")
        else:
            flash("File downloaded successfully", "success")
        return redirect(url_for("files", location="user", path=rel_path))

    @app.route("/download")
    @login_required
    def download_file():
        location = request.args.get("location", "user")
        rel_path = request.args.get("path", "")
        root = user_root(current_user) if location == "user" else GLOBAL_DIR
        file_path = safe_path(root, rel_path)
        if not file_path.exists() or not file_path.is_file():
            flash("File not found", "danger")
            return redirect(url_for("files", location=location))
        return send_file(file_path, as_attachment=True)

    @app.route("/rename", methods=["POST"])
    @login_required
    def rename_file():
        location = request.form.get("location", "user")
        root = user_root(current_user) if location == "user" else GLOBAL_DIR
        rel_path = request.form.get("path", "")
        new_name = request.form.get("new_name", "").strip()
        if not new_name:
            flash("New name required", "danger")
            return redirect(url_for("files", location=location))

        source = safe_path(root, rel_path)
        target = source.with_name(new_name)
        try:
            source.rename(target)
            flash("Renamed", "success")
        except OSError as exc:
            flash(f"Rename failed: {exc}", "danger")

        back_path = str(pathlib.Path(rel_path).parent) if rel_path else ""
        return redirect(url_for("files", location=location, path=back_path if back_path != "." else ""))

    @app.route("/to-global", methods=["POST"])
    @login_required
    def to_global():
        rel_path = request.form.get("path", "")
        source = safe_path(user_root(current_user), rel_path)
        if not source.exists() or not source.is_file():
            flash("Source file not found", "danger")
            return redirect(url_for("files", location="user"))

        target = GLOBAL_DIR / source.name
        counter = 1
        while target.exists():
            target = GLOBAL_DIR / f"{source.stem}_{counter}{source.suffix}"
            counter += 1

        source.replace(target)
        flash("File moved to global folder", "success")
        return redirect(url_for("files", location="user", path=str(pathlib.Path(rel_path).parent)))

    @app.route("/share", methods=["POST"])
    @login_required
    def share():
        import itsdangerous

        location = request.form.get("location", "user")
        rel_path = request.form.get("path", "")
        root = user_root(current_user) if location == "user" else GLOBAL_DIR
        target = safe_path(root, rel_path)
        if not target.exists() or not target.is_file():
            flash("File not found", "danger")
            return redirect(url_for("files", location=location))

        signer = itsdangerous.URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="file-share")
        token = signer.dumps({"location": location, "path": rel_path, "owner": current_user.id})
        share_url = url_for("shared_file", token=token, _external=True)
        flash(f"Temporary URL (expires in {app.config['SHARE_TTL_SECONDS']}s): {share_url}", "success")
        return redirect(url_for("files", location=location, path=str(pathlib.Path(rel_path).parent)))

    @app.route("/shared/<token>")
    def shared_file(token: str):
        import itsdangerous

        signer = itsdangerous.URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="file-share")
        try:
            payload = signer.loads(token, max_age=app.config["SHARE_TTL_SECONDS"])
        except itsdangerous.SignatureExpired:
            return "Share link expired", 410
        except itsdangerous.BadData:
            return "Invalid share link", 400

        location = payload.get("location", "user")
        rel_path = payload.get("path", "")
        owner_id = payload.get("owner")
        if location == "user":
            root = USERS_DIR / str(owner_id)
        else:
            root = GLOBAL_DIR
        file_path = safe_path(root, rel_path)
        if not file_path.exists() or not file_path.is_file():
            return "File not found", 404
        return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=True)
