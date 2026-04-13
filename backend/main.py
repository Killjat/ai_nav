from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
from .database import engine, get_db
from .models import Base, Site

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI生图导航")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def site_to_dict(s: Site) -> dict:
    return {
        "id": s.id,
        "url": s.url,
        "title": s.title or s.url,
        "description": s.description,
        "screenshot": s.screenshot,
        "features": {
            "text_to_image": s.text_to_image,
            "image_edit": s.image_edit,
            "video_gen": s.video_gen,
        },
        "api": {
            "has_api": s.has_api,
            "api_paths": s.api_paths or [],
            "swagger_url": s.swagger_url or "",
        },
        "confidence": s.confidence or "low",
        "is_active": s.is_active,
        "is_free": s.is_free,
        "tags": s.tags or [],
        "last_checked": s.last_checked.isoformat() if s.last_checked else None,
    }


@app.get("/api/sites")
def list_sites(
    feature: Optional[str] = Query(None, description="text_to_image | image_edit | video_gen"),
    has_api: Optional[bool] = Query(None, description="只看有开放 API 的站点"),
    confidence: Optional[str] = Query(None, description="high | medium | low"),
    free_only: bool = False,
    db: Session = Depends(get_db),
):
    q = db.query(Site).filter(Site.is_active == True)
    if feature == "text_to_image":
        q = q.filter(Site.text_to_image == True)
    elif feature == "image_edit":
        q = q.filter(Site.image_edit == True)
    elif feature == "video_gen":
        q = q.filter(Site.video_gen == True)
    if has_api is True:
        q = q.filter(Site.has_api == True)
    if confidence:
        q = q.filter(Site.confidence == confidence)
    if free_only:
        q = q.filter(Site.is_free == True)
    return [site_to_dict(s) for s in q.all()]


@app.get("/api/sites/{site_id}")
def get_site(site_id: int, db: Session = Depends(get_db)):
    s = db.query(Site).filter(Site.id == site_id).first()
    if not s:
        from fastapi import HTTPException
        raise HTTPException(404, "not found")
    return site_to_dict(s)


@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    total = db.query(Site).filter(Site.is_active == True).count()
    return {
        "total": total,
        "text_to_image": db.query(Site).filter(Site.text_to_image == True, Site.is_active == True).count(),
        "image_edit": db.query(Site).filter(Site.image_edit == True, Site.is_active == True).count(),
        "video_gen": db.query(Site).filter(Site.video_gen == True, Site.is_active == True).count(),
    }
