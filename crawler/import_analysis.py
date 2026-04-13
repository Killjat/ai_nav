"""将 analyzed.json 的结果更新回数据库"""
import json, sys
sys.path.append("..")

from backend.database import SessionLocal, engine
from backend.models import Base, Site

Base.metadata.create_all(bind=engine)


def import_analysis(filepath: str = "analyzed.json"):
    with open(filepath) as f:
        data = json.load(f)

    db = SessionLocal()
    updated = 0
    for item in data:
        site = db.query(Site).filter(Site.url == item["url"]).first()
        if not site:
            continue
        site.has_api     = item.get("has_api", False)
        site.api_paths   = item.get("api_paths", [])
        site.swagger_url = item.get("swagger_url", "")
        site.confidence  = item.get("confidence", "low")
        updated += 1

    db.commit()
    db.close()
    print(f"更新了 {updated} 条记录")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "analyzed.json"
    import_analysis(path)
