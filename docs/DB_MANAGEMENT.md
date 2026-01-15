# Database Management & Security Guide

## Overview

Lumina V2 uses **SurrealDB** as its core memory store.
To improve security, we have implemented a **Role-Based Access Control (RBAC)** system.

### Credentials Architecture

| Role              | Username (Default) | Password (Default)   | Permissions                                     |
| :---------------- | :----------------- | :------------------- | :---------------------------------------------- |
| **Root (Admin)**  | `root`             | `root`               | Full Access, Schema Definition, User Management |
| **App (Service)** | `lumina_app`       | `lumina_secure_pass` | Read/Write Data (DML), No Schema Changes (DDL)  |

> **⚠️ SECURITY WARNING**: In production, you MUST change these passwords via `memory_config.json` or Environment Variables.

### Environment Variables

You can override credentials without touching files (Recommended for Docker/Prod):

- `SURREAL_ROOT_USER` / `SURREAL_ROOT_PASS`
- `SURREAL_APP_USER` / `SURREAL_APP_PASS`
- `SURREAL_URL` (Default: `ws://127.0.0.1:8001/rpc`)

---

## How to Debug Data (Surrealist)

We have removed the dangerous `/debug/*` API endpoints.
To inspect or modify data manually, please use **Surrealist**, the official GUI for SurrealDB.

### 1. Download Surrealist

Download the desktop app from: [https://surrealdb.com/surrealist](https://surrealdb.com/surrealist)
Or use the web version: [https://surrealist.app/](https://surrealist.app/) (Requires allowing connection to localhost)

### 2. Connect to Local DB

1.  **Name**: Lumina Local
2.  **Endpoint**: `ws://127.0.0.1:8001/rpc`
3.  **Namespace**: `lumina`
4.  **Database**: `memory`
5.  **Auth Mode**: Root
6.  **Username**: `root`
7.  **Password**: `root` (or your configured password)

### 3. Verify RBAC

Try connecting with the App User to verify restrictions:

- **Username**: `lumina_app`
- **Password**: `lumina_secure_pass`

You should be able to `SELECT * FROM episodic_memory`, but `REMOVE TABLE episodic_memory` should fail.

---

## Troubleshooting

**Q: "Surreal Connection Failed" on startup?**
A: Ensure your SurrealDB server is running on port 8001.
If you changed the root password in the DB but not in `memory_config.json`, the app cannot initialize the schema.

**Q: I see "Auth Error" in logs?**
A: Check if `memory_config.json` contains old keys (`user`/`password`). Please update them to `root_user`/`root_password` and `app_user`/`app_password`.
