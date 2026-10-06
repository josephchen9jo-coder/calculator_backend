import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras

PORT = int(os.environ.get("PORT", 5000))
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if not DATABASE_URL:
    raise RuntimeError("Missing DATABASE_URL environment variable")


class ExpressionParser:
    """A safe, dependency-free arithmetic expression parser."""

    def __init__(self):
        self.tokens = []
        self.index = 0

    def parse(self, expression):
        self.tokens = self._tokenize(expression)
        self.index = 0
        if not self.tokens:
            raise ValueError("Expression is empty")
        value = self._parse_expression()
        if self.index != len(self.tokens):
            raise ValueError("Invalid expression")
        return _format_number(value)

    def _tokenize(self, expression):
        """Split the string into tokens: numbers, operators, parentheses."""
        tokens = []
        i = 0
        length = len(expression)
        while i < length:
            ch = expression[i]
            if ch.isspace():
                i += 1
            elif ch.isdigit() or ch == ".":
                start = i
                dot_count = 0
                while i < length and (expression[i].isdigit() or expression[i] == "."):
                    if expression[i] == ".":
                        dot_count += 1
                    i += 1
                if dot_count > 1:
                    raise ValueError("Invalid number")
                tokens.append(("NUMBER", expression[start:i]))
            elif ch in "+-*/()":
                tokens.append((ch, ch))
                i += 1
            else:
                raise ValueError("Invalid character")
        return tokens

    def _peek(self):
        if self.index < len(self.tokens):
            return self.tokens[self.index]
        return (None, None)

    def _parse_expression(self):
        """Handle addition and subtraction (lowest precedence)."""
        value = self._parse_term()
        while self._peek()[0] in ("+", "-"):
            op = self._peek()[0]
            self.index += 1
            if op == "+":
                value += self._parse_term()
            else:
                value -= self._parse_term()
        return value

    def _parse_term(self):
        """Handle multiplication and division (higher precedence than add/sub)."""
        value = self._parse_factor()
        while self._peek()[0] in ("*", "/"):
            op = self._peek()[0]
            self.index += 1
            right = self._parse_factor()
            if op == "*":
                value *= right
            else:
                if right == 0:
                    raise ZeroDivisionError("Division by zero")
                value /= right
        return value

    def _parse_factor(self):
        """Handle unary plus/minus, e.g. -5, 3*-2."""
        op = self._peek()[0]
        if op == "+":
            self.index += 1
            return self._parse_factor()
        if op == "-":
            self.index += 1
            return -self._parse_factor()
        return self._parse_primary()

    def _parse_primary(self):
        """Handle numbers and parentheses."""
        token_type, token_value = self._peek()
        if token_type == "NUMBER":
            self.index += 1
            return float(token_value)
        if token_type == "(":
            self.index += 1
            value = self._parse_expression()
            if self._peek()[0] != ")":
                raise ValueError("Missing closing parenthesis")
            self.index += 1
            return value
        raise ValueError("Invalid expression")


def _format_number(value):
    """Format the float result nicely: integers stay integers, decimals drop floating-point noise."""
    value = round(value, 10)
    if value.is_integer():
        return int(value)
    return value


def _connect():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def init_db():
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS calculation_history (
            id SERIAL PRIMARY KEY,
            expression TEXT NOT NULL,
            result DOUBLE PRECISION NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def insert_history(expression, result):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO calculation_history (expression, result, created_at) VALUES (%s, %s, %s)",
        (expression, result, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


def fetch_history():
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, expression, result, created_at FROM calculation_history ORDER BY id DESC"
    )
    rows = cur.fetchall()
    conn.close()
    history = []
    for row in rows:
        history.append(
            {
                "id": row["id"],
                "expression": row["expression"],
                "result": _format_number(row["result"]),
                "created_at": row["created_at"],
            }
        )
    return history


def delete_history(record_id):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM calculation_history WHERE id = %s", (record_id,))
    conn.commit()
    conn.close()


def clear_history():
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM calculation_history")
    conn.commit()
    conn.close()


class CalculatorHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        # Allow the browser's CORS preflight request
        self._send_json(204, {})

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/history":
            self._send_json(200, {"success": True, "history": fetch_history()})
        else:
            self._send_json(404, {"success": False, "message": "Not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/calculate":
            self._send_json(404, {"success": False, "message": "Not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8")
            data = json.loads(raw) if raw else {}
        except ValueError:
            self._send_json(400, {"success": False, "message": "Invalid request"})
            return

        expression = str(data.get("expression", "")).strip()
        if not expression:
            self._send_json(400, {"success": False, "message": "Expression is empty"})
            return

        try:
            result = ExpressionParser().parse(expression)
        except ZeroDivisionError:
            self._send_json(400, {"success": False, "message": "Division by zero"})
            return
        except ValueError:
            self._send_json(400, {"success": False, "message": "Invalid expression"})
            return

        insert_history(expression, result)
        self._send_json(200, {"success": True, "expression": expression, "result": result})

    def do_DELETE(self):
        parts = [p for p in urlparse(self.path).path.split("/") if p]

        # DELETE /api/history/{id}
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "history":
            try:
                record_id = int(parts[2])
            except ValueError:
                self._send_json(400, {"success": False, "message": "Invalid id"})
                return
            delete_history(record_id)
            self._send_json(200, {"success": True})

        # DELETE /api/history  Clear all history (extra feature)
        elif len(parts) == 2 and parts[0] == "api" and parts[1] == "history":
            clear_history()
            self._send_json(200, {"success": True})
        else:
            self._send_json(404, {"success": False, "message": "Not found"})

    def log_message(self, fmt, *args):
        # Suppress the default request log to avoid noise
        return


def main():
    init_db()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), CalculatorHandler)
    print(f"Backend started: http://127.0.0.1:{PORT}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()