import os
import secrets
import sys
import uuid
from datetime import timedelta
from pathlib import Path

os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).with_name('issue27-test.db')}")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("PASSWORD_PEPPER", "test-only-password-pepper-with-at-least-32-characters")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
import pytest
from app import main
from app.auth import create_access_token, hash_password, timestamp, token_hash, utc_now
from app.database import SessionLocal, initialize_database
from app.models import AccountDeletionRequest, LearningPost, RefreshSession, SecurityEvent, Student, Tutor, UserAccount

initialize_database()
client = TestClient(main.app)


@pytest.fixture(autouse=True)
def isolate_auth_rate_limit_events():
    # Each test starts with a clean auth-attempt bucket while requests inside
    # a test still share the real limiter and can exercise rate-limit behavior.
    with SessionLocal() as db:
        db.query(SecurityEvent).filter(
            SecurityEvent.event_type.like("auth_attempt_%"),
        ).delete(synchronize_session=False)
        db.commit()


def register_student(email: str):
    response = client.post("/api/auth/register/student", json={
        "full_name": "Report Student", "email": email, "password": "correct-horse-battery-staple-42",
        "education_level": "University", "subjects": ["Mathematics"],
    })
    assert response.status_code == 201, response.text
    data = response.json()
    return data, {"Authorization": f"Bearer {data['access_token']}"}


def register_tutor(email: str):
    response = client.post("/api/auth/register/tutor", json={
        "full_name": "Report Tutor", "email": email, "password": "correct-horse-battery-staple-42",
        "subjects": ["Physics"], "teaching_level": "HSC", "experience_years": 3, "hourly_rate": 500,
    })
    assert response.status_code == 201, response.text
    data = response.json()
    return data, {"Authorization": f"Bearer {data['access_token']}"}


def admin_headers():
    email = f"moderation-admin-{uuid.uuid4().hex[:10]}@example.com"
    with SessionLocal() as db:
        account = UserAccount(email=email, password_hash=hash_password("correct-horse-battery-staple-42"),
                              role="admin", status="active", created_at=timestamp(), updated_at=timestamp())
        db.add(account)
        db.flush()
        now = timestamp()
        session = RefreshSession(
            account_id=account.id, token_hash=token_hash(secrets.token_urlsafe(48)),
            family_id=str(uuid.uuid4()), csrf_token_hash=token_hash(secrets.token_urlsafe(32)),
            created_at=now, last_used_at=now, expires_at=(utc_now() + timedelta(days=1)).isoformat(),
            revoked_at=None, replaced_by=None, user_agent="moderation-test", ip_address="127.0.0.1",
        )
        db.add(session)
        db.flush()
        access, _ = create_access_token(account, session.id)
        db.commit()
    return {"Authorization": f"Bearer {access}"}


def test_reports_cover_profiles_tutoring_posts_and_tutoring_requests():
    suffix = uuid.uuid4().hex[:10]
    student, student_headers = register_student(f"reporter-{suffix}@example.com")
    other_student, _ = register_student(f"request-owner-{suffix}@example.com")
    tutor, _ = register_tutor(f"reported-tutor-{suffix}@example.com")
    with SessionLocal() as db:
        other_profile = db.query(Student).filter_by(account_id=other_student["account"]["id"]).one()
        tutor_profile = db.query(Tutor).filter_by(account_id=tutor["account"]["id"]).one()
        offer = LearningPost(
            post_type="tutor", author_name="Report Tutor", subject="Physics", level="HSC", fee=500,
            description="Tutor offer", author_profile_id=tutor_profile.id, author_profile_type="tutor",
            created_at=timestamp(),
        )
        request = LearningPost(
            post_type="student", author_name="Request owner", subject="Mathematics", level="University", fee=500,
            description="Student request", author_profile_id=other_profile.id, author_profile_type="student",
            created_at=timestamp(),
        )
        db.add_all([offer, request])
        db.commit()
        offer_id, request_id, tutor_profile_id, other_profile_id = offer.id, request.id, tutor_profile.id, other_profile.id

    profile_report = client.post("/api/reports", headers=student_headers, json={
        "target_type": "profile", "target_role": "tutor", "target_id": tutor_profile_id, "reason": "impersonation",
        "description": "Profile identity concern",
    })
    student_profile_report = client.post("/api/reports", headers=student_headers, json={
        "target_type": "profile", "target_role": "student", "target_id": other_profile_id,
        "reason": "harassment", "description": "Student profile report",
    })
    post_report = client.post("/api/reports", headers=student_headers, json={
        "target_type": "tutoring_post", "target_id": offer_id, "reason": "misleading",
        "description": "Offer details appear inaccurate",
    })
    request_report = client.post("/api/reports", headers=student_headers, json={
        "target_type": "tutoring_request", "target_id": request_id, "reason": "spam",
        "description": "Repeated solicitation",
    })
    assert profile_report.status_code == student_profile_report.status_code == post_report.status_code == request_report.status_code == 201
    duplicate = client.post("/api/reports", headers=student_headers, json={
        "target_type": "profile", "target_role": "tutor", "target_id": tutor_profile_id, "reason": "other", "description": "",
    })
    assert duplicate.status_code == 409

    admin = admin_headers()
    listed = client.get("/api/admin/reports?status=pending&limit=20", headers=admin)
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] >= 4
    report_id = profile_report.json()["id"]
    reviewed = client.patch(f"/api/admin/reports/{report_id}", headers=admin, json={
        "status": "resolved", "review_note": "Reviewed the profile and recorded the outcome.",
    })
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "resolved"
    assert client.get("/api/admin/reports", headers=student_headers).status_code == 403


def test_admin_subject_catalogue_duplicate_protection_and_reference_safeguards():
    admin = admin_headers()
    suffix = uuid.uuid4().hex[:8]
    name = f"Catalogue {suffix}"
    created = client.post("/api/admin/subjects", headers=admin, json={"name": name})
    assert created.status_code == 201, created.text
    subject = created.json()
    duplicate = client.post("/api/admin/subjects", headers=admin, json={"name": name.upper()})
    assert duplicate.status_code == 409

    with SessionLocal() as db:
        student = Student(
            full_name="Catalogue Test Student", email=f"catalogue-{suffix}@example.com",
            education_level="University", preferred_subjects=name, subjects_json='["' + name + '"]',
        )
        db.add(student)
        db.commit()
    blocked_delete = client.delete(f"/api/admin/subjects/{subject['id']}", headers=admin)
    assert blocked_delete.status_code == 409
    blocked_rename = client.patch(f"/api/admin/subjects/{subject['id']}", headers=admin, json={"name": name + " Updated"})
    assert blocked_rename.status_code == 409

    deactivated = client.patch(f"/api/admin/subjects/{subject['id']}", headers=admin, json={"active": False})
    assert deactivated.status_code == 200
    active = client.get("/api/subjects")
    assert active.status_code == 200
    assert name not in active.json()

    unused = client.post("/api/admin/subjects", headers=admin, json={"name": f"Unused {suffix}"})
    assert unused.status_code == 201
    deleted = client.delete(f"/api/admin/subjects/{unused.json()['id']}", headers=admin)
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True


def test_account_deletion_request_requires_password_and_admin_rejection_reactivates_account():
    suffix = uuid.uuid4().hex[:10]
    student, headers = register_student(f"delete-reject-{suffix}@example.com")
    wrong = client.post("/api/me/deletion-request", headers=headers, json={
        "current_password": "incorrect-password-value", "reason": "Testing request rejection", "deletion_option": "complete",
    })
    assert wrong.status_code == 400
    requested = client.post("/api/me/deletion-request", headers=headers, json={
        "current_password": "correct-horse-battery-staple-42", "reason": "I no longer need the account.", "deletion_option": "complete",
    })
    assert requested.status_code == 201, requested.text
    with SessionLocal() as db:
        account = db.get(UserAccount, student["account"]["id"])
        assert account.status == "deletion_pending"
        assert db.query(RefreshSession).filter_by(account_id=account.id, revoked_at=None).count() == 0
    assert client.post("/api/auth/login", json={
        "email": student["account"]["email"], "password": "correct-horse-battery-staple-42",
    }).status_code == 403
    admin = admin_headers()
    listed = client.get("/api/admin/account-deletion-requests?status=pending", headers=admin)
    assert listed.status_code == 200, listed.text
    item = next(row for row in listed.json()["items"] if row["id"] == requested.json()["id"])
    rejected = client.patch(f"/api/admin/account-deletion-requests/{item['id']}", headers=admin, json={
        "status": "rejected", "review_note": "Request reviewed; account restored.",
    })
    assert rejected.status_code == 200, rejected.text
    with SessionLocal() as db:
        account = db.get(UserAccount, student["account"]["id"])
        assert account.status == "active"
    assert client.post("/api/auth/login", json={
        "email": student["account"]["email"], "password": "correct-horse-battery-staple-42",
    }).status_code == 200


def test_approved_student_deletion_removes_profile_posts_tasks_and_membership():
    from app.models import GroupLearningTask, GroupTaskAssignment, LearningGroup, LearningGroupMember, PersonalLearningTask

    suffix = uuid.uuid4().hex[:10]
    student, student_headers = register_student(f"delete-student-{suffix}@example.com")
    tutor, _ = register_tutor(f"delete-owner-{suffix}@example.com")
    with SessionLocal() as db:
        student_profile = db.query(Student).filter_by(account_id=student["account"]["id"]).one()
        post = LearningPost(
            post_type="student", author_name="Delete Student", subject="Physics", level="University",
            fee=500, description="Private request", author_profile_id=student_profile.id,
            author_profile_type="student", created_at=timestamp(),
        )
        group = LearningGroup(owner_account_id=tutor["account"]["id"], name="Deletion test group",
                              description="", created_at=timestamp(), updated_at=timestamp())
        db.add_all([post, group])
        db.flush()
        task = GroupLearningTask(group_id=group.id, created_by_account_id=tutor["account"]["id"],
                                 title="Shared task", description="", created_at=timestamp(), updated_at=timestamp())
        membership = LearningGroupMember(group_id=group.id, student_account_id=student["account"]["id"],
                                         joined_at=timestamp())
        personal = PersonalLearningTask(owner_account_id=student["account"]["id"], title="Private task",
                                        description="", completed=False, created_at=timestamp(), updated_at=timestamp())
        db.add_all([task, membership, personal])
        db.flush()
        assignment = GroupTaskAssignment(task_id=task.id, student_account_id=student["account"]["id"],
                                         assigned_at=timestamp())
        db.add(assignment)
        post_id, group_id, personal_id = post.id, group.id, personal.id
        student_profile_id = student_profile.id
        db.commit()
    requested = client.post("/api/me/deletion-request", headers=student_headers, json={
        "current_password": "correct-horse-battery-staple-42", "reason": "Remove my account and data.", "deletion_option": "complete",
    })
    assert requested.status_code == 201, requested.text
    approved = client.patch(f"/api/admin/account-deletion-requests/{requested.json()['id']}",
        headers=admin_headers(), json={"status": "approved", "deletion_option": "complete", "review_note": "Verified request."})
    assert approved.status_code == 200, approved.text
    assert approved.json()["deleted"] is True
    with SessionLocal() as db:
        assert db.get(UserAccount, student["account"]["id"]) is None
        assert db.get(Student, student_profile_id) is None
        assert db.get(LearningPost, post_id) is None
        assert db.get(PersonalLearningTask, personal_id) is None
        assert db.query(LearningGroupMember).filter_by(student_account_id=student["account"]["id"]).count() == 0
        assert db.query(GroupTaskAssignment).filter_by(student_account_id=student["account"]["id"]).count() == 0
        assert db.get(LearningGroup, group_id) is not None
        from app.models import AccountDeletionRequest, SecurityEvent
        deletion = db.get(AccountDeletionRequest, requested.json()["id"])
        assert deletion.status == "approved" and deletion.account_id is None and deletion.account_email == "[deleted]"
        retained = db.query(SecurityEvent).filter_by(event_type="registration_succeeded", ip_address="testclient").first()
        assert retained is not None


def test_tutor_deletion_preserves_other_students_group_work_or_blocks_group_removal():
    from app.models import GroupLearningTask, GroupTaskAssignment, LearningGroup, LearningGroupMember, RetainedContent

    suffix = uuid.uuid4().hex[:10]
    tutor, tutor_headers = register_tutor(f"delete-tutor-{suffix}@example.com")
    student, _ = register_student(f"keep-student-{suffix}@example.com")
    with SessionLocal() as db:
        group = LearningGroup(owner_account_id=tutor["account"]["id"], name="Tutor owned group",
                              description="", created_at=timestamp(), updated_at=timestamp())
        db.add(group)
        db.flush()
        task = GroupLearningTask(group_id=group.id, created_by_account_id=tutor["account"]["id"],
                                 title="Tutor task", description="", created_at=timestamp(), updated_at=timestamp())
        db.add(task)
        db.flush()
        member = LearningGroupMember(group_id=group.id, student_account_id=student["account"]["id"],
                                     joined_at=timestamp())
        assignment = GroupTaskAssignment(task_id=task.id, student_account_id=student["account"]["id"],
                                         assigned_at=timestamp())
        db.add_all([member, assignment])
        group_id, task_id = group.id, task.id
        db.commit()
    requested = client.post("/api/me/deletion-request", headers=tutor_headers, json={
        "current_password": "correct-horse-battery-staple-42", "reason": "Please remove my tutor account.",
        "content_action": "delete_all",
    })
    assert requested.status_code == 201, requested.text
    admin = admin_headers()
    blocked = client.patch(f"/api/admin/account-deletion-requests/{requested.json()['id']}",
        headers=admin, json={"status": "approved", "content_action": "delete_all", "review_note": "Do not erase student work."})
    assert blocked.status_code == 409, blocked.text
    with SessionLocal() as db:
        assert db.get(UserAccount, tutor["account"]["id"]) is not None
        assert db.get(LearningGroup, group_id) is not None
        assert db.get(GroupLearningTask, task_id) is not None
        assert db.query(LearningGroupMember).filter_by(group_id=group_id).count() == 1
        assert db.query(GroupTaskAssignment).filter_by(task_id=task_id).count() == 1

    retained = client.patch(f"/api/admin/account-deletion-requests/{requested.json()['id']}",
        headers=admin, json={
            "status": "approved", "content_action": "account_only",
            "visibility": "visible", "anonymize_content": False,
            "review_note": "Keep the shared group and student progress.",
        })
    assert retained.status_code == 200, retained.text
    with SessionLocal() as db:
        assert db.get(UserAccount, tutor["account"]["id"]) is None
        group = db.get(LearningGroup, group_id)
        task = db.get(GroupLearningTask, task_id)
        assert group is not None and group.owner_account_id is None
        assert task is not None and task.created_by_account_id is None
        assert db.query(LearningGroupMember).filter_by(group_id=group_id, student_account_id=student["account"]["id"]).count() == 1
        assert db.query(GroupTaskAssignment).filter_by(task_id=task_id, student_account_id=student["account"]["id"]).count() == 1
        retained_types = {row.content_type for row in db.query(RetainedContent).filter_by(deletion_request_id=requested.json()["id"]).all()}
        assert {"learning_group", "group_task"}.issubset(retained_types)

def test_deleted_account_registration_ip_remains_pseudonymously_countable():
    from app.models import SecurityEvent

    suffix = uuid.uuid4().hex[:10]
    student, headers = register_student(f"delete-ip-{suffix}@example.com")
    requested = client.post("/api/me/deletion-request", headers=headers, json={
        "current_password": "correct-horse-battery-staple-42", "reason": "Delete my account.", "deletion_option": "complete",
    })
    assert requested.status_code == 201, requested.text
    approved = client.patch(f"/api/admin/account-deletion-requests/{requested.json()['id']}",
        headers=admin_headers(), json={"status": "approved", "deletion_option": "complete", "review_note": "Verified."})
    assert approved.status_code == 200, approved.text
    with SessionLocal() as db:
        event = db.query(SecurityEvent).filter_by(
            event_type="registration_succeeded",
            details="deleted_account_id=" + str(student["account"]["id"]),
        ).first()
        assert event is not None
        assert event.account_id is None and event.attempted_email == ""
        assert event.ip_address == "testclient"
    report = client.get("/api/admin/security?hours=720&min_events=1", headers=admin_headers())
    assert report.status_code == 200, report.text
    ip_summary = next(item for item in report.json()["registrations_by_ip"] if item["ip_address"] == "testclient")
    assert ip_summary["distinct_accounts"] >= 1


def test_pending_deletion_cannot_be_bypassed_by_generic_admin_status_change():
    suffix = uuid.uuid4().hex[:10]
    student, headers = register_student(f"delete-lock-{suffix}@example.com")
    requested = client.post("/api/me/deletion-request", headers=headers, json={
        "current_password": "correct-horse-battery-staple-42", "reason": "Testing review-only status.", "deletion_option": "complete",
    })
    assert requested.status_code == 201, requested.text
    direct = client.patch(f"/api/admin/users/{student['account']['id']}/status",
        headers=admin_headers(), json={"status": "active", "reason": "Trying to bypass deletion review."})
    assert direct.status_code == 409


def test_legacy_profile_delete_routes_cannot_bypass_admin_approved_account_deletion(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_MODE", "true")
    suffix = uuid.uuid4().hex[:10]
    student, _ = register_student(f"linked-student-{suffix}@example.com")
    tutor, _ = register_tutor(f"linked-tutor-{suffix}@example.com")
    with SessionLocal() as db:
        student_profile = db.query(Student).filter_by(account_id=student["account"]["id"]).one()
        tutor_profile = db.query(Tutor).filter_by(account_id=tutor["account"]["id"]).one()
        student_id, tutor_id = student_profile.id, tutor_profile.id
    assert client.delete(f"/api/students/{student_id}").status_code == 409
    assert client.delete(f"/api/tutors/{tutor_id}").status_code == 409
    with SessionLocal() as db:
        assert db.get(Student, student_id) is not None
        assert db.get(Tutor, tutor_id) is not None


def test_user_can_request_anonymization_and_admin_can_override_with_complete_removal():
    suffix = uuid.uuid4().hex[:10]
    student, headers = register_student(f"delete-choice-{suffix}@example.com")
    with SessionLocal() as db:
        profile = db.query(Student).filter_by(account_id=student["account"]["id"]).one()
        post = LearningPost(
            post_type="student", author_name=profile.full_name, subject="Math", level="College",
            fee=400, description="Keep as anonymous post", author_profile_id=profile.id,
            author_profile_type="student", created_at=timestamp(),
        )
        db.add(post)
        db.commit()
        post_id = post.id
    requested = client.post("/api/me/deletion-request", headers=headers, json={
        "current_password": "correct-horse-battery-staple-42",
        "reason": "Prefer anonymization", "deletion_option": "anonymize",
    })
    assert requested.status_code == 201, requested.text
    listed = client.get("/api/admin/account-deletion-requests?status=pending", headers=admin_headers())
    item = next(row for row in listed.json()["items"] if row["id"] == requested.json()["id"])
    assert item["requested_option"] == "anonymize"
    approved = client.patch(f"/api/admin/account-deletion-requests/{item['id']}",
        headers=admin_headers(), json={
            "status": "approved", "deletion_option": "complete",
            "review_note": "Admin selected complete removal.",
        })
    assert approved.status_code == 200, approved.text
    assert approved.json()["final_option"] == "complete"
    with SessionLocal() as db:
        assert db.get(UserAccount, student["account"]["id"]) is None
        assert db.get(LearningPost, post_id) is None
        receipt = db.get(AccountDeletionRequest, item["id"])
        assert receipt.requested_option == "anonymize"
        assert receipt.final_option == "complete"


def test_anonymization_preserves_post_without_profile_identity():
    suffix = uuid.uuid4().hex[:10]
    student, headers = register_student(f"delete-anon-{suffix}@example.com")
    with SessionLocal() as db:
        profile = db.query(Student).filter_by(account_id=student["account"]["id"]).one()
        post = LearningPost(
            post_type="student", author_name=profile.full_name, subject="English", level="College",
            fee=300, description="Shared content retained", author_profile_id=profile.id,
            author_profile_type="student", created_at=timestamp(),
        )
        db.add(post)
        db.commit()
        post_id = post.id
    requested = client.post("/api/me/deletion-request", headers=headers, json={
        "current_password": "correct-horse-battery-staple-42",
        "reason": "Please anonymize me", "deletion_option": "anonymize",
    })
    assert requested.status_code == 201, requested.text
    approved = client.patch(f"/api/admin/account-deletion-requests/{requested.json()['id']}",
        headers=admin_headers(), json={
            "status": "approved", "deletion_option": "anonymize",
            "review_note": "Approved anonymization.",
        })
    assert approved.status_code == 200, approved.text
    assert approved.json()["anonymized"] is True
    with SessionLocal() as db:
        post = db.get(LearningPost, post_id)
        assert post is not None
        assert post.author_name == "Deleted user"
        assert post.author_profile_id is None and post.author_profile_type is None
        receipt = db.get(AccountDeletionRequest, requested.json()["id"])
        assert receipt.requested_option == "anonymize" and receipt.final_option == "anonymize"



def test_expanded_account_deletion_preferences_are_persisted_separately():
    suffix = uuid.uuid4().hex[:10]
    student, headers = register_student(f"delete-preferences-{suffix}@example.com")
    requested = client.post("/api/me/deletion-request", headers=headers, json={
        "current_password": "correct-horse-battery-staple-42",
        "reason": "Keep my shared work but hide it.",
        "content_action": "account_only",
        "visibility": "hidden",
        "anonymize_content": True,
    })
    assert requested.status_code == 201, requested.text
    with SessionLocal() as db:
        deletion = db.query(AccountDeletionRequest).filter_by(id=requested.json()["id"]).one()
        assert deletion.requested_account_action == "delete_account"
        assert deletion.requested_content_action == "account_only"
        assert deletion.requested_content_ids == "[]"
        assert deletion.requested_visibility == "hidden"
        assert deletion.requested_anonymize_content is True


def test_expanded_account_deletion_rejects_empty_selected_content():
    suffix = uuid.uuid4().hex[:10]
    _, headers = register_student(f"delete-selected-empty-{suffix}@example.com")
    response = client.post("/api/me/deletion-request", headers=headers, json={
        "current_password": "correct-horse-battery-staple-42",
        "content_action": "delete_selected",
        "selected_content": [],
    })
    assert response.status_code == 422


def test_admin_selected_content_deletion_retains_and_anonymizes_unselected_content():
    from app.models import PersonalLearningTask, RetainedContent

    suffix = uuid.uuid4().hex[:10]
    student, headers = register_student(f"delete-selected-{suffix}@example.com")
    with SessionLocal() as db:
        profile = db.query(Student).filter_by(account_id=student["account"]["id"]).one()
        post = LearningPost(
            post_type="student", author_name=profile.full_name, subject="Biology", level="College",
            fee=250, description="Retain and hide this post", author_profile_id=profile.id,
            author_profile_type="student", created_at=timestamp(),
        )
        selected_task = PersonalLearningTask(
            owner_account_id=student["account"]["id"], title="Remove this task", description="",
            completed=False, created_at=timestamp(), updated_at=timestamp(),
        )
        retained_task = PersonalLearningTask(
            owner_account_id=student["account"]["id"], title="Keep this task", description="",
            completed=False, created_at=timestamp(), updated_at=timestamp(),
        )
        db.add_all([post, selected_task, retained_task])
        db.commit()
        post_id, selected_id, retained_id = post.id, selected_task.id, retained_task.id

    requested = client.post("/api/me/deletion-request", headers=headers, json={
        "current_password": "correct-horse-battery-staple-42",
        "content_action": "delete_selected",
        "selected_content": [{"content_type": "personal_task", "content_id": selected_id}],
        "visibility": "hidden",
        "anonymize_content": True,
    })
    assert requested.status_code == 201, requested.text
    approved = client.patch(f"/api/admin/account-deletion-requests/{requested.json()['id']}",
        headers=admin_headers(), json={
            "status": "approved",
            "content_action": "delete_selected",
            "selected_content": [{"content_type": "personal_task", "content_id": selected_id}],
            "visibility": "hidden",
            "anonymize_content": True,
            "review_note": "Delete the selected task and retain the remaining items.",
        })
    assert approved.status_code == 200, approved.text
    with SessionLocal() as db:
        assert db.get(UserAccount, student["account"]["id"]) is None
        assert db.get(PersonalLearningTask, selected_id) is None
        retained_task = db.get(PersonalLearningTask, retained_id)
        assert retained_task is not None and retained_task.owner_account_id is None
        post = db.get(LearningPost, post_id)
        assert post is not None and post.author_name == "Deleted user"
        assert post.author_profile_id is None and post.author_profile_type is None
        retained = db.query(RetainedContent).filter_by(deletion_request_id=requested.json()["id"]).all()
        assert {(row.content_type, row.content_id, row.visibility, row.anonymized) for row in retained} == {
            ("personal_task", retained_id, "hidden", True),
            ("learning_post", post_id, "hidden", True),
        }



def test_former_user_one_time_link_lists_and_requests_removal_of_retained_content():
    import hashlib
    from app.models import FormerUserContentRemovalRequest, FormerUserContentToken, RetainedContent

    raw_token = secrets.token_urlsafe(48)
    with SessionLocal() as db:
        post = LearningPost(
            post_type="student", author_name="Deleted user", subject="English", level="College",
            fee=0, description="Retained after account deletion", created_at=timestamp(),
        )
        db.add(post)
        db.flush()
        deletion = AccountDeletionRequest(
            account_id=None, account_email="", account_role="student", reason="",
            requested_option="complete", final_option="anonymize", status="approved",
            requested_at=timestamp(), final_content_action="retain_all",
            final_visibility="hidden", final_anonymize_content=True,
        )
        db.add(deletion)
        db.flush()
        retained = RetainedContent(
            deletion_request_id=deletion.id, content_type="learning_post",
            content_id=post.id, visibility="hidden", anonymized=True, created_at=timestamp(),
        )
        token = FormerUserContentToken(
            deletion_request_id=deletion.id,
            token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
            expires_at=(utc_now() + timedelta(hours=48)).isoformat(),
            created_at=timestamp(),
        )
        db.add_all([retained, token])
        db.commit()
        deletion_id, post_id = deletion.id, post.id

    listed = client.post("/api/former-user/retained-content", json={"token": raw_token})
    assert listed.status_code == 200, listed.text
    assert listed.json()["items"] == [{
        "content_type": "learning_post", "content_id": post_id,
        "label": "Learning post: English", "description": "Retained after account deletion",
        "visibility": "hidden",
    }]

    submitted = client.post("/api/former-user/content-removal-requests", json={
        "token": raw_token,
        "selected_content": [{"content_type": "learning_post", "content_id": post_id}],
    })
    assert submitted.status_code == 201, submitted.text
    assert submitted.json()["status"] == "pending"

    replay = client.post("/api/former-user/content-removal-requests", json={
        "token": raw_token,
        "selected_content": [{"content_type": "learning_post", "content_id": post_id}],
    })
    assert replay.status_code == 400

    queue = client.get("/api/admin/former-user-content-removal-requests", headers=admin_headers())
    assert queue.status_code == 200, queue.text
    item = next(row for row in queue.json()["items"] if row["deletion_request_id"] == deletion_id)
    reviewed = client.patch(
        f"/api/admin/former-user-content-removal-requests/{item['id']}",
        headers=admin_headers(),
        json={"status": "approved", "review_note": "Verified former-user request."},
    )
    assert reviewed.status_code == 200, reviewed.text
    with SessionLocal() as db:
        assert db.get(LearningPost, post_id) is None
        assert db.query(RetainedContent).filter_by(deletion_request_id=deletion_id).count() == 0
        request_row = db.get(FormerUserContentRemovalRequest, item["id"])
        assert request_row.status == "approved"
