from pathlib import Path
import os
import sqlite3

DATABASE_PATH = Path(
    os.getenv("DATABASE_PATH", Path(__file__).parent / "activities.db")
)


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(activities: dict[str, dict]) -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL CHECK (max_participants >= 0)
            );

            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
                UNIQUE (activity_id, email)
            );
            """
        )

        activity_count = connection.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
        if activity_count:
            return

        for name, activity in activities.items():
            cursor = connection.execute(
                """
                INSERT INTO activities (name, description, schedule, max_participants)
                VALUES (?, ?, ?, ?)
                """,
                (
                    name,
                    activity["description"],
                    activity["schedule"],
                    activity["max_participants"],
                ),
            )
            connection.executemany(
                "INSERT INTO participants (activity_id, email) VALUES (?, ?)",
                [(cursor.lastrowid, email) for email in activity["participants"]],
            )


def get_activities() -> dict[str, dict]:
    with get_connection() as connection:
        activities = connection.execute(
            "SELECT id, name, description, schedule, max_participants "
            "FROM activities ORDER BY id"
        ).fetchall()
        participants = connection.execute(
            "SELECT activity_id, email FROM participants ORDER BY id"
        ).fetchall()

    participants_by_activity: dict[int, list[str]] = {}
    for participant in participants:
        participants_by_activity.setdefault(participant["activity_id"], []).append(
            participant["email"]
        )

    return {
        activity["name"]: {
            "description": activity["description"],
            "schedule": activity["schedule"],
            "max_participants": activity["max_participants"],
            "participants": participants_by_activity.get(activity["id"], []),
        }
        for activity in activities
    }


def add_participant(activity_name: str, email: str) -> None:
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        activity = connection.execute(
            "SELECT id, max_participants FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()
        if activity is None:
            raise KeyError("activity_not_found")

        participant_count = connection.execute(
            "SELECT COUNT(*) FROM participants WHERE activity_id = ?",
            (activity["id"],),
        ).fetchone()[0]
        if participant_count >= activity["max_participants"]:
            raise ValueError("activity_full")

        try:
            connection.execute(
                "INSERT INTO participants (activity_id, email) VALUES (?, ?)",
                (activity["id"], email),
            )
        except sqlite3.IntegrityError as error:
            raise ValueError("already_registered") from error


def remove_participant(activity_name: str, email: str) -> None:
    with get_connection() as connection:
        activity = connection.execute(
            "SELECT id FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()
        if activity is None:
            raise KeyError("activity_not_found")

        result = connection.execute(
            "DELETE FROM participants WHERE activity_id = ? AND email = ?",
            (activity["id"], email),
        )
        if result.rowcount == 0:
            raise KeyError("participant_not_found")
