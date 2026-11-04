"""Bug Tracker: a small Flask + SQLite app with a JSON REST API."""
import logging
import os

from flask import Flask, jsonify, render_template, request

import database as db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
)
log = logging.getLogger("bugtracker")


def validate_bug(data, partial=False):
    """Check request JSON. Returns (clean_fields, error_message)."""
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object."

    clean = {}
    if "title" in data or not partial:
        title = str(data.get("title", "")).strip()
        if not title:
            return None, "Title is required."
        if len(title) > 120:
            return None, "Title must be 120 characters or fewer."
        clean["title"] = title

    if "description" in data:
        clean["description"] = str(data["description"]).strip()
    elif not partial:
        clean["description"] = ""

    if "severity" in data or not partial:
        severity = data.get("severity", "Medium")
        if severity not in db.SEVERITIES:
            return None, f"Severity must be one of: {', '.join(db.SEVERITIES)}."
        clean["severity"] = severity

    if "status" in data or not partial:
        status = data.get("status", "Open")
        if status not in db.STATUSES:
            return None, f"Status must be one of: {', '.join(db.STATUSES)}."
        clean["status"] = status

    return clean, None


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "bugs.db"
    )
    db.init_db(app.config["DB_PATH"])

    def path():
        return app.config["DB_PATH"]

    @app.get("/")
    def index():
        return render_template(
            "index.html", severities=db.SEVERITIES, statuses=db.STATUSES
        )

    @app.get("/api/bugs")
    def list_bugs():
        bugs = db.list_bugs(
            path(),
            severity=request.args.get("severity") or None,
            status=request.args.get("status") or None,
            search=(request.args.get("q") or "").strip() or None,
        )
        return jsonify(bugs)

    @app.get("/api/stats")
    def stats():
        return jsonify(db.get_stats(path()))

    @app.get("/api/bugs/<int:bug_id>")
    def get_bug(bug_id):
        bug = db.get_bug(path(), bug_id)
        if bug is None:
            return jsonify(error="Bug not found."), 404
        return jsonify(bug)

    @app.post("/api/bugs")
    def create_bug():
        clean, error = validate_bug(request.get_json(silent=True))
        if error:
            log.warning("Create rejected: %s", error)
            return jsonify(error=error), 400
        bug_id = db.create_bug(path(), **clean)
        log.info("Created bug #%s (%s)", bug_id, clean["severity"])
        return jsonify(db.get_bug(path(), bug_id)), 201

    @app.put("/api/bugs/<int:bug_id>")
    def update_bug(bug_id):
        clean, error = validate_bug(request.get_json(silent=True), partial=True)
        if error:
            log.warning("Update of #%s rejected: %s", bug_id, error)
            return jsonify(error=error), 400
        if not db.update_bug(path(), bug_id, clean):
            return jsonify(error="Bug not found."), 404
        log.info("Updated bug #%s: %s", bug_id, ", ".join(clean) or "no changes")
        return jsonify(db.get_bug(path(), bug_id))

    @app.delete("/api/bugs/<int:bug_id>")
    def delete_bug(bug_id):
        if not db.delete_bug(path(), bug_id):
            return jsonify(error="Bug not found."), 404
        log.info("Deleted bug #%s", bug_id)
        return "", 204

    @app.errorhandler(404)
    def not_found(_):
        return jsonify(error="Not found."), 404

    @app.errorhandler(500)
    def server_error(exc):
        log.exception("Unhandled error: %s", exc)
        return jsonify(error="Something went wrong on the server."), 500

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
