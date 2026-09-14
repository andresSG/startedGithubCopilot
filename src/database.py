from pathlib import Path
import os
import sqlite3


DEFAULT_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
    "Soccer Club": {
        "description": "Develop soccer skills and compete in team matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 24,
        "participants": [],
    },
    "Tennis Club": {
        "description": "Learn tennis fundamentals and practice match play",
        "schedule": "Wednesdays, 3:30 PM - 5:00 PM",
        "max_participants": 16,
        "participants": [],
    },
    "Art Club": {
        "description": "Explore drawing, painting, and other visual art techniques",
        "schedule": "Mondays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": [],
    },
    "Drama Club": {
        "description": "Build acting skills and perform creative theater productions",
        "schedule": "Fridays, 3:30 PM - 5:30 PM",
        "max_participants": 20,
        "participants": [],
    },
    "Debate Club": {
        "description": "Develop public speaking, research, and critical thinking skills",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 18,
        "participants": [],
    },
    "Science Club": {
        "description": "Investigate scientific ideas through experiments and discussion",
        "schedule": "Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": [],
    },
}

DATABASE_PATH = Path(
    os.getenv("DATABASE_PATH", Path(__file__).parent / "activities.db")
)


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
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

        for name, activity in DEFAULT_ACTIVITIES.items():
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
