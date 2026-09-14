from urllib.parse import quote


def test_get_activities_returns_activity_details(client):
    response = client.get("/activities")

    assert response.status_code == 200
    activities = response.json()
    assert "Chess Club" in activities
    assert {"description", "schedule", "max_participants", "participants"} <= set(
        activities["Chess Club"]
    )


def test_signup_registers_student(client):
    email = "new.student@mergington.edu"

    response = client.post(
        f"/activities/{quote('Art Club', safe='')}/signup",
        params={"email": email},
    )

    assert response.status_code == 200
    assert email in client.get("/activities").json()["Art Club"]["participants"]


def test_signup_rejects_duplicate_student(client):
    email = "duplicate.student@mergington.edu"
    activity = quote("Art Club", safe="")

    first_response = client.post(f"/activities/{activity}/signup", params={"email": email})
    second_response = client.post(f"/activities/{activity}/signup", params={"email": email})

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    participants = client.get("/activities").json()["Art Club"]["participants"]
    assert participants.count(email) == 1


def test_signup_rejects_unknown_activity(client):
    response = client.post(
        f"/activities/{quote('Unknown Club', safe='')}/signup",
        params={"email": "student@mergington.edu"},
    )

    assert response.status_code == 404


def test_unregister_removes_student(client):
    activity = quote("Chess Club", safe="")
    email = quote("michael@mergington.edu", safe="")

    response = client.delete(f"/activities/{activity}/participants/{email}")

    assert response.status_code == 200
    assert "michael@mergington.edu" not in client.get("/activities").json()["Chess Club"]["participants"]


def test_unregister_rejects_unknown_participant(client):
    response = client.delete(
        f"/activities/{quote('Chess Club', safe='')}/participants/unknown%40mergington.edu"
    )

    assert response.status_code == 404


def test_unregister_rejects_unknown_activity(client):
    response = client.delete(
        f"/activities/{quote('Unknown Club', safe='')}/participants/student%40mergington.edu"
    )

    assert response.status_code == 404