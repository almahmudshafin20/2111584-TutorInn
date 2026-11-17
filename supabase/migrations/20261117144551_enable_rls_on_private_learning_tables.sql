-- TutorInn browser clients must use the FastAPI/JWT API, not the Supabase Data API.
-- Keep these tables private to the trusted backend service; intentionally add no browser policies.
ALTER TABLE public.personal_learning_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learning_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learning_group_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.group_learning_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.group_task_assignments ENABLE ROW LEVEL SECURITY;

REVOKE ALL PRIVILEGES ON TABLE
  public.personal_learning_tasks,
  public.learning_groups,
  public.learning_group_members,
  public.group_learning_tasks,
  public.group_task_assignments
FROM PUBLIC, anon, authenticated;

REVOKE ALL PRIVILEGES ON SEQUENCE
  public.personal_learning_tasks_id_seq,
  public.learning_groups_id_seq,
  public.learning_group_members_id_seq,
  public.group_learning_tasks_id_seq,
  public.group_task_assignments_id_seq
FROM PUBLIC, anon, authenticated;
