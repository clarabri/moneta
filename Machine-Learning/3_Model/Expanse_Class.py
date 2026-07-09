# ----------------------------------------------------------
# Expense database
# ----------------------------------------------------------

import sqlite3
from pathlib import Path


class ExpenseDatabase:
    """
    Handles all persistent data used by the expense classifier.

    Stores:
        - available categories
        - rule keywords
        - learned merchant classifications

    This replaces:
        - CATEGORIES
        - RULES
        - init_database()
        - lookup_memory()
        - save_memory()
        - correct_category()
        - apply_rules()
    """

    def __init__(self, db_path="expense_memory.sqlite"):

        self.conn = sqlite3.connect(db_path)
        self.create_tables()


    # ------------------------------------------------------
    # Database setup
    # ------------------------------------------------------

    def create_tables(self):

        self.conn.executescript("""

        CREATE TABLE IF NOT EXISTS categories(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT UNIQUE NOT NULL,

            description TEXT
        );

        CREATE TABLE IF NOT EXISTS keywords(

            keyword TEXT PRIMARY KEY,

            category TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS merchant_memory(

            merchant TEXT PRIMARY KEY,

            category TEXT NOT NULL,

            confidence REAL DEFAULT 1.0
        );

        """)

        self.conn.commit()


    # ------------------------------------------------------
    # Categories
    # ------------------------------------------------------

    def add_category(self,
                     name,
                     description=""):

        self.conn.execute(
            """
            INSERT OR IGNORE INTO categories
            VALUES(NULL, ?, ?)
            """,
            (
                name,
                description
            )
        )

        self.conn.commit()


    def get_categories(self):

        rows = self.conn.execute(
            """
            SELECT
                name,
                description

            FROM categories

            ORDER BY id
            """
        ).fetchall()

        return rows


    def category_exists(self,
                        category):

        row = self.conn.execute(
            """
            SELECT 1

            FROM categories

            WHERE name=?
            """,
            (category,)
        ).fetchone()

        return row is not None


    # ------------------------------------------------------
    # Keywords (Rule Engine)
    # ------------------------------------------------------

    def add_keyword(self,
                    category,
                    keyword):

        if not self.category_exists(category):
            raise ValueError(
                f"Unknown category '{category}'"
            )

        self.conn.execute(
            """
            INSERT OR REPLACE INTO keywords

            VALUES (?, ?)
            """,
            (
                keyword.lower(),
                category
            )
        )

        self.conn.commit()


    def apply_rules(self,
                    description):

        if description is None:
            return None

        text = description.lower()

        rows = self.conn.execute(
            """
            SELECT
                keyword,
                category

            FROM keywords
            """
        ).fetchall()

        for keyword, category in rows:

            if keyword in text:

                return {

                    "category": category,

                    "confidence": 0.95,

                    "source": "rules"

                }

        return None


    # ------------------------------------------------------
    # Merchant Memory
    # ------------------------------------------------------

    def lookup_memory(self,
                      merchant):

        merchant = merchant.upper()

        rows = self.conn.execute(
            """
            SELECT
                merchant,
                category,
                confidence

            FROM merchant_memory
            """
        ).fetchall()

        for known, category, confidence in rows:

            if known in merchant:

                return {

                    "category": category,

                    "confidence": confidence,

                    "source": "memory"

                }

        return None


    def save_memory(self,
                    merchant,
                    category,
                    confidence):

        self.conn.execute(
            """
            INSERT OR REPLACE INTO merchant_memory

            VALUES (?, ?, ?)
            """,
            (
                merchant.upper(),
                category,
                confidence
            )
        )

        self.conn.commit()


    def correct_merchant(self,
                         merchant,
                         category):

        if not self.category_exists(category):

            raise ValueError(
                f"Unknown category '{category}'"
            )

        self.save_memory(
            merchant,
            category,
            1.0
        )


    # ------------------------------------------------------
    # Prompt generation
    # ------------------------------------------------------

    def build_prompt(self):
        """
        Returns the category section for the LLM prompt.
        """

        rows = self.get_categories()

        prompt = ""

        for category, description in rows:

            prompt += f'- "{category}"\n'

            if description:

                prompt += f"  {description}\n"

            prompt += "\n"

        return prompt
    
    # ------------------------------------------------------
    # Debugging
    # ------------------------------------------------------

    def show_categories(self):
        rows = self.conn.execute(
            """
            SELECT name, description
            FROM categories
            """
        ).fetchall()

        for row in rows:
            print(row)


    def show_keywords(self):
        rows = self.conn.execute(
            """
            SELECT category, keyword
            FROM keywords
            """
        ).fetchall()

        for row in rows:
            print(row)

    # ------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------

    def close(self):

        self.conn.close()