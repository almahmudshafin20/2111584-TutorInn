from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..auth import record_activity_event, require_roles
from ..database import get_db
from ..models import (
    GroupLearningTask, GroupTaskAssignment, LearningGroup, LearningGroupMember,
    Student, UserAccount,
)
from ..schemas import (
    GroupMemberCreate, GroupMemberPermissions, GroupTaskAssignmentInput,
    GroupTaskCompletionInput, GroupTaskCreate, GroupTaskRead, GroupMemberRead,
    LearningGroupCreate, LearningGroupRead, LearningGroupUpdate,
)

router = APIRouter(prefix="/api/groups", tags=["Group learning and assignments"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _group(group_id: int, db: Session) -> LearningGroup:
    group = db.get(LearningGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Learning group not found.")
    return group


def _owner(group: LearningGroup, account: UserAccount) -> None:
    if group.owner_account_id != account.id:
        raise HTTPException(status_code=403, detail="Only the group owner can perform this action.")


def _member(group: LearningGroup, account: UserAccount, db: Session) -> LearningGroupMember:
    membership = db.scalar(select(LearningGroupMember).where(
        LearningGroupMember.group_id == group.id,
        LearningGroupMember.student_account_id == account.id,
    ))
    if membership is None:
        raise HTTPException(status_code=404, detail="Learning group not found.")
    return membership


def _can(group: LearningGroup, account: UserAccount, db: Session, permission: str) -> None:
    if group.owner_account_id == account.id:
        return
    member = _member(group, account, db)
    if not getattr(member, permission):
        raise HTTPException(status_code=403, detail=f"The group owner has not enabled permission: {permission.replace('can_', '').replace('_', ' ')}.")


def _task(group: LearningGroup, task_id: int, db: Session) -> GroupLearningTask:
    task = db.scalar(select(GroupLearningTask).where(
        GroupLearningTask.id == task_id, GroupLearningTask.group_id == group.id
    ))
    if task is None:
        raise HTTPException(status_code=404, detail="Group task not found.")
    return task


def _member_read(member: LearningGroupMember, db: Session, *, include_email: bool = True) -> GroupMemberRead:
    account = db.get(UserAccount, member.student_account_id)
    profile = db.scalar(select(Student).where(Student.account_id == member.student_account_id))
    return GroupMemberRead(
        account_id=member.student_account_id,
        full_name=profile.full_name if profile else (account.email if account else "Student"),
        email=account.email if include_email and account else "",
        can_create_tasks=member.can_create_tasks,
        can_edit_tasks=member.can_edit_tasks,
        can_assign_tasks=member.can_assign_tasks,
        joined_at=member.joined_at,
    )


def _task_read(task: GroupLearningTask, db: Session, *, viewer_id: int | None = None) -> GroupTaskRead:
    assignments = list(db.scalars(select(GroupTaskAssignment).where(
        GroupTaskAssignment.task_id == task.id
    )).all())
    rows=[]
    for assignment in assignments:
        account=db.get(UserAccount, assignment.student_account_id)
        profile=db.scalar(select(Student).where(Student.account_id == assignment.student_account_id))
        if viewer_id is not None and assignment.student_account_id != viewer_id:
            continue
        rows.append({
            "id":assignment.id,"student_account_id":assignment.student_account_id,
            "student_name":profile.full_name if profile else (account.email if account else "Student"),
            "completed":assignment.completed,"assigned_at":assignment.assigned_at,
            "completed_at":assignment.completed_at,
        })
    return GroupTaskRead(
        id=task.id,group_id=task.group_id,created_by_account_id=task.created_by_account_id,
        title=task.title,description=task.description,video_url=task.video_url,due_date=task.due_date,
        created_at=task.created_at,updated_at=task.updated_at,assignments=rows,
    )


def _group_read(group: LearningGroup, account: UserAccount, db: Session) -> LearningGroupRead:
    is_owner=group.owner_account_id==account.id
    membership=None if is_owner else _member(group,account,db)
    members=list(db.scalars(select(LearningGroupMember).where(
        LearningGroupMember.group_id==group.id
    ).order_by(LearningGroupMember.joined_at.asc())).all())
    tasks=list(db.scalars(select(GroupLearningTask).where(
        GroupLearningTask.group_id==group.id
    ).order_by(GroupLearningTask.created_at.desc())).all())
    return LearningGroupRead(
        id=group.id,owner_account_id=group.owner_account_id,name=group.name,
        description=group.description,created_at=group.created_at,updated_at=group.updated_at,
        member_count=len(members),task_count=len(tasks),is_owner=is_owner,
        my_permissions=GroupMemberPermissions(
            can_create_tasks=True if is_owner else membership.can_create_tasks,
            can_edit_tasks=True if is_owner else membership.can_edit_tasks,
            can_assign_tasks=True if is_owner else membership.can_assign_tasks,
        ),
        members=[_member_read(m,db,include_email=is_owner) for m in members],
        tasks=[
            _task_read(t,db,viewer_id=None if is_owner else account.id)
            for t in tasks
            if is_owner or t.created_by_account_id == account.id or membership.can_assign_tasks or membership.can_edit_tasks or db.scalar(select(GroupTaskAssignment.id).where(
                GroupTaskAssignment.task_id == t.id,
                GroupTaskAssignment.student_account_id == account.id,
            )) is not None
        ],
    )


@router.get("", response_model=list[LearningGroupRead])
def list_groups(account: UserAccount = Depends(require_roles("student","tutor")), db: Session = Depends(get_db)):
    if account.role=="tutor":
        groups=list(db.scalars(select(LearningGroup).where(
            LearningGroup.owner_account_id==account.id
        ).order_by(LearningGroup.updated_at.desc())).all())
    else:
        ids=select(LearningGroupMember.group_id).where(LearningGroupMember.student_account_id==account.id)
        groups=list(db.scalars(select(LearningGroup).where(LearningGroup.id.in_(ids)).order_by(LearningGroup.updated_at.desc())).all())
    return [_group_read(group,account,db) for group in groups]


@router.post("", response_model=LearningGroupRead, status_code=status.HTTP_201_CREATED)
def create_group(payload: LearningGroupCreate, request: Request, account: UserAccount = Depends(require_roles("tutor")), db: Session = Depends(get_db)):
    now=_now()
    group=LearningGroup(owner_account_id=account.id,name=payload.name,description=payload.description,created_at=now,updated_at=now)
    db.add(group);db.commit();db.refresh(group)
    record_activity_event(db, request, actor_account_id=account.id, actor_role=account.role, action="learning_group_created", target_type="learning_group", target_id=group.id)
    return _group_read(group,account,db)


@router.get("/{group_id}", response_model=LearningGroupRead)
def get_group(group_id:int, account:UserAccount=Depends(require_roles("student","tutor")), db:Session=Depends(get_db)):
    group=_group(group_id,db)
    if group.owner_account_id!=account.id:
        _member(group,account,db)
    return _group_read(group,account,db)


@router.put("/{group_id}", response_model=LearningGroupRead)
def update_group(group_id:int,payload:LearningGroupUpdate,request:Request,account:UserAccount=Depends(require_roles("tutor")),db:Session=Depends(get_db)):
    group=_group(group_id,db);_owner(group,account)
    group.name=payload.name;group.description=payload.description;group.updated_at=_now()
    db.commit();db.refresh(group)
    record_activity_event(db, request, actor_account_id=account.id, actor_role=account.role, action="learning_group_updated", target_type="learning_group", target_id=group.id)
    return _group_read(group,account,db)


@router.post("/{group_id}/members",response_model=LearningGroupRead,status_code=status.HTTP_201_CREATED)
def add_member(group_id:int,payload:GroupMemberCreate,request:Request,account:UserAccount=Depends(require_roles("tutor")),db:Session=Depends(get_db)):
    group=_group(group_id,db);_owner(group,account)
    student_account=db.scalar(select(UserAccount).where(
        UserAccount.email==payload.student_email,UserAccount.role=="student",UserAccount.status=="active"
    ))
    if student_account is None or db.scalar(select(Student.id).where(Student.account_id==student_account.id)) is None:
        raise HTTPException(status_code=404,detail="No active Student account was found for that email.")
    exists=db.scalar(select(LearningGroupMember.id).where(
        LearningGroupMember.group_id==group.id,LearningGroupMember.student_account_id==student_account.id
    ))
    if exists:
        raise HTTPException(status_code=409,detail="This Student is already in the group.")
    db.add(LearningGroupMember(group_id=group.id,student_account_id=student_account.id,joined_at=_now()))
    group.updated_at=_now();db.commit();db.refresh(group)
    record_activity_event(db, request, actor_account_id=account.id, actor_role=account.role, action="group_member_added", target_type="group_member", target_id=student_account.id, details=f"group_id={group.id}")
    return _group_read(group,account,db)


@router.delete("/{group_id}/members/{student_account_id}",status_code=status.HTTP_204_NO_CONTENT)
def remove_member(group_id:int,student_account_id:int,request:Request,account:UserAccount=Depends(require_roles("tutor")),db:Session=Depends(get_db)):
    group=_group(group_id,db);_owner(group,account)
    member=db.scalar(select(LearningGroupMember).where(
        LearningGroupMember.group_id==group.id,LearningGroupMember.student_account_id==student_account_id
    ))
    if member is None: raise HTTPException(status_code=404,detail="Group member not found.")
    db.delete(member)
    # Removing membership also removes that Student's group-task assignments.
    task_ids=select(GroupLearningTask.id).where(GroupLearningTask.group_id==group.id)
    for assignment in list(db.scalars(select(GroupTaskAssignment).where(
        GroupTaskAssignment.task_id.in_(task_ids),GroupTaskAssignment.student_account_id==student_account_id
    )).all()):
        db.delete(assignment)
    group.updated_at=_now();db.commit()
    record_activity_event(db, request, actor_account_id=account.id, actor_role=account.role, action="group_member_removed", target_type="group_member", target_id=student_account_id, details=f"group_id={group.id}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{group_id}/members/{student_account_id}/permissions",response_model=LearningGroupRead)
def set_member_permissions(group_id:int,student_account_id:int,payload:GroupMemberPermissions,request:Request,account:UserAccount=Depends(require_roles("tutor")),db:Session=Depends(get_db)):
    group=_group(group_id,db);_owner(group,account)
    member=db.scalar(select(LearningGroupMember).where(
        LearningGroupMember.group_id==group.id,LearningGroupMember.student_account_id==student_account_id
    ))
    if member is None: raise HTTPException(status_code=404,detail="Group member not found.")
    member.can_create_tasks=payload.can_create_tasks
    member.can_edit_tasks=payload.can_edit_tasks
    member.can_assign_tasks=payload.can_assign_tasks
    group.updated_at=_now();db.commit();db.refresh(group)
    record_activity_event(db, request, actor_account_id=account.id, actor_role=account.role, action="group_member_permissions_updated", target_type="group_member", target_id=student_account_id, details=f"group_id={group.id}; create={member.can_create_tasks}; edit={member.can_edit_tasks}; assign={member.can_assign_tasks}")
    return _group_read(group,account,db)


@router.post("/{group_id}/tasks",response_model=GroupTaskRead,status_code=status.HTTP_201_CREATED)
def create_group_task(group_id:int,payload:GroupTaskCreate,request:Request,account:UserAccount=Depends(require_roles("student","tutor")),db:Session=Depends(get_db)):
    group=_group(group_id,db);_can(group,account,db,"can_create_tasks")
    now=_now()
    task=GroupLearningTask(group_id=group.id,created_by_account_id=account.id,title=payload.title,description=payload.description,video_url=payload.video_url,due_date=payload.due_date,created_at=now,updated_at=now)
    db.add(task);group.updated_at=now;db.commit();db.refresh(task)
    record_activity_event(db, request, actor_account_id=account.id, actor_role=account.role, action="group_task_created", target_type="group_task", target_id=task.id, details=f"group_id={group.id}")
    return _task_read(task,db,viewer_id=None if group.owner_account_id==account.id else account.id)


@router.put("/{group_id}/tasks/{task_id}",response_model=GroupTaskRead)
def update_group_task(group_id:int,task_id:int,payload:GroupTaskCreate,request:Request,account:UserAccount=Depends(require_roles("student","tutor")),db:Session=Depends(get_db)):
    group=_group(group_id,db);_can(group,account,db,"can_edit_tasks")
    task=_task(group,task_id,db)
    task.title=payload.title;task.description=payload.description;task.video_url=payload.video_url;task.due_date=payload.due_date;task.updated_at=_now()
    db.commit();db.refresh(task)
    record_activity_event(db, request, actor_account_id=account.id, actor_role=account.role, action="group_task_updated", target_type="group_task", target_id=task.id, details=f"group_id={group.id}")
    return _task_read(task,db,viewer_id=None if group.owner_account_id==account.id else account.id)


@router.delete("/{group_id}/tasks/{task_id}",status_code=status.HTTP_204_NO_CONTENT)
def delete_group_task(group_id:int,task_id:int,request:Request,account:UserAccount=Depends(require_roles("tutor")),db:Session=Depends(get_db)):
    group=_group(group_id,db);_owner(group,account)
    task=_task(group,task_id,db)
    # Explicitly clear child rows as well as relying on database ON DELETE CASCADE.
    # This keeps SQLite test environments consistent when FK enforcement is disabled.
    for assignment in list(db.scalars(select(GroupTaskAssignment).where(GroupTaskAssignment.task_id==task.id)).all()):
        db.delete(assignment)
    db.delete(task);db.commit()
    record_activity_event(db, request, actor_account_id=account.id, actor_role=account.role, action="group_task_deleted", target_type="group_task", target_id=task_id, details=f"group_id={group.id}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{group_id}/tasks/{task_id}/assignments",response_model=GroupTaskRead)
def assign_group_task(group_id:int,task_id:int,payload:GroupTaskAssignmentInput,request:Request,account:UserAccount=Depends(require_roles("student","tutor")),db:Session=Depends(get_db)):
    group=_group(group_id,db);_can(group,account,db,"can_assign_tasks")
    task=_task(group,task_id,db)
    if payload.all_members and payload.student_account_ids:
        raise HTTPException(status_code=422,detail="Choose all members or a selected list, not both.")
    if payload.all_members:
        student_ids=list(db.scalars(select(LearningGroupMember.student_account_id).where(LearningGroupMember.group_id==group.id)).all())
    else:
        student_ids=payload.student_account_ids
    if not student_ids:
        raise HTTPException(status_code=422,detail="Select at least one group member.")
    valid=set(db.scalars(select(LearningGroupMember.student_account_id).where(
        LearningGroupMember.group_id==group.id,LearningGroupMember.student_account_id.in_(student_ids)
    )).all())
    if valid!=set(student_ids):
        raise HTTPException(status_code=422,detail="Assignments can only target current members of this group.")
    existing=set(db.scalars(select(GroupTaskAssignment.student_account_id).where(GroupTaskAssignment.task_id==task.id)).all())
    now=_now()
    for student_id in student_ids:
        if student_id not in existing:
            db.add(GroupTaskAssignment(task_id=task.id,student_account_id=student_id,assigned_at=now))
    task.updated_at=now;db.commit();db.refresh(task)
    record_activity_event(db, request, actor_account_id=account.id, actor_role=account.role, action="group_task_assigned", target_type="group_task", target_id=task.id, details=f"group_id={group.id}; assigned_member_count={len(student_ids)}")
    return _task_read(task,db,viewer_id=None if group.owner_account_id==account.id else account.id)


@router.patch("/{group_id}/tasks/{task_id}/completion",response_model=GroupTaskRead)
def update_assignment_completion(group_id:int,task_id:int,payload:GroupTaskCompletionInput,request:Request,account:UserAccount=Depends(require_roles("student")),db:Session=Depends(get_db)):
    group=_group(group_id,db);_member(group,account,db)
    task=_task(group,task_id,db)
    assignment=db.scalar(select(GroupTaskAssignment).where(
        GroupTaskAssignment.task_id==task.id,GroupTaskAssignment.student_account_id==account.id
    ))
    if assignment is None:
        raise HTTPException(status_code=404,detail="This task is not assigned to your account.")
    assignment.completed=payload.completed
    assignment.completed_at=_now() if payload.completed else None
    db.commit();db.refresh(task)
    record_activity_event(db, request, actor_account_id=account.id, actor_role=account.role, action="group_assignment_completion_updated", target_type="group_task_assignment", target_id=assignment.id, details=f"group_id={group.id}; task_id={task.id}; completed={assignment.completed}")
    return _task_read(task,db,viewer_id=account.id)
