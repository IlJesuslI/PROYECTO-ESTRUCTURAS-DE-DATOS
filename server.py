"""Servidor HTTP de FoodQueue basado solo en la biblioteca estándar de Python.

Uso:
    python server.py
Luego abrir: http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.service import ConflictError, FoodQueueService, NotFoundError, ValidationError

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
DATA_FILE = ROOT / "data" / "state.json"
MAX_BODY_BYTES = 1_000_000
SERVICE = FoodQueueService(DATA_FILE)


class FoodQueueHandler(BaseHTTPRequestHandler):
    server_version = "FoodQueue/1.0"

    def log_message(self, fmt: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {self.address_string()} - {fmt % args}")

    # ---------- Respuestas ----------
    def _json(self, status: int, payload: dict | list) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, message: str) -> None:
        self._json(status, {"ok": False, "error": message})

    def _read_json(self) -> dict:
        content_type = self.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            raise ValidationError("Content-Type debe ser application/json.")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValidationError("Content-Length inválido.") from exc
        if length <= 0:
            raise ValidationError("El cuerpo de la solicitud está vacío.")
        if length > MAX_BODY_BYTES:
            raise ValidationError("La solicitud supera el límite de 1 MB.")
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValidationError("JSON inválido o codificación distinta de UTF-8.") from exc
        if not isinstance(data, dict):
            raise ValidationError("El JSON principal debe ser un objeto.")
        return data

    def _serve_static(self, requested_path: str) -> None:
        relative = "index.html" if requested_path == "/" else requested_path.lstrip("/")
        candidate = (STATIC_DIR / relative).resolve()
        if STATIC_DIR.resolve() not in candidate.parents and candidate != STATIC_DIR.resolve():
            self._error(HTTPStatus.FORBIDDEN, "Ruta no permitida.")
            return
        if not candidate.is_file():
            self._error(HTTPStatus.NOT_FOUND, "Recurso no encontrado.")
            return
        body = candidate.read_bytes()
        mime, _ = mimetypes.guess_type(candidate.name)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{mime or 'application/octet-stream'}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---------- API ----------
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        try:
            if path == "/api/status":
                self._json(HTTPStatus.OK, {"ok": True, "data": SERVICE.status()})
            elif path == "/api/products":
                query = parse_qs(parsed.query)
                include_inactive = query.get("all", ["0"])[0] == "1"
                self._json(
                    HTTPStatus.OK,
                    {"ok": True, "data": SERVICE.list_products(include_inactive)},
                )
            elif path == "/api/orders/pending":
                self._json(HTTPStatus.OK, {"ok": True, "data": SERVICE.list_pending_orders()})
            elif path == "/api/history":
                query = parse_qs(parsed.query)
                limit = int(query.get("limit", ["50"])[0])
                self._json(HTTPStatus.OK, {"ok": True, "data": SERVICE.list_history(limit)})
            elif path.startswith("/api/"):
                self._error(HTTPStatus.NOT_FOUND, "Endpoint no encontrado.")
            else:
                self._serve_static(parsed.path)
        except ValueError:
            self._error(HTTPStatus.BAD_REQUEST, "Parámetro numérico inválido.")
        except Exception as exc:  # protección de borde del servidor
            print(f"Error interno: {exc!r}")
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Error interno del servidor.")

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/")
        try:
            if path == "/api/products":
                result = SERVICE.add_product(self._read_json())
                self._json(HTTPStatus.CREATED, {"ok": True, "data": result})
            elif path == "/api/orders":
                result = SERVICE.create_order(self._read_json())
                self._json(HTTPStatus.CREATED, {"ok": True, "data": result})
            elif path == "/api/orders/process-next":
                result = SERVICE.process_next_order()
                self._json(HTTPStatus.OK, {"ok": True, "data": result})
            elif path == "/api/history/undo":
                result = SERVICE.undo_last_prepared()
                self._json(HTTPStatus.OK, {"ok": True, "data": result})
            elif match := re.fullmatch(r"/api/orders/([0-9a-f-]+)/cancel", path):
                result = SERVICE.cancel_order(match.group(1))
                self._json(HTTPStatus.OK, {"ok": True, "data": result})
            else:
                self._error(HTTPStatus.NOT_FOUND, "Endpoint no encontrado.")
        except ValidationError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
        except NotFoundError as exc:
            self._error(HTTPStatus.NOT_FOUND, str(exc))
        except ConflictError as exc:
            self._error(HTTPStatus.CONFLICT, str(exc))
        except Exception as exc:
            print(f"Error interno: {exc!r}")
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Error interno del servidor.")

    def do_PUT(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/")
        try:
            match = re.fullmatch(r"/api/products/([0-9a-f-]+)", path)
            if not match:
                self._error(HTTPStatus.NOT_FOUND, "Endpoint no encontrado.")
                return
            result = SERVICE.update_product(match.group(1), self._read_json())
            self._json(HTTPStatus.OK, {"ok": True, "data": result})
        except ValidationError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
        except NotFoundError as exc:
            self._error(HTTPStatus.NOT_FOUND, str(exc))
        except ConflictError as exc:
            self._error(HTTPStatus.CONFLICT, str(exc))
        except Exception as exc:
            print(f"Error interno: {exc!r}")
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Error interno del servidor.")

    def do_DELETE(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/")
        try:
            match = re.fullmatch(r"/api/products/([0-9a-f-]+)", path)
            if not match:
                self._error(HTTPStatus.NOT_FOUND, "Endpoint no encontrado.")
                return
            result = SERVICE.deactivate_product(match.group(1))
            self._json(HTTPStatus.OK, {"ok": True, "data": result})
        except NotFoundError as exc:
            self._error(HTTPStatus.NOT_FOUND, str(exc))
        except Exception as exc:
            print(f"Error interno: {exc!r}")
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Error interno del servidor.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor local de FoodQueue")
    parser.add_argument("--host", default="127.0.0.1", help="Host (por defecto 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Puerto (por defecto 8000)")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), FoodQueueHandler)
    print(f"FoodQueue disponible en http://{args.host}:{args.port}")
    print("Presione Ctrl+C para detener el servidor.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
