# 代码规范（Code Style）

## 规范来源

本项目的 Python 代码遵循官方规范 **PEP 8 —— Style Guide for Python Code**。

- 参考地址：https://peps.python.org/pep-0008/

## 本项目约定

- 使用 4 个空格缩进，不使用 Tab。
- 函数名、变量名使用小写字母加下划线（snake_case），例如 `fetch_history`。
- 类名使用大驼峰命名（CapWords），例如 `ExpressionParser`。
- 每个函数尽量只做一件事，保持职责清晰。
- 使用有意义的变量名，避免使用 `a`、`b`、`x` 等无意义命名。
- 在关键逻辑处添加简短的中文注释，帮助阅读。
