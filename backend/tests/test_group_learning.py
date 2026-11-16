import os,sys,uuid
from pathlib import Path
os.environ.setdefault("DATABASE_URL",f"sqlite:///{Path(__file__).with_name('group-learning-test.db')}")
os.environ.setdefault("JWT_SECRET","test-only-jwt-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("PASSWORD_PEPPER","test-only-password-pepper-with-at-least-32-characters")
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
import pytest
from app import main
from app.database import initialize_database
initialize_database()
client=TestClient(main.app)


@pytest.fixture(autouse=True)
def reset_test_auth_attempts():
    # The suite reuses one synthetic TestClient IP; reset the test-only
    # limiter counters between independent test cases.
    from app.models import SecurityEvent
    from app.database import SessionLocal
    with SessionLocal() as db:
        db.query(SecurityEvent).filter(
            SecurityEvent.event_type.like("auth_attempt_%"),
        ).delete(synchronize_session=False)
        db.commit()
    yield

def account(role):
    email=f"group-{role}-{uuid.uuid4().hex[:10]}@example.com"
    if role=="student":
        payload={"full_name":"Group Student","email":email,"password":"correct-horse-battery-staple-42","education_level":"University","subjects":["Math"]}
        response=client.post("/api/auth/register/student",json=payload)
    else:
        payload={"full_name":"Group Tutor","email":email,"password":"correct-horse-battery-staple-42","subjects":["Physics"],"teaching_level":"HSC","experience_years":3,"hourly_rate":500}
        response=client.post("/api/auth/register/tutor",json=payload)
    assert response.status_code==201,response.text
    return email,{"Authorization":"Bearer "+response.json()["access_token"]}

def create_group(headers,name="Physics Batch"):
    response=client.post("/api/groups",headers=headers,json={"name":name,"description":"Weekly learning group"})
    assert response.status_code==201,response.text
    return response.json()

def add_student(group_id,tutor_headers,email):
    response=client.post(f"/api/groups/{group_id}/members",headers=tutor_headers,json={"student_email":email})
    assert response.status_code==201,response.text
    return response.json()

def task_payload(title="Chapter exercises"):
    return {"title":title,"description":"Complete the practice set","due_date":None}

def test_tutor_group_crud_membership_and_private_group_access():
    tutor_email,tutor=account("tutor")
    student_email,student=account("student")
    _,stranger=account("student")
    group=create_group(tutor)
    assert group["is_owner"] is True
    assert client.put(f"/api/groups/{group['id']}",headers=tutor,json={"name":"Physics Batch A","description":"Updated"}).status_code==200
    added=add_student(group["id"],tutor,student_email)
    assert added["member_count"]==1
    assert added["members"][0]["email"]==student_email
    assert added["members"][0]["can_create_tasks"] is False
    assert client.get(f"/api/groups/{group['id']}",headers=student).status_code==200
    assert client.get(f"/api/groups/{group['id']}",headers=stranger).status_code==404
    assert client.put(f"/api/groups/{group['id']}",headers=student,json={"name":"Hijack","description":""}).status_code==403
    assert client.post("/api/groups",headers=student,json={"name":"Nope","description":""}).status_code==403

def test_member_permissions_are_enforced_and_owner_controls_group_tasks():
    email,tutor=account("tutor")
    student_email,student=account("student")
    group=create_group(tutor)
    group_id=group["id"]
    add_student(group_id,tutor,student_email)
    denied=client.post(f"/api/groups/{group_id}/tasks",headers=student,json=task_payload())
    assert denied.status_code==403
    task=client.post(f"/api/groups/{group_id}/tasks",headers=tutor,json=task_payload())
    assert task.status_code==201,task.text
    task_id=task.json()["id"]
    assert client.delete(f"/api/groups/{group_id}/tasks/{task_id}",headers=student).status_code==403
    permissions={"can_create_tasks":True,"can_edit_tasks":True,"can_assign_tasks":True}
    member_id=client.get(f"/api/groups/{group_id}",headers=tutor).json()["members"][0]["account_id"]
    updated=client.put(f"/api/groups/{group_id}/members/{member_id}/permissions",headers=tutor,json=permissions)
    assert updated.status_code==200
    created=client.post(f"/api/groups/{group_id}/tasks",headers=student,json=task_payload("Student-created task"))
    assert created.status_code==201,created.text
    created_id=created.json()["id"]
    edited=client.put(f"/api/groups/{group_id}/tasks/{task_id}",headers=student,json=task_payload("Edited by member"))
    assert edited.status_code==200
    assigned=client.post(f"/api/groups/{group_id}/tasks/{created_id}/assignments",headers=student,json={"all_members":True,"student_account_ids":[]})
    assert assigned.status_code==200,assigned.text
    assert assigned.json()["assignments"][0]["student_account_id"]==member_id
    assert client.delete(f"/api/groups/{group_id}/tasks/{created_id}",headers=student).status_code==403
    assert client.delete(f"/api/groups/{group_id}/tasks/{created_id}",headers=tutor).status_code==204

def test_student_sees_only_own_assignments_and_can_update_only_own_completion():
    _,tutor=account("tutor")
    first_email,first=account("student")
    second_email,second=account("student")
    group=create_group(tutor)
    group_id=group["id"]
    add_student(group_id,tutor,first_email)
    add_student(group_id,tutor,second_email)
    task=client.post(f"/api/groups/{group_id}/tasks",headers=tutor,json=task_payload())
    task_id=task.json()["id"]
    roster=client.get(f"/api/groups/{group_id}",headers=tutor).json()["members"]
    ids=[m["account_id"] for m in roster]
    assert len(ids)==2, f"Expected two group members, got {roster!r}"
    assigned=client.post(f"/api/groups/{group_id}/tasks/{task_id}/assignments",headers=tutor,json={"all_members":False,"student_account_ids":ids})
    assert assigned.status_code==200 and len(assigned.json()["assignments"])==2
    first_group=client.get(f"/api/groups/{group_id}",headers=first).json()
    assert len(first_group["tasks"])==1
    assert len(first_group["tasks"][0]["assignments"])==1
    assert first_group["tasks"][0]["assignments"][0]["student_account_id"]==ids[0] or first_group["tasks"][0]["assignments"][0]["student_account_id"]==ids[1]
    assert client.patch(f"/api/groups/{group_id}/tasks/{task_id}/completion",headers=first,json={"completed":True}).status_code==200
    first_after=client.get(f"/api/groups/{group_id}",headers=first).json()
    assert first_after["tasks"][0]["assignments"][0]["completed"] is True
    assert client.patch(f"/api/groups/{group_id}/tasks/{task_id}/completion",headers=second,json={"completed":True}).status_code==200

def test_assignment_targets_must_be_current_group_members():
    _,tutor=account("tutor")
    _,student=account("student")
    group=create_group(tutor)
    task=client.post(f"/api/groups/{group['id']}/tasks",headers=tutor,json=task_payload()).json()
    response=client.post(f"/api/groups/{group['id']}/tasks/{task['id']}/assignments",headers=tutor,json={"all_members":False,"student_account_ids":[999999]})
    assert response.status_code==422
    assert client.post(f"/api/groups/{group['id']}/members",headers=tutor,json={"student_email":"missing@example.com"}).status_code==404
    assert client.get("/api/groups").status_code==401


def test_each_member_permission_is_independent_and_enforced():
    student_email,student=account("student")
    _,tutor=account("tutor")
    group=create_group(tutor);gid=group["id"]
    add_student(gid,tutor,student_email)
    member_id=client.get(f"/api/groups/{gid}",headers=tutor).json()["members"][0]["account_id"]
    task=client.post(f"/api/groups/{gid}/tasks",headers=tutor,json=task_payload()).json()
    task_id=task["id"]

    # Create permission alone must not grant edit or assign rights.
    p={"can_create_tasks":True,"can_edit_tasks":False,"can_assign_tasks":False}
    assert client.put(f"/api/groups/{gid}/members/{member_id}/permissions",headers=tutor,json=p).status_code==200
    created=client.post(f"/api/groups/{gid}/tasks",headers=student,json=task_payload("Created by student"))
    assert created.status_code==201
    created_id=created.json()["id"]
    assert created.json()["assignments"]==[]
    assert client.put(f"/api/groups/{gid}/tasks/{task_id}",headers=student,json=task_payload("Denied edit")).status_code==403
    assert client.post(f"/api/groups/{gid}/tasks/{task_id}/assignments",headers=student,json={"all_members":True,"student_account_ids":[]}).status_code==403
    # A creator can still see their own task even without edit/assign permissions.
    visible=client.get(f"/api/groups/{gid}",headers=student).json()
    assert created_id in [row["id"] for row in visible["tasks"]]

    # Edit permission alone grants edit but not assignment.
    p={"can_create_tasks":False,"can_edit_tasks":True,"can_assign_tasks":False}
    assert client.put(f"/api/groups/{gid}/members/{member_id}/permissions",headers=tutor,json=p).status_code==200
    assert client.put(f"/api/groups/{gid}/tasks/{task_id}",headers=student,json=task_payload("Edited by student")).status_code==200
    assert client.post(f"/api/groups/{gid}/tasks/{task_id}/assignments",headers=student,json={"all_members":True,"student_account_ids":[]}).status_code==403

    # Assign permission alone grants assignment but not creation or editing.
    p={"can_create_tasks":False,"can_edit_tasks":False,"can_assign_tasks":True}
    assert client.put(f"/api/groups/{gid}/members/{member_id}/permissions",headers=tutor,json=p).status_code==200
    assert client.post(f"/api/groups/{gid}/tasks",headers=student,json=task_payload("Denied create")).status_code==403
    assert client.put(f"/api/groups/{gid}/tasks/{task_id}",headers=student,json=task_payload("Denied edit")).status_code==403
    assigned=client.post(f"/api/groups/{gid}/tasks/{task_id}/assignments",headers=student,json={"all_members":True,"student_account_ids":[]})
    assert assigned.status_code==200
    assert len(assigned.json()["assignments"])==1


def test_member_task_responses_never_expose_other_students_assignment_details():
    _,tutor=account("tutor")
    first_email,first=account("student")
    second_email,_=account("student")
    group=create_group(tutor);gid=group["id"]
    add_student(gid,tutor,first_email);add_student(gid,tutor,second_email)
    task=client.post(f"/api/groups/{gid}/tasks",headers=tutor,json=task_payload()).json()
    members=client.get(f"/api/groups/{gid}",headers=tutor).json()["members"]
    ids=[m["account_id"] for m in members]
    all_assigned=client.post(f"/api/groups/{gid}/tasks/{task['id']}/assignments",headers=tutor,json={"all_members":True,"student_account_ids":[]})
    assert all_assigned.status_code==200 and len(all_assigned.json()["assignments"])==2
    # The Student response contains only their own assignment, even on a task update.
    updated=client.put(f"/api/groups/{gid}/tasks/{task['id']}",headers=first,json=task_payload("Student view"))
    assert updated.status_code==403  # editing remains disabled by default
    own=client.get(f"/api/groups/{gid}",headers=first).json()["tasks"][0]["assignments"]
    assert len(own)==1 and own[0]["student_account_id"]==ids[0] or len(own)==1 and own[0]["student_account_id"]==ids[1]
