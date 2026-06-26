"""Moneta — local finance tracker MVP"""

import csv
import getpass as _getpass
import io
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

from db import (
    ENCRYPTION_AVAILABLE,
    get_db,
    init_db,
    migrate_encrypt_if_needed,
    now_iso,
    set_db_key,
    uid,
    verify_key,
)

# ---------------------------------------------------------------------------
# Encryption setup
#
# Runs once at process start. The key is read from the environment variable
# MONETA_KEY or prompted interactively. It is kept only in RAM (in db.DB_KEY)
# and never written to disk.
# ---------------------------------------------------------------------------

if ENCRYPTION_AVAILABLE:
    _key = os.environ.get("MONETA_KEY", "")
    if not _key:
        try:
            _key = _getpass.getpass("🔐 Datenbankpasswort (Enter = keine Verschlüsselung): ")
        except (EOFError, KeyboardInterrupt):
            print("\nAbgebrochen.", file=sys.stderr)
            sys.exit(0)
    if _key:
        set_db_key(_key)
        if migrate_encrypt_if_needed(_key):
            print("✓ Bestehende Datenbank wurde verschlüsselt.")
        if not verify_key():
            print("❌ Falsches Passwort. Programm wird beendet.", file=sys.stderr)
            sys.exit(1)
    else:
        print("ℹ️  Kein Passwort eingegeben — Datenbank bleibt unverschlüsselt.")
else:
    print("⚠️  sqlcipher3 nicht installiert — Datenbank ist unverschlüsselt.")
    print("   Installation: brew install sqlcipher && pip install sqlcipher3")

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Moneta")
STATIC = Path(__file__).parent / "static"

init_db()


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def row_to_dict(row) -> dict:
    return dict(row) if row else None


def rows_to_list(rows) -> list:
    return [dict(r) for r in rows]


def apply_category_rules(conn, payee: str, purpose: str) -> Optional[str]:
    """Return category_id for best-matching rule, or None."""
    rules = conn.execute(
        "SELECT * FROM category_rules ORDER BY priority DESC"
    ).fetchall()
    text_both = f"{payee} {purpose}".upper()
    for rule in rules:
        pattern = rule["pattern"].upper()
        field = rule["field"]
        if field == "payee" and pattern in payee.upper():
            return rule["category_id"]
        if field == "purpose" and pattern in purpose.upper():
            return rule["category_id"]
        if field == "both" and pattern in text_both:
            return rule["category_id"]
    return None


def get_cycle_start(conn) -> date:
    """Return the start of the current income cycle."""
    rule = conn.execute(
        "SELECT * FROM recurring_rules WHERE type='income' AND active=1 ORDER BY amount DESC LIMIT 1"
    ).fetchone()

    today = date.today()
    if rule:
        day = rule["day_of_month"] or 1
        day = min(day, 28)
        if today.day >= day:
            cycle_start = today.replace(day=day)
        else:
            first_of_month = today.replace(day=1)
            prev_month_last = first_of_month - timedelta(days=1)
            cycle_start = prev_month_last.replace(day=min(day, prev_month_last.day))
        return cycle_start

    row = conn.execute("SELECT value FROM settings WHERE key='cycle_start_day'").fetchone()
    if row:
        day = min(int(row["value"]), 28)
    else:
        day = 1

    if today.day >= day:
        return today.replace(day=day)
    first_of_month = today.replace(day=1)
    prev_month_last = first_of_month - timedelta(days=1)
    return prev_month_last.replace(day=min(day, prev_month_last.day))


def _parse_csv_amount(raw: str, decimal_sep: str = ",") -> float:
    """
    Parse a German or English formatted number string.
    decimal_sep=',' handles German format: 1.234,56 → 1234.56
    decimal_sep='.' handles English format: 1,234.56 → 1234.56
    Also handles trailing minus sign: 45,00- → -45.0
    """
    s = raw.strip().replace("\xa0", "").replace(" ", "")
    trailing_minus = s.endswith("-")
    if trailing_minus:
        s = s[:-1]
    if decimal_sep == ",":
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    return -float(s) if trailing_minus else float(s)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AccountIn(BaseModel):
    name: str
    type: str
    initial_balance: float = 0.0
    currency: str = "EUR"


class TransactionIn(BaseModel):
    account_id: str
    amount: float
    date: str
    payee: str = ""
    purpose: str = ""
    note: str = ""
    category_id: Optional[str] = None
    type: str  # income | expense | transfer
    transfer_to_account_id: Optional[str] = None
    recurring_rule_id: Optional[str] = None


class CategoryIn(BaseModel):
    name: str
    parent_id: Optional[str] = None
    type: str  # income | expense
    icon: str = "📁"


class RecurringRuleIn(BaseModel):
    name: str
    amount: float
    type: str  # income | expense
    category_id: Optional[str] = None
    account_id: str
    payee: str = ""
    purpose: str = ""
    interval_type: str  # monthly | quarterly | biannual | annual
    day_of_month: int = 1
    next_due_date: str
    active: bool = True


class CategoryRuleIn(BaseModel):
    pattern: str
    field: str  # payee | purpose | both
    category_id: str
    priority: int = 0


class BudgetIn(BaseModel):
    category_id: str
    amount: float


class SavingsGoalIn(BaseModel):
    name: str
    target_amount: float
    current_amount: float = 0.0
    monthly_contribution: float = 0.0
    target_date: Optional[str] = None
    color: str = "#6366f1"


class PotIn(BaseModel):
    account_id: str
    name: str
    target_amount: float = 0.0
    color: str = "#6366f1"


class CsvPreviewIn(BaseModel):
    csv_text: str
    delimiter: str = ";"
    has_header: bool = True


class CsvImportIn(BaseModel):
    csv_text: str
    account_id: str
    delimiter: str = ";"
    has_header: bool = True
    col_date: str
    col_amount: str
    col_payee: str = ""
    col_purpose: str = ""
    col_type: str = ""
    date_format: str = "%d.%m.%Y"
    decimal_sep: str = ","
    default_type: str = "auto"  # auto | income | expense
    skip_duplicates: bool = True


class SettingIn(BaseModel):
    value: str


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

@app.get("/api/accounts")
def list_accounts():
    with get_db() as conn:
        accounts = rows_to_list(conn.execute("SELECT * FROM accounts ORDER BY name").fetchall())
        for acc in accounts:
            balance = conn.execute(
                """SELECT COALESCE(SUM(
                    CASE
                        WHEN type='income' THEN amount
                        WHEN type='expense' THEN -amount
                        WHEN type='transfer' AND account_id=? THEN -amount
                        WHEN type='transfer' AND transfer_to_account_id=? THEN amount
                        ELSE 0
                    END
                ), 0) FROM transactions WHERE account_id=? OR transfer_to_account_id=?""",
                (acc["id"], acc["id"], acc["id"], acc["id"]),
            ).fetchone()[0]
            acc["balance"] = round(acc["initial_balance"] + balance, 2)
            # Sum of all pot target_amounts for this account
            reserved = conn.execute(
                "SELECT COALESCE(SUM(target_amount), 0) FROM pots WHERE account_id=?",
                (acc["id"],),
            ).fetchone()[0]
            acc["pots_reserved"] = round(reserved, 2)
            acc["free_balance"] = round(acc["balance"] - reserved, 2)
        return accounts


@app.post("/api/accounts", status_code=201)
def create_account(data: AccountIn):
    with get_db() as conn:
        acc_id = uid()
        conn.execute(
            "INSERT INTO accounts (id, name, type, initial_balance, currency, created_at) VALUES (?,?,?,?,?,?)",
            (acc_id, data.name, data.type, data.initial_balance, data.currency, now_iso()),
        )
        conn.commit()
        return {"id": acc_id}


@app.put("/api/accounts/{acc_id}")
def update_account(acc_id: str, data: AccountIn):
    with get_db() as conn:
        conn.execute(
            "UPDATE accounts SET name=?, type=?, initial_balance=?, currency=? WHERE id=?",
            (data.name, data.type, data.initial_balance, data.currency, acc_id),
        )
        conn.commit()
        return {"ok": True}


@app.delete("/api/accounts/{acc_id}")
def delete_account(acc_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM accounts WHERE id=?", (acc_id,))
        conn.commit()
        return {"ok": True}


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

@app.get("/api/transactions")
def list_transactions(
    account_id: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    category_id: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
):
    with get_db() as conn:
        q = "SELECT t.*, c.name as category_name, c.icon as category_icon, c.parent_id as category_parent_id FROM transactions t LEFT JOIN categories c ON t.category_id=c.id WHERE 1=1"
        params: list = []
        if account_id:
            q += " AND t.account_id=?"
            params.append(account_id)
        if start:
            q += " AND t.date>=?"
            params.append(start)
        if end:
            q += " AND t.date<=?"
            params.append(end)
        if category_id:
            q += " AND t.category_id=?"
            params.append(category_id)
        q += " ORDER BY t.date DESC, t.created_at DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        return rows_to_list(conn.execute(q, params).fetchall())


@app.post("/api/transactions", status_code=201)
def create_transaction(data: TransactionIn):
    with get_db() as conn:
        tx_id = uid()
        category_id = data.category_id
        if not category_id and data.type != "transfer":
            category_id = apply_category_rules(conn, data.payee, data.purpose)
        ts = now_iso()
        conn.execute(
            """INSERT INTO transactions
               (id, account_id, amount, date, payee, purpose, note,
                category_id, type, transfer_to_account_id, recurring_rule_id, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                tx_id, data.account_id, abs(data.amount), data.date,
                data.payee, data.purpose, data.note,
                category_id, data.type,
                data.transfer_to_account_id, data.recurring_rule_id,
                ts, ts,
            ),
        )
        conn.commit()
        return {"id": tx_id, "category_id": category_id}


@app.put("/api/transactions/{tx_id}")
def update_transaction(tx_id: str, data: TransactionIn):
    with get_db() as conn:
        conn.execute(
            """UPDATE transactions SET
               account_id=?, amount=?, date=?, payee=?, purpose=?, note=?,
               category_id=?, type=?, transfer_to_account_id=?, updated_at=?
               WHERE id=?""",
            (
                data.account_id, abs(data.amount), data.date,
                data.payee, data.purpose, data.note,
                data.category_id, data.type,
                data.transfer_to_account_id, now_iso(),
                tx_id,
            ),
        )
        conn.commit()
        return {"ok": True}


@app.delete("/api/transactions/{tx_id}")
def delete_transaction(tx_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM transactions WHERE id=?", (tx_id,))
        conn.commit()
        return {"ok": True}


@app.get("/api/transactions/suggest-category")
def suggest_category(payee: str = "", purpose: str = ""):
    with get_db() as conn:
        cat_id = apply_category_rules(conn, payee, purpose)
        return {"category_id": cat_id}


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

@app.get("/api/categories")
def list_categories():
    with get_db() as conn:
        cats = rows_to_list(conn.execute("SELECT * FROM categories ORDER BY type, parent_id NULLS FIRST, name").fetchall())
        return cats


@app.post("/api/categories", status_code=201)
def create_category(data: CategoryIn):
    with get_db() as conn:
        cat_id = uid()
        conn.execute(
            "INSERT INTO categories (id, name, parent_id, type, icon, created_at) VALUES (?,?,?,?,?,?)",
            (cat_id, data.name, data.parent_id, data.type, data.icon, now_iso()),
        )
        conn.commit()
        return {"id": cat_id}


@app.put("/api/categories/{cat_id}")
def update_category(cat_id: str, data: CategoryIn):
    with get_db() as conn:
        conn.execute(
            "UPDATE categories SET name=?, parent_id=?, type=?, icon=? WHERE id=?",
            (data.name, data.parent_id, data.type, data.icon, cat_id),
        )
        conn.commit()
        return {"ok": True}


@app.delete("/api/categories/{cat_id}")
def delete_category(cat_id: str):
    with get_db() as conn:
        conn.execute("UPDATE categories SET parent_id=NULL WHERE parent_id=?", (cat_id,))
        conn.execute("DELETE FROM categories WHERE id=?", (cat_id,))
        conn.commit()
        return {"ok": True}


# ---------------------------------------------------------------------------
# Recurring rules
# ---------------------------------------------------------------------------

@app.get("/api/recurring")
def list_recurring():
    with get_db() as conn:
        rules = rows_to_list(conn.execute(
            "SELECT r.*, c.name as category_name, c.icon as category_icon FROM recurring_rules r LEFT JOIN categories c ON r.category_id=c.id ORDER BY r.type, r.name"
        ).fetchall())
        return rules


@app.post("/api/recurring", status_code=201)
def create_recurring(data: RecurringRuleIn):
    with get_db() as conn:
        rule_id = uid()
        conn.execute(
            """INSERT INTO recurring_rules
               (id, name, amount, type, category_id, account_id, payee, purpose,
                interval_type, day_of_month, next_due_date, active, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                rule_id, data.name, data.amount, data.type,
                data.category_id, data.account_id,
                data.payee, data.purpose,
                data.interval_type, data.day_of_month,
                data.next_due_date, 1 if data.active else 0,
                now_iso(),
            ),
        )
        conn.commit()
        return {"id": rule_id}


@app.put("/api/recurring/{rule_id}")
def update_recurring(rule_id: str, data: RecurringRuleIn):
    with get_db() as conn:
        conn.execute(
            """UPDATE recurring_rules SET
               name=?, amount=?, type=?, category_id=?, account_id=?,
               payee=?, purpose=?, interval_type=?, day_of_month=?,
               next_due_date=?, active=?
               WHERE id=?""",
            (
                data.name, data.amount, data.type, data.category_id, data.account_id,
                data.payee, data.purpose, data.interval_type, data.day_of_month,
                data.next_due_date, 1 if data.active else 0,
                rule_id,
            ),
        )
        conn.commit()
        return {"ok": True}


@app.delete("/api/recurring/{rule_id}")
def delete_recurring(rule_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM recurring_rules WHERE id=?", (rule_id,))
        conn.commit()
        return {"ok": True}


def _next_due(current: str, interval: str) -> str:
    d = date.fromisoformat(current)
    if interval == "monthly":
        month = d.month + 1
        year = d.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        day = min(d.day, [31,29,31,30,31,30,31,31,30,31,30,31][month-1])
        return date(year, month, day).isoformat()
    if interval == "quarterly":
        return (d + timedelta(days=91)).isoformat()
    if interval == "biannual":
        return (d + timedelta(days=182)).isoformat()
    if interval == "annual":
        return date(d.year + 1, d.month, d.day).isoformat()
    return current


@app.post("/api/recurring/{rule_id}/book")
def book_recurring(rule_id: str):
    """Manually book a recurring transaction now and advance next_due_date."""
    with get_db() as conn:
        rule = row_to_dict(conn.execute("SELECT * FROM recurring_rules WHERE id=?", (rule_id,)).fetchone())
        if not rule:
            raise HTTPException(404)
        today = date.today().isoformat()
        tx_id = uid()
        ts = now_iso()
        conn.execute(
            """INSERT INTO transactions
               (id, account_id, amount, date, payee, purpose, note,
                category_id, type, transfer_to_account_id, recurring_rule_id, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                tx_id, rule["account_id"], rule["amount"], today,
                rule["payee"], rule["purpose"] or rule["name"], "",
                rule["category_id"], rule["type"],
                None, rule_id, ts, ts,
            ),
        )
        next_due = _next_due(rule["next_due_date"], rule["interval_type"])
        conn.execute("UPDATE recurring_rules SET next_due_date=? WHERE id=?", (next_due, rule_id))
        conn.commit()
        return {"transaction_id": tx_id, "next_due_date": next_due}


# ---------------------------------------------------------------------------
# Category rules
# ---------------------------------------------------------------------------

@app.get("/api/rules")
def list_rules():
    with get_db() as conn:
        return rows_to_list(conn.execute(
            "SELECT r.*, c.name as category_name FROM category_rules r LEFT JOIN categories c ON r.category_id=c.id ORDER BY r.priority DESC, r.pattern"
        ).fetchall())


@app.post("/api/rules", status_code=201)
def create_rule(data: CategoryRuleIn):
    with get_db() as conn:
        rule_id = uid()
        conn.execute(
            "INSERT INTO category_rules (id, pattern, field, category_id, priority, created_at) VALUES (?,?,?,?,?,?)",
            (rule_id, data.pattern, data.field, data.category_id, data.priority, now_iso()),
        )
        conn.commit()
        return {"id": rule_id}


@app.put("/api/rules/{rule_id}")
def update_rule(rule_id: str, data: CategoryRuleIn):
    with get_db() as conn:
        conn.execute(
            "UPDATE category_rules SET pattern=?, field=?, category_id=?, priority=? WHERE id=?",
            (data.pattern, data.field, data.category_id, data.priority, rule_id),
        )
        conn.commit()
        return {"ok": True}


@app.delete("/api/rules/{rule_id}")
def delete_rule(rule_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM category_rules WHERE id=?", (rule_id,))
        conn.commit()
        return {"ok": True}


# ---------------------------------------------------------------------------
# Budgets
# ---------------------------------------------------------------------------

@app.get("/api/budgets")
def list_budgets():
    with get_db() as conn:
        return rows_to_list(conn.execute(
            "SELECT b.*, c.name as category_name, c.icon as category_icon FROM budgets b JOIN categories c ON b.category_id=c.id"
        ).fetchall())


@app.post("/api/budgets", status_code=201)
def create_budget(data: BudgetIn):
    with get_db() as conn:
        budget_id = uid()
        conn.execute(
            "INSERT OR REPLACE INTO budgets (id, category_id, amount, created_at) VALUES (?,?,?,?)",
            (budget_id, data.category_id, data.amount, now_iso()),
        )
        conn.commit()
        return {"id": budget_id}


@app.put("/api/budgets/{budget_id}")
def update_budget(budget_id: str, data: BudgetIn):
    with get_db() as conn:
        conn.execute(
            "UPDATE budgets SET category_id=?, amount=? WHERE id=?",
            (data.category_id, data.amount, budget_id),
        )
        conn.commit()
        return {"ok": True}


@app.delete("/api/budgets/{budget_id}")
def delete_budget(budget_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM budgets WHERE id=?", (budget_id,))
        conn.commit()
        return {"ok": True}


# ---------------------------------------------------------------------------
# Savings goals
# ---------------------------------------------------------------------------

@app.get("/api/goals")
def list_goals():
    with get_db() as conn:
        return rows_to_list(conn.execute("SELECT * FROM savings_goals ORDER BY name").fetchall())


@app.post("/api/goals", status_code=201)
def create_goal(data: SavingsGoalIn):
    with get_db() as conn:
        goal_id = uid()
        conn.execute(
            """INSERT INTO savings_goals (id, name, target_amount, current_amount, monthly_contribution, target_date, color, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (goal_id, data.name, data.target_amount, data.current_amount,
             data.monthly_contribution, data.target_date, data.color, now_iso()),
        )
        conn.commit()
        return {"id": goal_id}


@app.put("/api/goals/{goal_id}")
def update_goal(goal_id: str, data: SavingsGoalIn):
    with get_db() as conn:
        conn.execute(
            """UPDATE savings_goals SET name=?, target_amount=?, current_amount=?,
               monthly_contribution=?, target_date=?, color=? WHERE id=?""",
            (data.name, data.target_amount, data.current_amount,
             data.monthly_contribution, data.target_date, data.color, goal_id),
        )
        conn.commit()
        return {"ok": True}


@app.delete("/api/goals/{goal_id}")
def delete_goal(goal_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM savings_goals WHERE id=?", (goal_id,))
        conn.commit()
        return {"ok": True}


# ---------------------------------------------------------------------------
# Pots (FR-T1, FR-T2)
#
# Pots are virtual "envelopes" within an account. They hold a target_amount
# that is considered "reserved". The account's free_balance = balance - sum(pots).
# ---------------------------------------------------------------------------

@app.get("/api/pots")
def list_pots(account_id: Optional[str] = None):
    with get_db() as conn:
        if account_id:
            rows = conn.execute(
                "SELECT p.*, a.name as account_name FROM pots p JOIN accounts a ON p.account_id=a.id WHERE p.account_id=? ORDER BY p.name",
                (account_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT p.*, a.name as account_name FROM pots p JOIN accounts a ON p.account_id=a.id ORDER BY a.name, p.name"
            ).fetchall()
        return rows_to_list(rows)


@app.post("/api/pots", status_code=201)
def create_pot(data: PotIn):
    with get_db() as conn:
        pot_id = uid()
        conn.execute(
            "INSERT INTO pots (id, account_id, name, target_amount, color, created_at) VALUES (?,?,?,?,?,?)",
            (pot_id, data.account_id, data.name, data.target_amount, data.color, now_iso()),
        )
        conn.commit()
        return {"id": pot_id}


@app.put("/api/pots/{pot_id}")
def update_pot(pot_id: str, data: PotIn):
    with get_db() as conn:
        conn.execute(
            "UPDATE pots SET account_id=?, name=?, target_amount=?, color=? WHERE id=?",
            (data.account_id, data.name, data.target_amount, data.color, pot_id),
        )
        conn.commit()
        return {"ok": True}


@app.delete("/api/pots/{pot_id}")
def delete_pot(pot_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM pots WHERE id=?", (pot_id,))
        conn.commit()
        return {"ok": True}


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@app.get("/api/settings/{key}")
def get_setting(key: str):
    with get_db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return {"value": row["value"] if row else None}


@app.put("/api/settings/{key}")
def set_setting(key: str, data: SettingIn):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)",
            (key, data.value),
        )
        conn.commit()
        return {"ok": True}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.get("/api/dashboard")
def dashboard():
    with get_db() as conn:
        cycle_start = get_cycle_start(conn)
        today = date.today()
        cycle_start_str = cycle_start.isoformat()
        today_str = today.isoformat()

        income = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='income' AND date>=? AND date<=?",
            (cycle_start_str, today_str),
        ).fetchone()[0]

        fixed_expenses = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='expense' AND recurring_rule_id IS NOT NULL AND date>=? AND date<=?",
            (cycle_start_str, today_str),
        ).fetchone()[0]

        variable_expenses = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='expense' AND recurring_rule_id IS NULL AND date>=? AND date<=?",
            (cycle_start_str, today_str),
        ).fetchone()[0]

        savings_monthly = conn.execute(
            "SELECT COALESCE(SUM(monthly_contribution), 0) FROM savings_goals"
        ).fetchone()[0]

        budgets = conn.execute("SELECT b.amount, b.category_id FROM budgets b").fetchall()
        eingeplant = 0.0
        for budget in budgets:
            spent = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='expense' AND category_id=? AND date>=? AND date<=?",
                (budget["category_id"], cycle_start_str, today_str),
            ).fetchone()[0]
            remaining = budget["amount"] - spent
            if remaining > 0:
                eingeplant += remaining

        available = round(income - fixed_expenses - variable_expenses - savings_monthly, 2)

        recent = rows_to_list(conn.execute(
            "SELECT t.*, c.name as category_name, c.icon as category_icon FROM transactions t LEFT JOIN categories c ON t.category_id=c.id ORDER BY t.date DESC, t.created_at DESC LIMIT 10"
        ).fetchall())

        accounts = list_accounts()
        total_assets = sum(a["balance"] for a in accounts)

        return {
            "cycle_start": cycle_start_str,
            "today": today_str,
            "income": round(income, 2),
            "fixed_expenses": round(fixed_expenses, 2),
            "variable_expenses": round(variable_expenses, 2),
            "savings_monthly": round(savings_monthly, 2),
            "eingeplant": round(eingeplant, 2),
            "available": available,
            "total_expenses": round(fixed_expenses + variable_expenses, 2),
            "total_assets": round(total_assets, 2),
            "recent_transactions": recent,
            "account_count": len(accounts),
        }


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

@app.get("/api/analysis/by-category")
def analysis_by_category(start: Optional[str] = None, end: Optional[str] = None):
    with get_db() as conn:
        if not start:
            start = date.today().replace(day=1).isoformat()
        if not end:
            end = date.today().isoformat()

        rows = conn.execute(
            """SELECT c.name, c.icon, c.type, cp.name as parent_name,
                      COALESCE(SUM(t.amount), 0) as total,
                      COUNT(t.id) as count
               FROM transactions t
               JOIN categories c ON t.category_id = c.id
               LEFT JOIN categories cp ON c.parent_id = cp.id
               WHERE t.type IN ('income','expense') AND t.date>=? AND t.date<=?
               GROUP BY t.category_id
               ORDER BY total DESC""",
            (start, end),
        ).fetchall()
        return rows_to_list(rows)


@app.get("/api/analysis/cashflow")
def analysis_cashflow(months: int = 6):
    with get_db() as conn:
        results = []
        today = date.today()
        for i in range(months - 1, -1, -1):
            month = today.month - i
            year = today.year
            while month <= 0:
                month += 12
                year -= 1
            start = date(year, month, 1).isoformat()
            if month == 12:
                end = date(year, 12, 31).isoformat()
            else:
                end = (date(year, month + 1, 1) - timedelta(days=1)).isoformat()
            income = conn.execute(
                "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='income' AND date>=? AND date<=?",
                (start, end),
            ).fetchone()[0]
            expense = conn.execute(
                "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='expense' AND date>=? AND date<=?",
                (start, end),
            ).fetchone()[0]
            results.append({
                "month": f"{year}-{month:02d}",
                "label": date(year, month, 1).strftime("%b %Y"),
                "income": round(income, 2),
                "expense": round(expense, 2),
                "net": round(income - expense, 2),
            })
        return results


# ---------------------------------------------------------------------------
# CSV Import (FR-D2)
# ---------------------------------------------------------------------------

@app.post("/api/import/csv/preview")
def preview_csv(data: CsvPreviewIn):
    """Return column headers and first 5 data rows of a CSV for mapping UI."""
    reader = csv.reader(io.StringIO(data.csv_text), delimiter=data.delimiter)
    rows = [row for row in reader if any(c.strip() for c in row)][:7]
    if not rows:
        raise HTTPException(400, "CSV ist leer")
    if data.has_header:
        headers = [h.strip() for h in rows[0]]
        preview = [list(r) for r in rows[1:6]]
    else:
        headers = [str(i) for i in range(len(rows[0]))]
        preview = [list(r) for r in rows[:5]]
    return {"headers": headers, "preview": preview}


@app.post("/api/import/csv")
def import_csv(data: CsvImportIn):
    """
    Import transactions from CSV. Column mapping is provided by the client.

    duplicate detection: (account_id, date, amount, payee) must be unique.
    Returns count of imported, skipped, and up to 10 error messages.
    """
    reader = csv.reader(io.StringIO(data.csv_text), delimiter=data.delimiter)
    all_rows = [row for row in reader if any(c.strip() for c in row)]
    if not all_rows:
        raise HTTPException(400, "CSV ist leer")

    if data.has_header:
        header = [h.strip() for h in all_rows[0]]
        data_rows = all_rows[1:]
    else:
        header = [str(i) for i in range(len(all_rows[0]))]
        data_rows = all_rows

    def col_idx(col_name: str) -> Optional[int]:
        if not col_name:
            return None
        if col_name.isdigit():
            return int(col_name)
        try:
            return header.index(col_name)
        except ValueError:
            raise HTTPException(400, f"Spalte '{col_name}' nicht in CSV-Kopfzeile gefunden. Vorhandene Spalten: {header}")

    idx_date    = col_idx(data.col_date)
    idx_amount  = col_idx(data.col_amount)
    idx_payee   = col_idx(data.col_payee)
    idx_purpose = col_idx(data.col_purpose)
    idx_type    = col_idx(data.col_type)

    if idx_date is None:
        raise HTTPException(400, "col_date ist erforderlich")
    if idx_amount is None:
        raise HTTPException(400, "col_amount ist erforderlich")

    def cell(row: list, idx: Optional[int]) -> str:
        if idx is None or idx >= len(row):
            return ""
        return row[idx].strip()

    imported = 0
    skipped = 0
    errors: list[str] = []

    with get_db() as conn:
        for i, row in enumerate(data_rows):
            try:
                raw_date   = cell(row, idx_date)
                raw_amount = cell(row, idx_amount)
                payee      = cell(row, idx_payee)
                purpose    = cell(row, idx_purpose)

                if not raw_date or not raw_amount:
                    skipped += 1
                    continue

                parsed_date = datetime.strptime(raw_date, data.date_format).date().isoformat()
                amount = _parse_csv_amount(raw_amount, data.decimal_sep)

                # Determine transaction type
                if idx_type is not None:
                    raw_type = cell(row, idx_type).lower()
                    if raw_type in ("einnahme", "income", "gutschrift", "haben", "credit", "+"):
                        tx_type = "income"
                    else:
                        tx_type = "expense"
                    amount = abs(amount)
                elif data.default_type == "auto":
                    tx_type = "income" if amount >= 0 else "expense"
                    amount = abs(amount)
                else:
                    tx_type = data.default_type
                    amount = abs(amount)

                if data.skip_duplicates:
                    exists = conn.execute(
                        "SELECT id FROM transactions WHERE account_id=? AND date=? AND amount=? AND payee=?",
                        (data.account_id, parsed_date, amount, payee),
                    ).fetchone()
                    if exists:
                        skipped += 1
                        continue

                category_id = apply_category_rules(conn, payee, purpose)
                ts = now_iso()
                conn.execute(
                    """INSERT INTO transactions
                       (id, account_id, amount, date, payee, purpose, note,
                        category_id, type, transfer_to_account_id, recurring_rule_id, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (uid(), data.account_id, amount, parsed_date, payee, purpose, "",
                     category_id, tx_type, None, None, ts, ts),
                )
                imported += 1
            except Exception as e:
                errors.append(f"Zeile {i + 2}: {e}")

        conn.commit()

    return {"imported": imported, "skipped": skipped, "errors": errors[:10]}


# ---------------------------------------------------------------------------
# Export / Import
# ---------------------------------------------------------------------------

@app.get("/api/export")
def export_data():
    with get_db() as conn:
        data = {
            "version": 1,
            "exported_at": now_iso(),
            "accounts": rows_to_list(conn.execute("SELECT * FROM accounts").fetchall()),
            "categories": rows_to_list(conn.execute("SELECT * FROM categories").fetchall()),
            "transactions": rows_to_list(conn.execute("SELECT * FROM transactions").fetchall()),
            "recurring_rules": rows_to_list(conn.execute("SELECT * FROM recurring_rules").fetchall()),
            "category_rules": rows_to_list(conn.execute("SELECT * FROM category_rules").fetchall()),
            "budgets": rows_to_list(conn.execute("SELECT * FROM budgets").fetchall()),
            "savings_goals": rows_to_list(conn.execute("SELECT * FROM savings_goals").fetchall()),
            "pots": rows_to_list(conn.execute("SELECT * FROM pots").fetchall()),
            "settings": rows_to_list(conn.execute("SELECT * FROM settings").fetchall()),
        }
        return JSONResponse(content=data, headers={
            "Content-Disposition": f'attachment; filename="moneta-export-{date.today()}.json"'
        })


@app.post("/api/import")
async def import_data(request: Request):
    body = await request.json()
    if body.get("version") != 1:
        raise HTTPException(400, "Unsupported export version")

    tables = ["accounts", "categories", "transactions", "recurring_rules",
              "category_rules", "budgets", "savings_goals", "pots", "settings"]

    with get_db() as conn:
        for t in reversed(tables):
            conn.execute(f"DELETE FROM {t}")

        for table in tables:
            rows = body.get(table, [])
            if not rows:
                continue
            cols = list(rows[0].keys())
            placeholders = ",".join("?" * len(cols))
            col_str = ",".join(cols)
            for row in rows:
                conn.execute(
                    f"INSERT OR REPLACE INTO {table} ({col_str}) VALUES ({placeholders})",
                    list(row.values()),
                )
        conn.commit()

    return {"ok": True, "imported": {t: len(body.get(t, [])) for t in tables}}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import threading
    import webbrowser

    def open_browser():
        import time
        time.sleep(0.8)
        webbrowser.open("http://localhost:8000")

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
