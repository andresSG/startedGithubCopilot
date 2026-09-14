"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import asyncio
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, StreamingResponse

from .database import (
    add_participant,
    get_activities as get_activities_from_database,
    initialize_database,
)

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

activities = {
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

initialize_database(activities)
subscribers: set[asyncio.Queue[str]] = set()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return get_activities_from_database()


async def publish_activity_update(activity_name: str) -> None:
    event = f"event: activity_updated\ndata: {json.dumps({'activity': activity_name})}\n\n"
    disconnected_subscribers = []
    for subscriber in subscribers:
        try:
            subscriber.put_nowait(event)
        except asyncio.QueueFull:
            disconnected_subscribers.append(subscriber)

    for subscriber in disconnected_subscribers:
        subscribers.discard(subscriber)


@app.get("/events", include_in_schema=False)
async def activity_events():
    subscriber: asyncio.Queue[str] = asyncio.Queue(maxsize=10)
    subscribers.add(subscriber)

    async def event_stream():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(subscriber.get(), timeout=15)
                    yield event
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            subscribers.discard(subscriber)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/activities/{activity_name}/signup")
async def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    try:
        add_participant(activity_name, email)
    except KeyError:
        raise HTTPException(status_code=404, detail="Activity not found")
    except ValueError as error:
        details = {
            "activity_full": (409, "Activity is full"),
            "already_registered": (409, "Student is already registered"),
        }
        status_code, detail = details[error.args[0]]
        raise HTTPException(status_code=status_code, detail=detail)

    await publish_activity_update(activity_name)
    return {"message": f"Signed up {email} for {activity_name}"}

