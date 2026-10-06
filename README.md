# Calculator Backend

This is the back-end service for the front-end and back-end separated calculator. It receives calculation requests, parses expressions, calculates results, and persists calculation history in a database.

## Overview

- The front end only handles display and interaction; it does not do the core calculation.
- The back end provides its capabilities through HTTP/JSON APIs.
- Calculation history is stored in the Neon cloud database (PostgreSQL).

## Technology Stack

- Language: Python 3
- HTTP service: `http.server`
- Database: Neon cloud database (PostgreSQL), accessed with `psycopg2`

## Runtime Environment

- Python 3.8 or higher
- Install dependencies with `pip install -r requirements.txt`

## Installation

```bash
pip install -r requirements.txt
```

## Running

Set the `DATABASE_URL` environment variable to the Neon connection string, then run:

```bash
python app.py
```

## Configuration

- `DATABASE_URL`: the Neon (PostgreSQL) connection string. Required.
- `PORT`: the port the server listens on. Defaults to `5000`.

## Database Initialization

The `calculation_history` table is created automatically when the back end starts. Table structure:

| Field | Type | Description |
| --- | --- | --- |
| id | SERIAL PRIMARY KEY | Auto-increment primary key |
| expression | TEXT | Calculation expression |
| result | DOUBLE PRECISION | Calculation result |
| created_at | TEXT | Calculation time |

## API

The front end accesses the back end through the following APIs.

### Endpoints

- `POST /api/calculate`: calculate an expression
- `GET /api/history`: query history
- `DELETE /api/history/{id}`: delete a specific history record
- `DELETE /api/history`: clear all history (extra feature)

### Request / Response Examples

Calculation request:

```json
POST /api/calculate
{ "expression": "(1+2)*3" }
```

Success response:

```json
{ "success": true, "expression": "(1+2)*3", "result": 9 }
```

Error response:

```json
{ "success": false, "message": "Invalid expression" }
```