# 计算器后端（Calculator Backend）

这是「前后端分离计算器」的后端服务，负责接收计算请求、解析表达式、计算结果，并把计算历史持久化到数据库。

## 项目介绍

- 前端只负责展示和交互，不参与核心计算。
- 后端通过 HTTP/JSON 接口对外提供能力。
- 计算历史保存在本地 SQLite 数据库 `calculator.db` 中，重启后不会丢失。

## 技术栈

- 语言：Python 3（标准库）
- HTTP 服务：`http.server`
- 数据库：`sqlite3`（SQLite）

## 运行环境

- Python 3.8 或更高版本
- 无需安装任何第三方依赖

## 安装方法

本项目不依赖第三方库，无需安装依赖。直接运行即可。

## 启动方法

在 `calculator_backend` 目录下打开命令行，执行：

```bash
python app.py
```

看到 `后端已启动：http://127.0.0.1:5000` 即启动成功。

## 配置说明

- 默认监听端口：`5000`（可在 `app.py` 顶部修改 `PORT`）。
- 数据库文件：首次启动会自动在同目录生成 `calculator.db`。

## 数据库初始化

数据库由后端在启动时自动创建，无需手动初始化。表结构如下：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | INTEGER | 自增主键 |
| expression | TEXT | 计算表达式 |
| result | REAL | 计算结果 |
| created_at | TEXT | 计算时间 |

## 前后端连接方式

前端通过以下接口访问后端，默认地址为 `http://127.0.0.1:5000`。

### 接口列表

- `POST /api/calculate`：计算表达式
- `GET /api/history`：查询计算历史
- `DELETE /api/history/{id}`：删除指定历史记录
- `DELETE /api/history`：清空全部历史（加分功能）

### 请求 / 响应示例

计算请求：

```json
POST /api/calculate
{ "expression": "(1+2)*3" }
```

成功响应：

```json
{ "success": true, "expression": "(1+2)*3", "result": 9 }
```

错误响应：

```json
{ "success": false, "message": "Invalid expression" }
```
