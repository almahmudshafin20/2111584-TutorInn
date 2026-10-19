from sqlmodel import Field, SQLModel


class Student(SQLModel, table=True):
    __tablename__ = "students"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str
    education_level: str
    bio: str | None = None
