import os
import io
import zipfile
import tarfile
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, flash, send_file,
    abort, jsonify
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required,
    current_user, UserMixin
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ----------------------------
# Config
# ----------------------------
APP_TITLE = "LightDrive"
ROOT_DIR = os.path.abspath(os.environ.get("FILE_ROOT", "./storage"))  # sandbox root
DB_PATH = os.path.abspath(os.environ.get("FILEMGR_DB", "./users.db"))

os.makedirs(ROOT_DIR, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

login_manager = LoginManager(app)
login_manager.login_view = "login"

# ----------------------------
# DB + User model (sqlite3)
# ----------------------------
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('admin','editor','viewer'))
    )
    """)
    conn.commit()
    conn.close()

init_db()

class User(UserMixin):
    def __init__(self, id_, username, role):
        self.id = id_
        self.username = username
        self.role = role

    @staticmethod
    def get_by_username(username):
        conn = db()
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if row:
            return User(row["id"], row["username"], row["role"])
        return None

    @staticmethod
    def get_by_id(id_):
        conn = db()
        row = conn.execute("SELECT * FROM users WHERE id=?", (id_,)).fetchone()
        conn.close()
        if row:
            return User(row["id"], row["username"], row["role"])
        return None

    @staticmethod
    def count():
        conn = db()
        (count,) = conn.execute("SELECT COUNT(*) FROM users").fetchone()
        conn.close()
        return count

    @staticmethod
    def create(username, password, role):
        ph = generate_password_hash(password)
        conn = db()
        conn.execute("INSERT INTO users(username,password_hash,role) VALUES (?,?,?)",
                     (username, ph, role))
        conn.commit()
        conn.close()

    def check_password(self, password):
        conn = db()
        row = conn.execute("SELECT password_hash FROM users WHERE id=?", (self.id,)).fetchone()
        conn.close()
        return check_password_hash(row["password_hash"], password)

# ----------------------------
# Auth helpers
# ----------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(int(user_id))

def role_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role not in roles:
                flash("Insufficient permissions.", "error")
                return redirect(url_for("browse"))
            return fn(*args, **kwargs)
        return wrapper
    return deco

def can_edit():
    return current_user.is_authenticated and current_user.role in ("admin", "editor")

def can_delete():
    return current_user.is_authenticated and current_user.role == "admin"

# ----------------------------
# Path helpers (sandboxing)
# ----------------------------
def safe_join(root: str, rel: str) -> str:
    # Normalize and ensure path stays inside ROOT_DIR
    rel = rel.strip().lstrip("/").replace("\\", "/")
    final = os.path.abspath(os.path.join(root, rel))
    if not final.startswith(os.path.abspath(root) + os.sep) and final != os.path.abspath(root):
        abort(400, "Invalid path")
    return final

def relpath_from_root(abs_path: str) -> str:
    abs_root = os.path.abspath(ROOT_DIR)
    ap = os.path.abspath(abs_path)
    if ap == abs_root:
        return ""
    return ap[len(abs_root):].lstrip(os.sep).replace("\\", "/")

def human_size(n):
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    f = float(n)
    while f >= 1024 and i < len(units)-1:
        f /= 1024.0
        i += 1
    if i == 0:
        return f"{int(f)} {units[i]}"
    return f"{f:.1f} {units[i]}"

# ----------------------------
# Auth routes
# ----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    # If there are no users, show bootstrap form to create the first admin
    no_users = User.count() == 0
    if request.method == "POST":
        if no_users:
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            if not username or not password:
                flash("Provide username and password.", "error")
                return render_template("login.html", no_users=True, app_title=APP_TITLE)
            User.create(username, password, "admin")
            user = User.get_by_username(username)
            login_user(user)
            flash("Admin account created.", "success")
            return redirect(url_for("browse"))
        else:
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = User.get_by_username(username)
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for("browse"))
            flash("Invalid credentials.", "error")
    return render_template("login.html", no_users=no_users, app_title=APP_TITLE)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/users", methods=["GET", "POST"])
@role_required("admin")
def users():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            role = request.form.get("role", "viewer")
            if not username or not password:
                flash("Username & password required.", "error")
            else:
                try:
                    User.create(username, password, role)
                    flash("User created.", "success")
                except sqlite3.IntegrityError:
                    flash("Username already exists.", "error")
        elif action == "delete":
            uid = request.form.get("id")
            if str(current_user.id) == str(uid):
                flash("You cannot delete yourself.", "error")
            else:
                conn = db()
                conn.execute("DELETE FROM users WHERE id=?", (uid,))
                conn.commit()
                conn.close()
                flash("User deleted.", "success")
    conn = db()
    rows = conn.execute("SELECT id, username, role FROM users ORDER BY username").fetchall()
    conn.close()
    return render_template("users.html", users=rows, app_title=APP_TITLE)

# ----------------------------
# Core file browser
# ----------------------------
@app.route("/")
@login_required
def browse():
    rel = request.args.get("path", "").strip().lstrip("/").replace("\\", "/")
    abs_dir = safe_join(ROOT_DIR, rel)

    if not os.path.exists(abs_dir):
        abort(404)

    # If a file path is passed, show the parent directory instead
    if os.path.isfile(abs_dir):
        abs_dir = os.path.dirname(abs_dir)
        rel = relpath_from_root(abs_dir)

    entries = []
    with os.scandir(abs_dir) as it:
        for e in it:
            try:
                stat = e.stat()
                entries.append({
                    "name": e.name,
                    "is_dir": e.is_dir(),
                    "size": (stat.st_size if not e.is_dir() else 0),
                    "size_h": (human_size(stat.st_size) if not e.is_dir() else ""),
                    "mtime": stat.st_mtime,
                    "mtime_h": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    "rel": relpath_from_root(os.path.join(abs_dir, e.name))
                })
            except FileNotFoundError:
                continue

    # Sort: directories first, then name
    entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

    # Breadcrumbs
    crumbs = []
    parts = [p for p in rel.split("/") if p] if rel else []
    acc = ""
    crumbs.append({"name": "root", "path": ""})
    for p in parts:
        acc = f"{acc}/{p}" if acc else p
        crumbs.append({"name": p, "path": acc})

    return render_template(
        "browse.html",
        app_title=APP_TITLE,
        current_rel=rel,
        crumbs=crumbs,
        entries=entries,
        can_edit=can_edit(),
        can_delete=can_delete()
    )

# ----------------------------
# Uploads (files + folders)
# ----------------------------
@app.route("/upload", methods=["POST"])
@login_required
def upload():
    if not can_edit():
        abort(403)
    target_rel = request.form.get("target_dir", "").strip().lstrip("/")
    target_abs = safe_join(ROOT_DIR, target_rel)
    os.makedirs(target_abs, exist_ok=True)

    # Expect multiple files; each may include a client-provided relative_path
    files = request.files.getlist("files[]")
    count = 0
    for f in files:
        if not f.filename:
            continue
        raw_name = f.filename
        rel_path = request.form.get(f"relpath_{raw_name}") or request.form.get("relative_path") or ""
        # Prefer webkitRelativePath if supplied via input[type=file] directory selection
        if hasattr(f, "webkit_relative_path") and f.webkit_relative_path:
            rel_path = f.webkit_relative_path

        rel_path = (rel_path or "").lstrip("/").replace("\\", "/")
        filename = secure_filename(os.path.basename(raw_name))
        subdir = os.path.dirname(rel_path) if rel_path else ""
        dest_dir = safe_join(target_abs, subdir)
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, filename)
        f.save(dest_path)
        count += 1

    return jsonify({"ok": True, "uploaded": count})

# ----------------------------
# Download (file or folder) as raw / zip / tar
# ----------------------------
@app.route("/download")
@login_required
def download():
    rel = request.args.get("path", "").strip().lstrip("/")
    fmt = (request.args.get("format", "raw") or "raw").lower()
    abs_path = safe_join(ROOT_DIR, rel)
    if not os.path.exists(abs_path):
        abort(404)

    if os.path.isfile(abs_path):
        # Single file
        if fmt == "raw":
            return send_file(abs_path, as_attachment=True,
                             download_name=os.path.basename(abs_path))
        elif fmt == "zip":
            mem = io.BytesIO()
            with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(abs_path, arcname=os.path.basename(abs_path))
            mem.seek(0)
            return send_file(mem, as_attachment=True,
                             download_name=os.path.basename(abs_path) + ".zip")
        elif fmt == "tar":
            mem = io.BytesIO()
            with tarfile.open(fileobj=mem, mode="w:gz") as tf:
                tf.add(abs_path, arcname=os.path.basename(abs_path))
            mem.seek(0)
            return send_file(mem, as_attachment=True,
                             download_name=os.path.basename(abs_path) + ".tar.gz")
        else:
            abort(400, "Invalid format")

    # Directory
    base = os.path.basename(abs_path.rstrip(os.sep)) or "folder"
    if fmt == "zip":
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(abs_path):
                for name in files:
                    full = os.path.join(root, name)
                    rel_arc = os.path.relpath(full, start=os.path.dirname(abs_path))
                    zf.write(full, arcname=rel_arc)
        mem.seek(0)
        return send_file(mem, as_attachment=True, download_name=f"{base}.zip")
    elif fmt == "tar":
        mem = io.BytesIO()
        with tarfile.open(fileobj=mem, mode="w:gz") as tf:
            tf.add(abs_path, arcname=base)
        mem.seek(0)
        return send_file(mem, as_attachment=True, download_name=f"{base}.tar.gz")
    else:
        abort(400, "Use format=zip or format=tar for folders")

# ----------------------------
# Delete (files or folders)
# ----------------------------
@app.route("/delete", methods=["POST"])
@login_required
def delete():
    if not can_delete():
        abort(403)
    rel = request.form.get("path", "").strip().lstrip("/")
    abs_path = safe_join(ROOT_DIR, rel)
    if not os.path.exists(abs_path):
        return jsonify({"ok": False, "error": "Not found"}), 404

    try:
        if os.path.isdir(abs_path):
            shutil.rmtree(abs_path)
        else:
            os.remove(abs_path)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ----------------------------
# Text editor (simple)
# ----------------------------
TEXT_MAX_BYTES = 2 * 1024 * 1024  # 2 MB

@app.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    if request.method == "GET":
        rel = request.args.get("path", "").strip().lstrip("/")
        abs_path = safe_join(ROOT_DIR, rel)
        if not os.path.isfile(abs_path):
            abort(404)
        try:
            size = os.path.getsize(abs_path)
            if size > TEXT_MAX_BYTES:
                flash("File too large to edit online.", "error")
                return redirect(url_for("browse", path=relpath_from_root(os.path.dirname(abs_path))))
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            content = ""
        return render_template(
            "editor.html",
            app_title=APP_TITLE,
            rel=rel,
            content=content,
            can_edit=can_edit()
        )
    else:
        if not can_edit():
            abort(403)
        rel = request.form.get("path", "").strip().lstrip("/")
        content = request.form.get("content", "")
        abs_path = safe_join(ROOT_DIR, rel)
        # Ensure parent exists
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        flash("Saved.", "success")
        return redirect(url_for("browse", path=relpath_from_root(os.path.dirname(abs_path))))

# ----------------------------
# Utilities
# ----------------------------
@app.template_filter("icon")
def icon_filter(is_dir, name):
    ext = (name.rsplit(".", 1)[-1].lower() if "." in name else "")
    if is_dir:
        return "📁"
    if ext in {"txt","md","json","yml","yaml","toml","py","js","ts","css","html"}:
        return "📄"
    if ext in {"png","jpg","jpeg","gif","webp","svg"}:
        return "🖼️"
    if ext in {"zip","tar","gz","rar","7z"}:
        return "🗜️"
    return "📦"

@app.errorhandler(400)
def bad_request(e):
    return render_template("error.html", app_title=APP_TITLE, code=400, message=str(e)), 400

@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", app_title=APP_TITLE, code=403, message="Forbidden"), 403

@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", app_title=APP_TITLE, code=404, message="Not found"), 404

# ----------------------------
# Run
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "80")), debug=True)
