"""Web UI for managing SFgame bot accounts.

Usage: uv run web.py
"""

import asyncio
import json
import os
import sys
from datetime import UTC, datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for

sys.path.insert(0, os.path.dirname(__file__))

from sfbot.constants import (
    CHARACTER_CLASS_INDEX,
    VALUES_DELIMITER,
    Attribute,
    CompanionClass,
)
from sfbot.constants.enums import CharClass
from sfbot.logging import BOT_LOG_DIR, LOG_DIR
from sfbot.persistence.accounts import (
    connect_sync,
    delete_account,
    get_all_accounts,
    get_all_characters,
    get_characters_for_account,
    get_stats_for_characters,
    init_db,
    load_config_json,
    save_config_json,
    set_character_enabled,
    set_character_running,
    upsert_account,
    upsert_character,
)
from sfbot.session import (
    SERVER_MAP_CACHE,
    GameSession,
    hash_password,
    init_server_map_async,
    sso_list_characters_async,
)

app = Flask(__name__, template_folder="templates")
app.secret_key = os.environ.get("SECRET_KEY", "dev-fallback-key-change-in-production")

WEB_USERNAME = os.environ["WEB_USERNAME"]
WEB_PASSWORD = os.environ["WEB_PASSWORD"]


@app.before_request
def require_login():
    if request.endpoint in ("web_login", "static"):
        return
    if not session.get("authenticated"):
        return redirect(url_for("web_login"))


@app.route("/login", methods=["GET", "POST"])
def web_login():
    if session.get("authenticated"):
        return redirect(url_for("index"))
    if request.method == "GET":
        return render_template("web_login.html")
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    if username == WEB_USERNAME and password == WEB_PASSWORD:
        session["authenticated"] = True
        return redirect(url_for("index"))
    flash("Invalid credentials.", "error")
    return render_template("web_login.html")


@app.route("/logout", methods=["POST"])
def web_logout():
    session.clear()
    return redirect(url_for("web_login"))


@app.template_filter("display_name")
def display_name_filter(s: str) -> str:
    return s.replace("_", " ").title() if s else s


@app.template_filter("localtime")
def localtime_filter(s: str | None) -> str:
    if not s:
        return ""
    utc_dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    local_dt = utc_dt.astimezone()
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")


ATTRIBUTES = [a.name for a in Attribute]
COMPANION_CLASSES = [c.name for c in CompanionClass]


def fetch_server_map() -> dict[int, str]:
    """Fetch server_id -> server_url mapping from sfgame.net."""
    import requests

    resp = requests.get("https://sfgame.net/config.json", timeout=10)
    data = resp.json()
    servers: dict[int, str] = {}
    for s in data.get("servers", []):
        url = s.get("md") or s.get("d", "")
        if url:
            servers[s["i"]] = url
    return servers


def list_characters(username: str, password_hash: str) -> list[dict]:
    """SSO login and list characters for an account."""
    return asyncio.run(sso_list_characters_async(username, password_hash))


def fetch_char_class(
    username: str, password_hash: str, server: str, character_id: str
) -> str:
    """Log into a character's game server and return its class name."""

    async def run() -> str:
        if not SERVER_MAP_CACHE:
            await init_server_map_async()
        session = GameSession(username, password_hash, server, character_id)
        try:
            await session.login_async()
            values = session.login_data["ownplayersavecharacter"]
            parts = values.split(VALUES_DELIMITER)
            class_id = int(parts[CHARACTER_CLASS_INDEX]) - 1
            return CharClass(class_id).name
        finally:
            await session.close()

    return asyncio.run(run())


@app.route("/")
def index():
    conn = connect_sync()
    try:
        accounts = get_all_accounts(conn)
        all_chars = get_all_characters(conn)
        char_ids = [c["character_id"] for c in all_chars]
        stats_map = get_stats_for_characters(conn, char_ids)

        chars_by_account: dict[int, list[dict]] = {}
        for c in all_chars:
            s = stats_map.get(c["character_id"])
            char = {
                "id": c["id"],
                "name": c["name"],
                "character_id": c["character_id"],
                "server": c["server"],
                "enabled": bool(c["enabled"]),
                "running": bool(c["running"]),
                "has_config": load_config_json(c["character_id"]) is not None,
                "char_class": c["char_class"] or "Unknown",
                "level": s["level"] if s else None,
                "gold": s["silver_total"] // 100 if s else None,
                "silver": s["silver_total"] % 100 if s else None,
                "mushrooms": s["mushrooms"] if s else None,
            }
            chars_by_account.setdefault(c["account_id"], []).append(char)

        account_list = []
        for a in accounts:
            account_list.append(
                {
                    "id": a["id"],
                    "username": a["username"],
                    "characters": chars_by_account.get(a["id"], []),
                }
            )

        return render_template("index.html", accounts=account_list)
    finally:
        conn.close()


@app.route("/add_account", methods=["GET", "POST"])
def add_account():
    if request.method == "GET":
        return render_template("add_account.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        flash("Username and password are required.", "error")
        return render_template("add_account.html")

    password_hash = hash_password(password)

    try:
        server_map = fetch_server_map()
        chars = list_characters(username, password_hash)
    except Exception as e:
        flash(f"Login failed: {e}", "error")
        return render_template("add_account.html")

    if not chars:
        flash("No characters found for this account.", "error")
        return render_template("add_account.html")

    conn = connect_sync()
    try:
        account_id = upsert_account(conn, username, password_hash)
    finally:
        conn.close()

    char_list = []
    for c in chars:
        server_url = server_map.get(c["server_id"], "")
        char_list.append(
            {
                "name": c["name"],
                "character_id": c["id"],
                "server_id": c["server_id"],
                "server_url": server_url,
            }
        )

    return render_template(
        "select_characters.html",
        characters=char_list,
        account_id=account_id,
        username=username,
    )


@app.route("/account/<int:account_id>")
def account_detail(account_id: int):
    conn = connect_sync()
    try:
        acct = conn.execute(
            "SELECT * FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
        if not acct:
            flash("Account not found.", "error")
            return redirect(url_for("index"))

        chars = get_characters_for_account(conn, account_id)
        char_ids = [c["character_id"] for c in chars]
        stats_map = get_stats_for_characters(conn, char_ids)

        char_list = []
        for c in chars:
            s = stats_map.get(c["character_id"])
            char_list.append(
                {
                    "id": c["id"],
                    "name": c["name"],
                    "character_id": c["character_id"],
                    "server": c["server"],
                    "char_class": c["char_class"] or "Unknown",
                    "enabled": bool(c["enabled"]),
                    "running": bool(c["running"]),
                    "has_config": load_config_json(c["character_id"]) is not None,
                    "level": s["level"] if s else None,
                    "gold": s["silver_total"] // 100 if s else None,
                    "silver": s["silver_total"] % 100 if s else None,
                    "mushrooms": s["mushrooms"] if s else None,
                    "lucky_coins": s["lucky_coins"] if s else None,
                    "updated_at": s["updated_at"] if s else None,
                }
            )

        return render_template(
            "account_detail.html",
            account=acct,
            characters=char_list,
        )
    finally:
        conn.close()


@app.route("/save_characters", methods=["POST"])
def save_characters():
    account_id = int(request.form["account_id"])
    selected = request.form.getlist("characters")

    if not selected:
        flash("Select at least one character.", "error")
        return redirect(url_for("add_account"))

    conn = connect_sync()
    try:
        account_row = conn.execute(
            "SELECT * FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
        saved_ids = []
        for char_json in selected:
            char = json.loads(char_json)
            char_class = fetch_char_class(
                account_row["username"],
                account_row["password_hash"],
                char["server_url"],
                char["character_id"],
            )
            char_row_id = upsert_character(
                conn,
                account_id,
                name=char["name"],
                character_id=char["character_id"],
                server=char["server_url"],
                enabled=True,
                char_class=char_class,
            )
            saved_ids.append(char_row_id)
        flash(f"Saved {len(saved_ids)} character(s).", "success")
    finally:
        conn.close()

    return redirect(url_for("index"))


@app.route("/config/<int:char_id>", methods=["GET", "POST"])
def config(char_id: int):
    conn = connect_sync()
    try:
        row = conn.execute(
            "SELECT c.*, a.username FROM characters c "
            "JOIN accounts a ON c.account_id = a.id WHERE c.id = ?",
            (char_id,),
        ).fetchone()
        if not row:
            flash("Character not found.", "error")
            return redirect(url_for("index"))

        if request.method == "GET":
            existing = load_config_json(row["character_id"])
            if existing:
                existing = _normalize_config(existing)
            return render_template(
                "config.html",
                char=row,
                config=existing,
                attributes=ATTRIBUTES,
                companions=COMPANION_CLASSES,
            )

        config_data = parse_config_from_form(request.form)
        save_config_json(row["character_id"], config_data)
        flash("Configuration saved.", "success")
        return redirect(url_for("index"))
    finally:
        conn.close()


@app.route("/toggle/<int:char_id>", methods=["POST"])
def toggle(char_id: int):
    conn = connect_sync()
    try:
        row = conn.execute(
            "SELECT enabled FROM characters WHERE id = ?", (char_id,)
        ).fetchone()
        if row:
            set_character_enabled(conn, char_id, not bool(row["enabled"]))
    finally:
        conn.close()
    return redirect(request.referrer or url_for("index"))


@app.route("/delete_account/<int:account_id>", methods=["POST"])
def delete_account_route(account_id: int):
    conn = connect_sync()
    try:
        delete_account(conn, account_id)
        flash("Account and all its characters removed.", "success")
    finally:
        conn.close()
    return redirect(url_for("index"))


@app.route("/refresh_account/<int:account_id>", methods=["POST"])
def refresh_account(account_id: int):
    conn = connect_sync()
    try:
        row = conn.execute(
            "SELECT * FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
        if not row:
            flash("Account not found.", "error")
            return redirect(url_for("index"))

        username = row["username"]
        password_hash = row["password_hash"]

        try:
            server_map = fetch_server_map()
            chars = list_characters(username, password_hash)
        except Exception as e:
            flash(f"Refresh failed: {e}", "error")
            return redirect(url_for("index"))

        for c in chars:
            server_url = server_map.get(c["server_id"], "")
            character_id = c["id"]
            name = c["name"]
            try:
                char_class = fetch_char_class(
                    username, password_hash, server_url, character_id
                )
            except Exception as e:
                app.logger.warning(
                    f"fetch_char_class failed for {name} ({character_id}): {e}"
                )
                continue
            upsert_character(
                conn,
                account_id,
                name=name,
                character_id=character_id,
                server=server_url,
                char_class=char_class,
            )

        flash(f"Refreshed {len(chars)} character(s) for {username}.", "success")
    finally:
        conn.close()
    return redirect(url_for("index"))


@app.route("/run/<int:char_id>", methods=["POST"])
def run_character(char_id: int):
    conn = connect_sync()
    try:
        set_character_running(conn, char_id, True)
    finally:
        conn.close()
    return redirect(request.referrer or url_for("index"))


@app.route("/pause/<int:char_id>", methods=["POST"])
def pause_character(char_id: int):
    conn = connect_sync()
    try:
        set_character_running(conn, char_id, False)
    finally:
        conn.close()
    return redirect(request.referrer or url_for("index"))


@app.route("/logs/<character_id>")
def view_character_logs(character_id: str):
    log_file = BOT_LOG_DIR / f"{character_id}.log"
    content = log_file.read_text() if log_file.exists() else ""
    conn = connect_sync()
    try:
        row = conn.execute(
            "SELECT name, server FROM characters WHERE character_id = ?",
            (character_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        flash("Character not found.", "error")
        return redirect(url_for("index"))
    return render_template(
        "logs.html",
        content=content,
        name=row["name"],
        server=row["server"],
        character_id=character_id,
    )


@app.route("/clear_logs/<character_id>", methods=["POST"])
def clear_character_logs(character_id: str):
    log_file = BOT_LOG_DIR / f"{character_id}.log"
    if log_file.exists():
        log_file.write_text("")
    flash("Log file cleared.", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/clear_all_logs", methods=["POST"])
def clear_all_logs():
    if LOG_DIR.exists():
        for child in LOG_DIR.rglob("*.log"):
            child.write_text("")
    flash("All logs cleared.", "success")
    return redirect(url_for("index"))


def _normalize_config(config: dict) -> dict:
    """Ensure all expected keys exist in a loaded config dict."""
    zero_attrs = {a: 0 for a in ATTRIBUTES}
    config.setdefault("base_attrs_target_ratios", dict(zero_attrs))
    equip = config.setdefault("equipment_attrs_target_ratios", {})
    equip.setdefault("main", dict(zero_attrs))
    comps = equip.setdefault("companions", {})
    for comp in COMPANION_CLASSES:
        comps.setdefault(comp, dict(zero_attrs))
    gems = config.setdefault("gems_attrs_target_ratios", {})
    gems.setdefault("main", dict(zero_attrs))
    gem_comps = gems.setdefault("companions", {})
    for comp in COMPANION_CLASSES:
        gem_comps.setdefault(comp, dict(zero_attrs))
    return config


def parse_config_from_form(form: dict) -> dict:
    config_data: dict = {
        "base_attrs_target_ratios": {},
        "equipment_attrs_target_ratios": {"main": {}, "companions": {}},
        "gems_attrs_target_ratios": {"main": {}, "companions": {}},
    }

    for attr in ATTRIBUTES:
        config_data["base_attrs_target_ratios"][attr] = float(
            form.get(f"base_{attr}", 0)
        )
        config_data["equipment_attrs_target_ratios"]["main"][attr] = float(
            form.get(f"equip_main_{attr}", 0)
        )
        config_data["gems_attrs_target_ratios"]["main"][attr] = float(
            form.get(f"gem_main_{attr}", 0)
        )

    for comp in COMPANION_CLASSES:
        config_data["equipment_attrs_target_ratios"]["companions"][comp] = {}
        config_data["gems_attrs_target_ratios"]["companions"][comp] = {}
        for attr in ATTRIBUTES:
            config_data["equipment_attrs_target_ratios"]["companions"][comp][attr] = (
                float(form.get(f"equip_{comp}_{attr}", 0))
            )
            config_data["gems_attrs_target_ratios"]["companions"][comp][attr] = float(
                form.get(f"gem_{comp}_{attr}", 0)
            )

    return config_data


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", debug=False, port=5001)
