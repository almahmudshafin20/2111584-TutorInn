import os
import sys
import uuid
from pathlib import Path

os.environ["DATABASE_URL"] = f"sqlite:///{Path(__file__).with_name('issue27-test.db')}"
os.environ["ADMIN_API_KEY"] = "issue-27-test-admin-key"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
import main

client = TestClient(main.app)


def test_profile_owned_posts_independent_responses_subjects_and_admin_review():
    suffix = uuid.uuid4().hex[:10]
    tutor = client.post("/api/tutors", json={
        "full_name": "Tutor " + suffix, "email": f"tutor-{suffix}@example.com", "phone_number": "+8801712345678",
        "subjects": ["English", "Bangla", "English"], "teaching_level": "HSC",
        "experience_years": 4, "hourly_rate": 500, "bio": "Test tutor",
    })
    assert tutor.status_code == 201, tutor.text
    tutor_data = tutor.json()
    assert tutor_data["subjects"] == ["English", "Bangla"]

    students = []
    for name in ("A", "B", "C"):
        response = client.post("/api/students", json={
            "full_name": f"Student {name} {suffix}", "email": f"student-{name}-{suffix}@example.com", "phone_number": "+8801812345678",
            "education_level": "HSC", "subjects": ["English", "Mathematics"],
        })
        assert response.status_code == 201, response.text
        students.append(response.json())

    tutor_headers = {"X-TutorInn-Profile-ID": str(tutor_data["id"]), "X-TutorInn-Profile-Type": "tutor"}
    post = client.post("/api/posts", headers=tutor_headers, json={
        "post_type": "tutor", "author_name": "", "subjects": ["English", "Bangla"],
        "level": "HSC", "experience": "Four years", "availability": "Weekends",
        "location": "Dhaka", "fee": 500, "description": "English and Bangla tutoring",
    })
    assert post.status_code == 201, post.text
    post_data = post.json()
    assert post_data["author_profile_id"] == tutor_data["id"]
    assert post_data["author_profile_type"] == "tutor"
    assert post_data["subjects"] == ["English", "Bangla"]

    def profile_headers(student):
        return {"X-TutorInn-Profile-ID": str(student["id"]), "X-TutorInn-Profile-Type": "student"}

    a_response = client.post(f"/api/posts/{post_data['id']}/response", headers=profile_headers(students[0]),
                             json={"response": "Interested"})
    b_response = client.post(f"/api/posts/{post_data['id']}/response", headers=profile_headers(students[1]),
                             json={"response": "Not Interested"})
    c_response = client.post(f"/api/posts/{post_data['id']}/response", headers=profile_headers(students[2]),
                             json={"response": "Interested"})
    assert a_response.status_code == b_response.status_code == c_response.status_code == 200
    assert a_response.json()["response"] == "Interested"
    assert b_response.json()["review_status"] == "Not required"

    a_history = client.get("/api/responses", headers=profile_headers(students[0]))
    b_history = client.get("/api/responses", headers=profile_headers(students[1]))
    assert [item["profile_id"] for item in a_history.json()] == [students[0]["id"]]
    assert [item["response"] for item in b_history.json()] == ["Not Interested"]

    admin_headers = {"X-Admin-Key": "issue-27-test-admin-key"}
    queue = client.get("/api/admin/responses?review_status=Pending", headers=admin_headers)
    assert queue.status_code == 200, queue.text
    assert {item["profile_id"] for item in queue.json()} == {students[0]["id"], students[2]["id"]}
    approved = client.post(f"/api/responses/{a_response.json()['id']}/approve", headers=admin_headers)
    assert approved.status_code == 200
    assert approved.json()["review_status"] == "Approved"

    changed = client.post(f"/api/posts/{post_data['id']}/response", headers=profile_headers(students[1]),
                          json={"response": "Interested"})
    assert changed.status_code == 200
    assert changed.json()["review_status"] == "Pending"

    # The selected author can edit/delete the post; another profile cannot.
    wrong_owner = client.delete(f"/api/posts/{post_data['id']}", headers=profile_headers(students[0]))
    assert wrong_owner.status_code == 403
    deleted = client.delete(f"/api/tutors/{tutor_data['id']}")
    assert deleted.status_code == 204
    missing_post = client.get(f"/api/posts/{post_data['id']}")
    assert missing_post.status_code == 404


def test_public_profiles_hide_email_and_admin_match_view_is_protected():
    suffix = uuid.uuid4().hex[:10]
    tutor_email = f"private-tutor-{suffix}@example.com"
    student_email = f"private-student-{suffix}@example.com"
    tutor = client.post("/api/tutors", json={
        "full_name": f"Private Tutor {suffix}", "email": tutor_email, "subjects": ["Physics"],
        "teaching_level": "University", "experience_years": 5, "hourly_rate": 700, "bio": "Profile bio",
    })
    student = client.post("/api/students", json={
        "full_name": f"Private Student {suffix}", "email": student_email,
        "education_level": "University", "subjects": ["Physics"],
    })
    assert tutor.status_code == student.status_code == 201
    tutor_data, student_data = tutor.json(), student.json()
    assert "email" not in tutor_data
    assert "email" not in student_data
    assert "email" not in client.get(f"/api/tutors/{tutor_data['id']}").json()
    assert "email" not in client.get(f"/api/students/{student_data['id']}").json()
    assert "phone_number" not in tutor_data and "phone_number" not in student_data
    assert "phone_number" not in client.get(f"/api/tutors/{tutor_data['id']}").json()
    assert "phone_number" not in client.get(f"/api/students/{student_data['id']}").json()

    post = client.post("/api/posts", headers={
        "X-TutorInn-Profile-ID": str(student_data["id"]), "X-TutorInn-Profile-Type": "student",
    }, json={
        "post_type": "student", "author_name": "", "subjects": ["Physics"], "level": "University",
        "experience": "Needs mechanics support", "availability": "Evenings", "location": "Dhaka",
        "fee": 700, "description": "Looking for a physics tutor",
    })
    assert post.status_code == 201, post.text
    interest = client.post(f"/api/posts/{post.json()['id']}/response", headers={
        "X-TutorInn-Profile-ID": str(tutor_data["id"]), "X-TutorInn-Profile-Type": "tutor",
    }, json={"response": "Interested"})
    assert interest.status_code == 200, interest.text

    denied = client.get("/api/admin/matches?review_status=Pending")
    assert denied.status_code == 403
    admin = client.get("/api/admin/matches?review_status=Pending", headers={
        "X-Admin-Key": "issue-27-test-admin-key",
    })
    assert admin.status_code == 200, admin.text
    candidate = next(item for item in admin.json() if item["response"]["id"] == interest.json()["id"])
    assert candidate["tutor"]["email"] == tutor_email
    assert candidate["student"]["email"] == student_email
    assert candidate["tutor"]["phone_number"] == "+8801712345678"
    assert candidate["student"]["phone_number"] == "+8801812345678"
    assert candidate["response"]["review_status"] == "Pending"

    tutor_headers = {"X-TutorInn-Profile-ID": str(tutor_data["id"]), "X-TutorInn-Profile-Type": "tutor"}
    student_headers = {"X-TutorInn-Profile-ID": str(student_data["id"]), "X-TutorInn-Profile-Type": "student"}
    unrelated_headers = {"X-TutorInn-Profile-ID": "99999999", "X-TutorInn-Profile-Type": "student"}
    assert client.get("/api/profiles/approved-matches", headers=student_headers).json() == []
    assert client.get("/api/profiles/approved-matches", headers=tutor_headers).json() == []
    assert client.post(f"/api/responses/{interest.json()['id']}/approve", headers={"X-Admin-Key": "issue-27-test-admin-key"}).status_code == 200
    student_matches = client.get("/api/profiles/approved-matches", headers=student_headers)
    tutor_matches = client.get("/api/profiles/approved-matches", headers=tutor_headers)
    assert student_matches.status_code == tutor_matches.status_code == 200
    assert student_matches.json()[0]["counterpart"]["email"] == tutor_email
    assert student_matches.json()[0]["counterpart"]["phone_number"] == "+8801712345678"
    assert tutor_matches.json()[0]["counterpart"]["email"] == student_email
    assert tutor_matches.json()[0]["counterpart"]["phone_number"] == "+8801812345678"
    assert client.get("/api/profiles/approved-matches", headers=unrelated_headers).status_code == 409
