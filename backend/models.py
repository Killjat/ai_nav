from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from datetime import datetime
from .database import Base

class Site(Base):
    __tablename__ = "sites"

    id          = Column(Integer, primary_key=True, index=True)
    url         = Column(String, unique=True, index=True)
    title       = Column(String, default="")
    description = Column(String, default="")
    screenshot  = Column(String, default="")   # 截图路径或 base64

    # 功能标签
    text_to_image = Column(Boolean, default=False)
    image_edit    = Column(Boolean, default=False)
    video_gen     = Column(Boolean, default=False)

    # 状态
    is_active  = Column(Boolean, default=True)   # 是否在线
    is_free    = Column(Boolean, default=True)   # 是否免费
    tags       = Column(JSON, default=list)      # 额外标签

    last_checked = Column(DateTime, default=datetime.utcnow)
    created_at   = Column(DateTime, default=datetime.utcnow)
