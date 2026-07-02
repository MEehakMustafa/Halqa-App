from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Halaqa(Base):
    __tablename__ = "halaqas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_private = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    creator = relationship("User", back_populates="halaqas")
    memberships = relationship("Membership", back_populates="halaqa")

    @property
    def member_count(self) -> int:
        return len(self.memberships)

    @property
    def creator_name(self) -> str:
        return self.creator.name
