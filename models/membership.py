from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "halaqa_id", name="uq_membership_user_halaqa"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    halaqa_id = Column(Integer, ForeignKey("halaqas.id"), nullable=False)
    role = Column(String, default="member", nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="memberships")
    halaqa = relationship("Halaqa", back_populates="memberships")

    @property
    def name(self) -> str:
        return self.user.name
