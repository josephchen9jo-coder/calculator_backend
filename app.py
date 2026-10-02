import json
import os
import sqlite3
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# 数据库文件会生成在 app.py 同目录下，名为 calculator.db
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calculator.db")
PORT = int(os.environ.get("PORT", 5000))


class ExpressionParser:
    """一个不依赖第三方库、安全的四则运算表达式解析器。"""

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
        """把字符串拆成一个一个的 token：数字、运算符、括号。"""
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
        """处理加减法（优先级最低）。"""
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
        """处理乘除法（优先级比加减高）。"""
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
        """处理一元正负号，例如 -5、3*-2。"""
        op = self._peek()[0]
        if op == "+":
            self.index += 1
            return self._parse_factor()
        if op == "-":
            self.index += 1
            return -self._parse_factor()
        return self._parse_primary()

    def _parse_primary(self):
        """处理数字和括号。"""
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
    """把浮点结果整理得好看一点：整数显示为整数，小数去掉浮点误差。"""
    value = round(value, 10)
    if value.is_integer():
        return int(value)
    return value


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS calculation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expression TEXT NOT NULL,
            result REAL NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def insert_history(expression, result):
    conn = _connect()
    conn.execute(
        "INSERT INTO calculation_history (expression, result, created_at) VALUES (?, ?, ?)",
        (expression, result, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


def fetch_history():
    conn = _connect()
    rows = conn.execute(
        "SELECT id, expression, result, created_at FROM calculation_history ORDER BY id DESC"
    ).fetchall()
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
    conn.execute("DELETE FROM calculation_history WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


def clear_history():
    conn = _connect()
    conn.execute("DELETE FROM calculation_history")
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
        # 浏览器跨域预检请求，直接放行
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

        # DELETE /api/history  清空全部（选做的加分功能）
        elif len(parts) == 2 and parts[0] == "api" and parts[1] == "history":
            clear_history()
            self._send_json(200, {"success": True})
        else:
            self._send_json(404, {"success": False, "message": "Not found"})

    def log_message(self, fmt, *args):
        # 关闭默认的请求日志，避免刷屏
        return


def main():
    init_db()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), CalculatorHandler)
    print(f"后端已启动：http://127.0.0.1:{PORT}")
    print("按 Ctrl+C 停止服务")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
