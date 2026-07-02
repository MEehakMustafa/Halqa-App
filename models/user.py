from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    timezone = Column(
        String, nullable=False, default="Asia/Karachi", server_default="Asia/Karachi"
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    halaqas = relationship("Halaqa", back_populates="creator")
    memberships = relationship("Membership", back_populates="user")
