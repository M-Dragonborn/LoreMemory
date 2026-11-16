# LoreMemory: Future To-Do List

This document tracks upcoming features and architectural extensions that are planned for future development.

---

## 1. Multi-Tier Role Hierarchy (Super Admin, Admin, Standard User)

### Status: Planned / On Hold (Not active focus)

### Goal:
Introduce role-based access control (RBAC) into `data/users.db`:
- **`super_admin`**: Root administrator. Controls admin accounts (creates, promotes, demotes, deletes admins) and system-wide settings.
- **`admin`**: Department/Team administrator. Controls standard user accounts (creates users, deactivates accounts, resets passwords, views user activity logs).
- **`user`**: Standard database user. Can use the manual DBMS and view shared query histories, but cannot access user management.

---

### Database Schema Design (`data/users.db`)

#### Primary Approach: Unified Users Table with Role Hierarchy & Lineage
This approach maintains clean foreign keys with `data/history.db` (`query_history.user_id`) without requiring polymorphic cross-table joins.

```sql
PRAGMA foreign_keys = ON;

-- 1. Unified accounts table with role hierarchy
CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user' 
                  CHECK (role IN ('user', 'admin', 'super_admin')),
    is_active     INTEGER NOT NULL DEFAULT 1 
                  CHECK (is_active IN (0, 1)),
    created_by    INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login    TEXT
);

-- Index for fast role-based lookups and lineage queries
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);
CREATE INDEX IF NOT EXISTS idx_users_created_by ON users (created_by);

-- 2. Audit table tracking role changes, promotions, and demotions
CREATE TABLE IF NOT EXISTS role_audit_log (
    audit_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    target_user  INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    changed_by   INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    old_role     TEXT NOT NULL,
    new_role     TEXT NOT NULL,
    changed_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reason       TEXT
);
```

#### Alternative Approach: Dedicated Tables per Role
If strict physical table separation is desired:
```sql
PRAGMA foreign_keys = ON;

-- Super Admins (Root)
CREATE TABLE IF NOT EXISTS super_admins (
    super_admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username       TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    salt           TEXT NOT NULL,
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login     TEXT
);

-- Admins (Managed by Super Admins)
CREATE TABLE IF NOT EXISTS admins (
    admin_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username       TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    salt           TEXT NOT NULL,
    is_active      INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_by     INTEGER NOT NULL REFERENCES super_admins(super_admin_id) ON DELETE RESTRICT,
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login     TEXT
);

-- Standard Users (Managed by Admins)
CREATE TABLE IF NOT EXISTS users (
    user_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username       TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    salt           TEXT NOT NULL,
    is_active      INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_by     INTEGER NOT NULL REFERENCES admins(admin_id) ON DELETE RESTRICT,
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login     TEXT
);
```

---

### How this Connects to `data/history.db`
In `data/history.db`, each query record stores `user_id`. When using the **Primary Approach**:
- `ATTACH DATABASE 'data/users.db' AS u;` connects seamlessly.
- Query history joins `u.users` on `user_id` to display both `username` and `role`.
- Admins can query `WHERE u.role = 'user' AND q.user_id = ?` to inspect any user's past actions.
- Super admins can inspect admin-level actions.

---

### Implementation Steps (When Ready):
1. **Schema Migration:** Update `auth.py` to support `role`, `is_active`, and `created_by`.
2. **First-Time Setup (Bootstrap):** Automatically create the initial `super_admin` account on first startup (or prompt for setup).
3. **Permission Rules:**
   - Standard registration sets `role = 'user'`.
   - Only `admin` or `super_admin` can create new users directly.
   - Only `super_admin` can create or promote accounts to `admin`.
4. **GUI Integration:**
   - Add an **"Account Management"** section in the GUI visible only when logged in as an `admin` or `super_admin`.
   - Admins see user list + audit logs.
   - Super admins see admin list + user list + role assignment dropdown.
