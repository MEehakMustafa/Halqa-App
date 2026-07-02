from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    halaqa_id = Column(Integer, ForeignKey("halaqas.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    author = relationship("User")
    halaqa = relationship("Halaqa")
    comments = relationship(
        "Comment", back_populates="post", order_by="Comment.created_at"
    )

    @property
    def author_name(self) -> str:
        return self.author.name

    @property
    def halaqa_name(self) -> str:
        return self.halaqa.name

    @property
    def comment_count(self) -> int:
        return len(self.comments)
