import hashlib
import json
import os
import secrets
import sqlite3
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "world_fitness.db"
INDEX_PATH = BASE_DIR / "index.html"
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
SESSION_COOKIE = "world_fitness_session"
SESSION_DURATION = timedelta(hours=12)
ADMIN_USER = "admin"
ADMIN_PASS_HASH = hashlib.sha256("1234".encode("utf-8")).hexdigest()

DEFAULT_DATA = {
    "academy": {
        "name": "Academia World Fitness BH",
        "rating": "4,6",
        "reviewsCount": 156,
        "address": "R. Jose Alves, 300 - Jardim dos Comerciarios, Vespasiano - MG, 33200-000",
        "phone": "(31) 99326-2334",
        "openStatus": "Aberto • Fecha 23:00",
        "whatsapp": "5531993262334",
        "heroTitle": "A academia certa para seu foco, sua saude e sua evolucao.",
        "heroSubtitle": (
            "Treine em um ambiente acolhedor, com bons profissionais, varios equipamentos "
            "e atendimento que faz diferenca no seu resultado."
        ),
        "about": (
            "A World Fitness BH e uma academia voltada para quem quer treinar com seriedade, "
            "conforto e motivacao. Nosso espaco foi pensado para oferecer uma rotina mais "
            "saudavel, com estrutura funcional, equipamentos e acompanhamento proximo."
        ),
        "ctaText": "Agende sua visita",
    },
    "plans": [
        {
            "id": 1,
            "name": "Mensal",
            "price": "R$ 89,90",
            "desc": "Ideal para comecar seu projeto sem burocracia.",
            "highlight": False,
        },
        {
            "id": 2,
            "name": "Trimestral",
            "price": "R$ 239,90",
            "desc": "Mais economia para manter constancia nos treinos.",
            "highlight": True,
        },
        {
            "id": 3,
            "name": "Anual",
            "price": "R$ 799,90",
            "desc": "Melhor custo-beneficio para transformar seu corpo e rotina.",
            "highlight": False,
        },
    ],
    "features": [
        "Varios equipamentos disponiveis",
        "Instrutores atenciosos",
        "Precos acessiveis",
        "Ambiente saudavel",
        "Otimo atendimento",
        "Espaco acolhedor para treinar",
    ],
    "testimonials": [
        {
            "id": 1,
            "name": "Lucileide Ramos De Santana",
            "text": "Ambiente saudavel! Varios equipamentos disponiveis!",
            "stars": 5,
            "when": "um mes atras",
        },
        {
            "id": 2,
            "name": "Eleo S",
            "text": "Um lugar muito bom para treinar, bons profissionais.",
            "stars": 5,
            "when": "um ano atras",
        },
        {
            "id": 3,
            "name": "Cliente World Fitness",
            "text": "Instrutores atenciosos, precos acessiveis e excelente atendimento.",
            "stars": 5,
            "when": "avaliacao destacada",
        },
    ],
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def clone_default_data():
    return deepcopy(DEFAULT_DATA)


def db_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS site_content (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                academy_json TEXT NOT NULL,
                plans_json TEXT NOT NULL,
                features_json TEXT NOT NULL,
                testimonials_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                goal TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_sessions (
                token TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )

        existing = conn.execute("SELECT id FROM site_content WHERE id = 1").fetchone()
        if not existing:
            seed = clone_default_data()
            conn.execute(
                """
                INSERT INTO site_content (id, academy_json, plans_json, features_json, testimonials_json, updated_at)
                VALUES (1, ?, ?, ?, ?, ?)
                """,
                (
                    json.dumps(seed["academy"], ensure_ascii=False),
                    json.dumps(seed["plans"], ensure_ascii=False),
                    json.dumps(seed["features"], ensure_ascii=False),
                    json.dumps(seed["testimonials"], ensure_ascii=False),
                    utc_now().isoformat(),
                ),
            )


def read_site_data(include_leads: bool = True):
    with db_connection() as conn:
        row = conn.execute(
            """
            SELECT academy_json, plans_json, features_json, testimonials_json
            FROM site_content
            WHERE id = 1
            """
        ).fetchone()

        data = {
            "academy": json.loads(row["academy_json"]),
            "plans": json.loads(row["plans_json"]),
            "features": json.loads(row["features_json"]),
            "testimonials": json.loads(row["testimonials_json"]),
            "leads": [],
        }

        if include_leads:
            leads = conn.execute(
                """
                SELECT id, name, phone, goal, created_at
                FROM leads
                ORDER BY id DESC
                """
            ).fetchall()
            data["leads"] = [
                {
                    "id": lead["id"],
                    "name": lead["name"],
                    "phone": lead["phone"],
                    "goal": lead["goal"],
                    "createdAt": lead["created_at"],
                }
                for lead in leads
            ]

        return data


def write_site_content(content):
    with db_connection() as conn:
        conn.execute(
            """
            UPDATE site_content
            SET academy_json = ?, plans_json = ?, features_json = ?, testimonials_json = ?, updated_at = ?
            WHERE id = 1
            """,
            (
                json.dumps(content["academy"], ensure_ascii=False),
                json.dumps(content["plans"], ensure_ascii=False),
                json.dumps(content["features"], ensure_ascii=False),
                json.dumps(content["testimonials"], ensure_ascii=False),
                utc_now().isoformat(),
            ),
        )


def add_lead(name: str, phone: str, goal: str):
    created_at = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
    with db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO leads (name, phone, goal, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (name, phone, goal, created_at),
        )
        return {
            "id": cursor.lastrowid,
            "name": name,
            "phone": phone,
            "goal": goal,
            "createdAt": created_at,
        }


def reset_site_data():
    defaults = clone_default_data()
    with db_connection() as conn:
        conn.execute("DELETE FROM leads")
        conn.execute(
            """
            UPDATE site_content
            SET academy_json = ?, plans_json = ?, features_json = ?, testimonials_json = ?, updated_at = ?
            WHERE id = 1
            """,
            (
                json.dumps(defaults["academy"], ensure_ascii=False),
                json.dumps(defaults["plans"], ensure_ascii=False),
                json.dumps(defaults["features"], ensure_ascii=False),
                json.dumps(defaults["testimonials"], ensure_ascii=False),
                utc_now().isoformat(),
            ),
        )


def create_session():
    token = secrets.token_urlsafe(32)
    now = utc_now()
    expires_at = now + SESSION_DURATION
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO admin_sessions (token, created_at, expires_at)
            VALUES (?, ?, ?)
            """,
            (token, now.isoformat(), expires_at.isoformat()),
        )
    return token, expires_at


def cleanup_sessions(conn):
    conn.execute(
        "DELETE FROM admin_sessions WHERE expires_at <= ?",
        (utc_now().isoformat(),),
    )


def session_is_valid(token: str | None):
    if not token:
        return False
    with db_connection() as conn:
        cleanup_sessions(conn)
        row = conn.execute(
            "SELECT token FROM admin_sessions WHERE token = ?",
            (token,),
        ).fetchone()
        return row is not None


def delete_session(token: str | None):
    if not token:
        return
    with db_connection() as conn:
        conn.execute("DELETE FROM admin_sessions WHERE token = ?", (token,))


class AppHandler(BaseHTTPRequestHandler):
    server_version = "WorldFitnessServer/1.0"

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in {"/", "/index.html", "/admin"}:
            return self.serve_index()
        if parsed.path == "/api/public-data":
            return self.send_json(HTTPStatus.OK, read_site_data(include_leads=False))
        if parsed.path == "/api/admin/session":
            return self.send_json(HTTPStatus.OK, {"logged": self.is_authenticated()})
        if parsed.path == "/api/admin/data":
            if not self.require_auth():
                return
            return self.send_json(HTTPStatus.OK, read_site_data(include_leads=True))
        if parsed.path == "/api/admin/export":
            if not self.require_auth():
                return
            return self.send_download(read_site_data(include_leads=True))

        return self.send_error_json(HTTPStatus.NOT_FOUND, "Rota nao encontrada.")

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/leads":
            return self.handle_create_lead()
        if parsed.path == "/api/admin/login":
            return self.handle_login()
        if parsed.path == "/api/admin/logout":
            return self.handle_logout()
        if parsed.path == "/api/admin/save":
            if not self.require_auth():
                return
            return self.handle_save()
        if parsed.path == "/api/admin/reset":
            if not self.require_auth():
                return
            return self.handle_reset()

        return self.send_error_json(HTTPStatus.NOT_FOUND, "Rota nao encontrada.")

    def serve_index(self):
        content = INDEX_PATH.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def handle_create_lead(self):
        payload = self.read_json_body()
        if payload is None:
            return

        name = str(payload.get("name", "")).strip()
        phone = str(payload.get("phone", "")).strip()
        goal = str(payload.get("goal", "")).strip()

        if not name or not phone:
            return self.send_error_json(
                HTTPStatus.BAD_REQUEST,
                "Preencha pelo menos nome e WhatsApp para enviar seu contato.",
            )

        lead = add_lead(name=name, phone=phone, goal=goal)
        return self.send_json(HTTPStatus.CREATED, {"lead": lead})

    def handle_login(self):
        payload = self.read_json_body()
        if payload is None:
            return

        user = str(payload.get("user", "")).strip()
        password = str(payload.get("pass", "")).strip()
        password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()

        if user != ADMIN_USER or password_hash != ADMIN_PASS_HASH:
            return self.send_error_json(
                HTTPStatus.UNAUTHORIZED,
                "Login invalido. Verifique usuario e senha.",
            )

        token, expires_at = create_session()
        self.send_response(HTTPStatus.OK)
        self.send_cookie(token, expires_at)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        body = json.dumps({"logged": True}).encode("utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_logout(self):
        token = self.get_session_token()
        delete_session(token)
        self.send_response(HTTPStatus.OK)
        self.clear_cookie()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        body = json.dumps({"logged": False}).encode("utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_save(self):
        payload = self.read_json_body()
        if payload is None:
            return

        academy = payload.get("academy")
        plans = payload.get("plans")
        features = payload.get("features")
        testimonials = payload.get("testimonials")

        if not isinstance(academy, dict):
            return self.send_error_json(HTTPStatus.BAD_REQUEST, "Academy invalido.")
        if not isinstance(plans, list):
            return self.send_error_json(HTTPStatus.BAD_REQUEST, "Plans invalido.")
        if not isinstance(features, list):
            return self.send_error_json(HTTPStatus.BAD_REQUEST, "Features invalido.")
        if not isinstance(testimonials, list):
            return self.send_error_json(HTTPStatus.BAD_REQUEST, "Testimonials invalido.")

        content = normalize_content(
            {
                "academy": academy,
                "plans": plans,
                "features": features,
                "testimonials": testimonials,
            }
        )
        write_site_content(content)
        return self.send_json(HTTPStatus.OK, read_site_data(include_leads=True))

    def handle_reset(self):
        reset_site_data()
        return self.send_json(HTTPStatus.OK, read_site_data(include_leads=True))

    def read_json_body(self):
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "JSON invalido.")
            return None

    def get_session_token(self):
        cookie_header = self.headers.get("Cookie")
        if not cookie_header:
            return None
        cookie = SimpleCookie()
        cookie.load(cookie_header)
        morsel = cookie.get(SESSION_COOKIE)
        return morsel.value if morsel else None

    def is_authenticated(self):
        return session_is_valid(self.get_session_token())

    def require_auth(self):
        if self.is_authenticated():
            return True
        self.send_error_json(HTTPStatus.UNAUTHORIZED, "Sessao expirada ou nao autenticada.")
        return False

    def send_cookie(self, token: str, expires_at: datetime):
        expires_http = expires_at.astimezone(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        cookie = (
            f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; "
            f"Expires={expires_http}"
        )
        self.send_header("Set-Cookie", cookie)

    def clear_cookie(self):
        self.send_header(
            "Set-Cookie",
            f"{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0",
        )

    def send_json(self, status: HTTPStatus, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: HTTPStatus, message: str):
        self.send_json(status, {"error": message})

    def send_download(self, payload):
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="world-fitness-bh-data.json"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def normalize_content(content):
    defaults = clone_default_data()
    academy_defaults = defaults["academy"]
    academy = {}

    for key, default_value in academy_defaults.items():
        value = content["academy"].get(key, default_value)
        if key == "reviewsCount":
            academy[key] = max(0, int(value or 0))
        else:
            academy[key] = str(value).strip() or default_value

    plans = []
    for index, plan in enumerate(content["plans"], start=1):
        name = str(plan.get("name", "")).strip()
        price = str(plan.get("price", "")).strip()
        if not name or not price:
            continue
        plans.append(
            {
                "id": int(plan.get("id") or int(datetime.now().timestamp() * 1000) + index),
                "name": name,
                "price": price,
                "desc": str(plan.get("desc", "")).strip(),
                "highlight": bool(plan.get("highlight")),
            }
        )

    features = [
        str(item).strip()
        for item in content["features"]
        if str(item).strip()
    ]

    testimonials = []
    for index, item in enumerate(content["testimonials"], start=1):
        name = str(item.get("name", "")).strip()
        text = str(item.get("text", "")).strip()
        if not name or not text:
            continue
        testimonials.append(
            {
                "id": int(item.get("id") or int(datetime.now().timestamp() * 1000) + index),
                "name": name,
                "text": text,
                "stars": max(1, min(5, int(item.get("stars") or 5))),
                "when": str(item.get("when", "agora")).strip() or "agora",
            }
        )

    if not plans:
        plans = defaults["plans"]
    if not features:
        features = defaults["features"]
    if not testimonials:
        testimonials = defaults["testimonials"]

    return {
        "academy": academy,
        "plans": plans,
        "features": features,
        "testimonials": testimonials,
    }


def run():
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"Servidor pronto em http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    run()
