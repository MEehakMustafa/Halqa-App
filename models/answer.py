from sqlalchemy import Column, Integer, Boolean, Text, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class QuestionAnswer(Base):
    """One row per member per question; re-answering updates the row
    and sets edited_at (enforced by the unique constraint)."""

    __tablename__ = "question_answers"
    __table_args__ = (
        UniqueConstraint("question_id", "user_id", name="uq_answer_question_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("halaqa_questions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    answer = Column(Boolean, nullable=False)
    reflection = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    edited_at = Column(DateTime(timezone=True), nullable=True)

    question = relationship("HalaqaQuestion", back_populates="answers")
    user = relationship("User")

    @property
    def user_name(self) -> str:
        return self.user.name
