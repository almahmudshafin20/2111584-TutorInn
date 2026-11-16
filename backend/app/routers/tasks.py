from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from ..auth import require_roles
from ..database import get_db
from ..models import PersonalLearningTask, UserAccount
from ..schemas import PersonalTaskInput, PersonalTaskRead, PersonalTaskSummaryRead

router = APIRouter(prefix="/api/me/tasks", tags=["Personal learning tasks"])

def _owned_task(task_id: int, account: UserAccount, db: Session) -> PersonalLearningTask:
    task = db.scalar(select(PersonalLearningTask).where(
        PersonalLearningTask.id == task_id, PersonalLearningTask.owner_account_id == account.id
    ))
    if task is None:
        raise HTTPException(status_code=404, detail="Personal task not found.")
    return task

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

@router.get("/summary", response_model=PersonalTaskSummaryRead)
def personal_task_summary(account: UserAccount = Depends(require_roles("student", "tutor")), db: Session = Depends(get_db)) -> dict:
    tasks = list(db.scalars(select(PersonalLearningTask).where(PersonalLearningTask.owner_account_id == account.id)).all())
    today = date.today()
    completed = sum(task.completed for task in tasks)
    overdue = sum(not task.completed and task.due_date is not None and task.due_date < today for task in tasks)
    categories = sorted({task.category for task in tasks if task.category}, key=str.casefold)
    return {"total_count":len(tasks),"open_count":len(tasks)-completed-overdue,"completed_count":completed,
            "overdue_count":overdue,"uncategorized_count":sum(task.category is None for task in tasks),"categories":categories}

@router.get("", response_model=list[PersonalTaskRead])
def list_personal_tasks(
    q: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, max_length=60),
    uncategorized: bool = False,
    task_status: str | None = Query(default=None, alias="status", pattern="^(open|completed|overdue)$"),
    account: UserAccount = Depends(require_roles("student", "tutor")), db: Session = Depends(get_db),
) -> list[PersonalLearningTask]:
    if category and uncategorized:
        raise HTTPException(status_code=422, detail="Choose a category or uncategorized tasks, not both.")
    statement = select(PersonalLearningTask).where(PersonalLearningTask.owner_account_id == account.id)
    if q and q.strip():
        needle=f"%{q.strip()}%"
        statement=statement.where(or_(PersonalLearningTask.title.ilike(needle),PersonalLearningTask.description.ilike(needle)))
    if category and category.strip():
        statement=statement.where(func.lower(PersonalLearningTask.category)==category.strip().casefold())
    if uncategorized:
        statement=statement.where(PersonalLearningTask.category.is_(None))
    today=date.today()
    if task_status=="completed":
        statement=statement.where(PersonalLearningTask.completed.is_(True))
    elif task_status=="overdue":
        statement=statement.where(PersonalLearningTask.completed.is_(False),PersonalLearningTask.due_date.is_not(None),PersonalLearningTask.due_date<today)
    elif task_status=="open":
        statement=statement.where(PersonalLearningTask.completed.is_(False),or_(PersonalLearningTask.due_date.is_(None),PersonalLearningTask.due_date>=today))
    return list(db.scalars(statement.order_by(PersonalLearningTask.completed.asc(),PersonalLearningTask.due_date.asc(),PersonalLearningTask.created_at.desc())).all())

@router.post("", response_model=PersonalTaskRead, status_code=status.HTTP_201_CREATED)
def create_personal_task(payload: PersonalTaskInput, account: UserAccount = Depends(require_roles("student","tutor")), db: Session = Depends(get_db)) -> PersonalLearningTask:
    now=_now()
    task=PersonalLearningTask(owner_account_id=account.id,title=payload.title,description=payload.description,category=payload.category,
        due_date=payload.due_date,completed=payload.completed,created_at=now,updated_at=now)
    db.add(task); db.commit(); db.refresh(task)
    return task

@router.get("/{task_id}", response_model=PersonalTaskRead)
def get_personal_task(task_id:int, account:UserAccount=Depends(require_roles("student","tutor")), db:Session=Depends(get_db))->PersonalLearningTask:
    return _owned_task(task_id,account,db)

@router.put("/{task_id}", response_model=PersonalTaskRead)
def update_personal_task(task_id:int,payload:PersonalTaskInput,account:UserAccount=Depends(require_roles("student","tutor")),db:Session=Depends(get_db))->PersonalLearningTask:
    task=_owned_task(task_id,account,db)
    task.title=payload.title; task.description=payload.description; task.category=payload.category
    task.due_date=payload.due_date; task.completed=payload.completed; task.updated_at=_now()
    db.commit(); db.refresh(task)
    return task

@router.delete("/{task_id}",status_code=status.HTTP_204_NO_CONTENT)
def delete_personal_task(task_id:int,account:UserAccount=Depends(require_roles("student","tutor")),db:Session=Depends(get_db))->Response:
    task=_owned_task(task_id,account,db); db.delete(task); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
