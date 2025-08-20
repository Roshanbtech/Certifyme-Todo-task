from __future__ import annotations
from datetime import timedelta, datetime
import os, secrets
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    abort,
    g,
)
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, init_db, User, Todo


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # --- secure session defaults ---
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)

    # --- DATABASE CONFIG ---
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///db.sqlite3"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if test_config:
        app.config.update(test_config)

    # Bind SQLAlchemy and create tables
    init_db(app)

    # ---------------- CSRF (minimal) ----------------
    def _get_csrf_token() -> str:
        token = session.get("_csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["_csrf_token"] = token
        return token

    @app.before_request
    def _csrf_protect():
        if app.config.get("TESTING"):
            return
        if request.method == "POST":
            token_session = session.get("_csrf_token")
            token_form = request.form.get("csrf_token")
            if not token_session or token_session != token_form:
                abort(400, description="CSRF token missing or invalid.")

    # Make csrf_token() available in templates
    app.jinja_env.globals["csrf_token"] = _get_csrf_token

    # --------------- load current user ---------------
    @app.before_request
    def _load_user():
        g.user = None
        uid = session.get("user_id")
        if uid:
            g.user = db.session.get(User, uid)

    # --------------- login-required decorator --------
    def login_required(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)

        return wrapper

    # ---------------- routes -------------------------

    @app.get("/")
    def index():
        # send logged-in users to dashboard; others to login
        if session.get("user_id"):
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            name = (request.form.get("name") or "").strip()
            email = (request.form.get("email") or "").strip().lower()
            password = request.form.get("password") or ""
            confirm = request.form.get("confirm_password") or ""

            errs = []
            if len(name) < 2:
                errs.append("Name must be at least 2 characters.")
            if "@" not in email or "." not in email or len(email) < 6:
                errs.append("Enter a valid email address.")
            if len(password) < 8:
                errs.append("Password must be at least 8 characters.")
            if password != confirm:
                errs.append("Passwords do not match.")
            if User.query.filter_by(email=email).first():
                errs.append("Email is already registered.")

            if errs:
                for e in errs:
                    flash(e, "danger")
                return render_template("register.html", name=name, email=email)

            pw_hash = generate_password_hash(
                password, method="pbkdf2:sha256", salt_length=16
            )
            user = User(name=name, email=email, password_hash=pw_hash)
            db.session.add(user)
            db.session.commit()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            password = request.form.get("password") or ""

            user = User.query.filter_by(email=email).first()
            if not user or not check_password_hash(user.password_hash, password):
                flash("Invalid email or password.", "danger")
                return render_template("login.html", email=email)

            session.clear()
            session.permanent = True
            session["user_id"] = user.id
            session["user_name"] = user.name
            flash(f"Welcome back, {user.name.split()[0]}!", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("dashboard"))

        return render_template("login.html")

    @app.get("/logout")
    def logout():
        session.clear()
        flash("You have been logged out.", "info")
        return redirect(url_for("login"))

    # ---------- Todos (Create/List/Edit/Toggle/Delete) ----------
    @app.route("/dashboard", methods=["GET", "POST"])
    @login_required
    def dashboard():
        # Create todo
        if request.method == "POST":
            title = (request.form.get("title") or "").strip()
            if not title:
                flash("Task title cannot be empty.", "danger")
            elif len(title) > 150:
                flash("Task title must be under 150 characters.", "danger")
            else:
                todo = Todo(user_id=session["user_id"], title=title)
                db.session.add(todo)
                db.session.commit()
                flash("Task added.", "success")
            return redirect(url_for("dashboard"))

        # List user’s todos (newest first)
        todos = (
            Todo.query.filter_by(user_id=session["user_id"])
            .order_by(Todo.created_at.desc())
            .all()
        )
        return render_template("dashboard.html", todos=todos)

    @app.post("/todo/<int:todo_id>/toggle")
    @login_required
    def toggle_todo(todo_id: int):
        todo = Todo.query.filter_by(id=todo_id, user_id=session["user_id"]).first()
        if not todo:
            flash("Task not found.", "warning")
        else:
            todo.is_done = not todo.is_done
            db.session.commit()  # updates updated_at automatically
            flash("Task updated.", "success")
        return redirect(url_for("dashboard"))

    @app.post("/todo/<int:todo_id>/delete")
    @login_required
    def delete_todo(todo_id: int):
        todo = Todo.query.filter_by(id=todo_id, user_id=session["user_id"]).first()
        if not todo:
            flash("Task not found.", "warning")
        else:
            db.session.delete(todo)
            db.session.commit()
            flash("Task deleted.", "info")
        return redirect(url_for("dashboard"))

    @app.post("/todo/<int:todo_id>/edit")
    @login_required
    def edit_todo(todo_id: int):
        # Update title (inline edit)
        new_title = (request.form.get("title") or "").strip()
        if not new_title:
            flash("Task title cannot be empty.", "danger")
            return redirect(url_for("dashboard"))
        if len(new_title) > 150:
            flash("Task title must be under 150 characters.", "danger")
            return redirect(url_for("dashboard"))

        todo = Todo.query.filter_by(id=todo_id, user_id=session["user_id"]).first()
        if not todo:
            flash("Task not found.", "warning")
            return redirect(url_for("dashboard"))

        todo.title = new_title
        db.session.commit()  # updated_at auto-changes
        flash("Task title saved.", "success")
        return redirect(url_for("dashboard"))

    # --- Forgot / Reset Password (manual) ---
    @app.route("/forgot-password", methods=["GET", "POST"])
    def forgot_password():
        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            user = User.query.filter_by(email=email).first()
            if not user:
                # Don’t reveal whether the email exists
                flash("If the email exists, you'll be able to reset the password next.", "info")
                return render_template("forgot_password.html")

            session["reset_user_id"] = user.id
            session["reset_started_at"] = datetime.utcnow().isoformat()
            flash("Identity verified. Please set a new password.", "success")
            return redirect(url_for("reset_password"))

        return render_template("forgot_password.html")

    @app.route("/reset-password", methods=["GET", "POST"])
    def reset_password():
        uid = session.get("reset_user_id")
        ts = session.get("reset_started_at")

        if not uid or not ts:
            flash("Password reset session not found or expired. Please try again.", "warning")
            return redirect(url_for("forgot_password"))

        try:
            started = datetime.fromisoformat(ts)
        except Exception:
            started = datetime.utcnow() - timedelta(hours=1)

        if datetime.utcnow() - started > timedelta(minutes=15):
            session.pop("reset_user_id", None)
            session.pop("reset_started_at", None)
            flash("Password reset session expired. Please try again.", "warning")
            return redirect(url_for("forgot_password"))

        if request.method == "POST":
            new_pw = request.form.get("password") or ""
            confirm = request.form.get("confirm_password") or ""

            errs = []
            if len(new_pw) < 8:
                errs.append("Password must be at least 8 characters.")
            if new_pw != confirm:
                errs.append("Passwords do not match.")

            if errs:
                for e in errs:
                    flash(e, "danger")
                return render_template("reset_password.html")

            user = db.session.get(User, uid)
            if not user:
                flash("User not found. Please try again.", "danger")
                return redirect(url_for("forgot_password"))

            user.password_hash = generate_password_hash(
                new_pw, method="pbkdf2:sha256", salt_length=16
            )
            db.session.commit()

            # Clear reset state so the flow can't be reused
            session.pop("reset_user_id", None)
            session.pop("reset_started_at", None)

            flash("Password updated. Please log in.", "success")
            return redirect(url_for("login"))

        return render_template("reset_password.html")

    # diagnostics
    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/db-ping")
    def db_ping():
        return {"users": User.query.count(), "todos": Todo.query.count()}

    @app.errorhandler(400)
    def bad_request(e):
        return render_template("dashboard.html", error=str(e)), 400

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
