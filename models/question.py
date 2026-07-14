from sqlalchemy import Column, Integer, Text, Date, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class HalaqaQuestion(Base):
    """Daily accountability question for a halaqa. active_date is fixed at
    creation (the admin's "today") — members answer against that date."""

    __tablename__ = "halaqa_questions"
    __table_args__ = (
        UniqueConstraint("halaqa_id", "active_date", name="uq_question_halaqa_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    halaqa_id = Column(Integer, ForeignKey("halaqas.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    active_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    halaqa = relationship("Halaqa")
    creator = relationship("User")
    answers = relationship(
        "QuestionAnswer", back_populates="question", cascade="all, delete-orphan"
    )

    @property
    def creator_name(self) -> str:
        return self.creator.name
