from sqlmodel import Field, SQLModel


class Tutor(SQLModel, table=True):
    __tablename__ = "tutors"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str
    subject: str
    teaching_level: str
    experience: int
    bio: str | None = None
    availability: str | None = None
