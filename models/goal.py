from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    halaqa_id = Column(Integer, ForeignKey("halaqas.id"), nullable=True)  # null = personal goal
    is_private = Column(Boolean, default=False, nullable=False)
    target_days = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User")
    halaqa = relationship("Halaqa")
    checkins = relationship(
        "CheckIn", back_populates="goal", cascade="all, delete-orphan"
    )

    @property
    def owner_name(self) -> str:
        return self.owner.name
