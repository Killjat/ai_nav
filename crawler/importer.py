"""
将 checked.json 导入数据库，只保留有功能的站点
"""
import json, sys
from datetime import datetime
sys.path.append("..")

from backend.database import SessionLocal, engine
from backend.models import Base, Site

Base.metadata.create_all(bind=engine)


def import_results(filepath: str = "checked.json"):
    with open(filepath) as f:
        data = json.load(f)

    db = SessionLocal()
    added = 0
    for item in data:
        # 过滤：必须在线且至少有一个功能
        if not item["is_active"]:
            continue
        if not any([item["text_to_image"], item["image_edit"], item["video_gen"]]):
            continue

        site_data = {k: v for k, v in item.items() if hasattr(Site, k)}
        # 字符串转 datetime
        if isinstance(site_data.get("last_checked"), str):
            site_data["last_checked"] = datetime.fromisoformat(site_data["last_checked"])

        existing = db.query(Site).filter(Site.url == item["url"]).first()
        if existing:
            for k, v in site_data.items():
                setattr(existing, k, v)
        else:
            db.add(Site(**site_data))
            added += 1

    db.commit()
    db.close()
    print(f"导入完成，新增 {added} 条")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "checked.json"
    import_results(path)
