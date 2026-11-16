import os, sys, uuid
from datetime import date, timedelta
from pathlib import Path
os.environ.setdefault("DATABASE_URL",f"sqlite:///{Path(__file__).with_name('issue27-test.db')}")
os.environ.setdefault("JWT_SECRET","test-only-jwt-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("PASSWORD_PEPPER","test-only-password-pepper-with-at-least-32-characters")
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app import main
from app.database import initialize_database
initialize_database()
client=TestClient(main.app)

def student_headers():
    email=f"task-student-{uuid.uuid4().hex[:10]}@example.com"
    r=client.post("/api/auth/register/student",json={"full_name":"Task Student","email":email,"password":"correct-horse-battery-staple-42","education_level":"University","subjects":["Math"]})
    assert r.status_code==201,r.text
    return {"Authorization":f"Bearer {r.json()['access_token']}"}

def tutor_headers():
    email=f"task-tutor-{uuid.uuid4().hex[:10]}@example.com"
    r=client.post("/api/auth/register/tutor",json={"full_name":"Task Tutor","email":email,"password":"correct-horse-battery-staple-42","subjects":["Physics"],"teaching_level":"HSC","experience_years":2,"hourly_rate":500})
    assert r.status_code==201,r.text
    return {"Authorization":f"Bearer {r.json()['access_token']}"}

def payload(**updates):
    result={"title":"Revise algebra","description":"Practice questions","category":"Revision","due_date":(date.today()+timedelta(days=2)).isoformat(),"completed":False}
    result.update(updates); return result

def test_student_task_crud_completion_and_due_status():
    h=student_headers(); created=client.post("/api/me/tasks",headers=h,json=payload())
    assert created.status_code==201,created.text
    task=created.json(); assert task["status"]=="open"
    assert client.get(f"/api/me/tasks/{task['id']}",headers=h).json()["title"]=="Revise algebra"
    done=client.put(f"/api/me/tasks/{task['id']}",headers=h,json=payload(completed=True))
    assert done.status_code==200 and done.json()["status"]=="completed"
    overdue=client.put(f"/api/me/tasks/{task['id']}",headers=h,json=payload(completed=False,due_date=(date.today()-timedelta(days=1)).isoformat()))
    assert overdue.json()["status"]=="overdue"
    assert client.delete(f"/api/me/tasks/{task['id']}",headers=h).status_code==204
    assert client.get(f"/api/me/tasks/{task['id']}",headers=h).status_code==404

def test_task_ownership_isolated_between_student_and_tutor():
    owner=tutor_headers(); stranger=student_headers()
    created=client.post("/api/me/tasks",headers=owner,json=payload()); task_id=created.json()["id"]
    assert client.get("/api/me/tasks",headers=stranger).json()==[]
    assert client.get(f"/api/me/tasks/{task_id}",headers=stranger).status_code==404
    assert client.put(f"/api/me/tasks/{task_id}",headers=stranger,json=payload(title="Hijack")).status_code==404
    assert client.delete(f"/api/me/tasks/{task_id}",headers=stranger).status_code==404

def test_task_filters_summary_validation_and_authentication():
    h=student_headers()
    client.post("/api/me/tasks",headers=h,json=payload(title="Open algebra",category="Study"))
    client.post("/api/me/tasks",headers=h,json=payload(title="Late physics",category=None,due_date=(date.today()-timedelta(days=1)).isoformat()))
    client.post("/api/me/tasks",headers=h,json=payload(title="Finished reading",category="Reading",completed=True))
    assert [x["title"] for x in client.get("/api/me/tasks?status=overdue",headers=h).json()]==["Late physics"]
    assert [x["title"] for x in client.get("/api/me/tasks?status=completed",headers=h).json()]==["Finished reading"]
    assert [x["title"] for x in client.get("/api/me/tasks?uncategorized=true",headers=h).json()]==["Late physics"]
    assert [x["title"] for x in client.get("/api/me/tasks?q=algebra&category=Study",headers=h).json()]==["Open algebra"]
    summary=client.get("/api/me/tasks/summary",headers=h).json()
    assert (summary["open_count"],summary["overdue_count"],summary["completed_count"],summary["uncategorized_count"])==(1,1,1,1)
    assert summary["categories"]==["Reading","Study"]
    assert client.post("/api/me/tasks",headers=h,json=payload(title="   ")).status_code==422
    assert client.post("/api/me/tasks",headers=h,json=payload(owner_account_id=999)).status_code==422
    assert client.get("/api/me/tasks").status_code==401
