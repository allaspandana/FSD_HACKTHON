from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
import json
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import String, Text, Date, DateTime, Boolean, Integer, ForeignKey, func, or_
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session
from .database import Base, engine, get_db

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

class Mistake(Base):
    __tablename__ = "mistakes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    language: Mapped[str] = mapped_column(String(60), nullable=False)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    incorrect_code: Mapped[str] = mapped_column(Text, default="")
    corrected_code: Mapped[str] = mapped_column(Text, default="")
    explanation: Mapped[str] = mapped_column(Text, default="")
    root_cause: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[str] = mapped_column(String(20), default="Medium")
    tags: Mapped[str] = mapped_column(Text, default="")  # comma-separated
    recorded_on: Mapped[date] = mapped_column(Date, default=date.today)
    next_revision: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviews: Mapped[list["Review"]] = relationship(back_populates="mistake", cascade="all, delete-orphan")

class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mistake_id: Mapped[int] = mapped_column(ForeignKey("mistakes.id", ondelete="CASCADE"), nullable=False)
    reviewed_on: Mapped[date] = mapped_column(Date, default=date.today)
    note: Mapped[str] = mapped_column(Text, default="")
    mistake: Mapped[Mistake] = relationship(back_populates="reviews")

Base.metadata.create_all(bind=engine)

class MistakeIn(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    language: str = Field(min_length=1, max_length=60)
    topic: str = Field(min_length=1, max_length=100)
    error_message: str = Field(min_length=2)
    incorrect_code: str = ""
    corrected_code: str = ""
    explanation: str = ""
    root_cause: str = ""
    difficulty: str = "Medium"
    tags: str = ""
    recorded_on: date = Field(default_factory=date.today)
    next_revision: Optional[date] = None

class MistakeUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=160)
    language: Optional[str] = None
    topic: Optional[str] = None
    error_message: Optional[str] = None
    incorrect_code: Optional[str] = None
    corrected_code: Optional[str] = None
    explanation: Optional[str] = None
    root_cause: Optional[str] = None
    difficulty: Optional[str] = None
    tags: Optional[str] = None
    recorded_on: Optional[date] = None
    next_revision: Optional[date] = None

class ReviewIn(BaseModel):
    note: str = ""

def serialize(m: Mistake):
    return {
        "id": m.id, "title": m.title, "language": m.language, "topic": m.topic,
        "error_message": m.error_message, "incorrect_code": m.incorrect_code,
        "corrected_code": m.corrected_code, "explanation": m.explanation,
        "root_cause": m.root_cause, "difficulty": m.difficulty,
        "tags": m.tags, "recorded_on": m.recorded_on.isoformat(),
        "next_revision": m.next_revision.isoformat() if m.next_revision else None,
        "reviewed": m.reviewed, "is_sample": m.is_sample,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "review_history": [{"id": r.id, "reviewed_on": r.reviewed_on.isoformat(), "note": r.note} for r in sorted(m.reviews, key=lambda x: x.reviewed_on, reverse=True)]
    }

def require_mistake(db: Session, mistake_id: int):
    item = db.get(Mistake, mistake_id)
    if not item:
        raise HTTPException(status_code=404, detail="Mistake not found")
    return item

app = FastAPI(title="BugDiary API", version="1.0.0", description="Personal coding mistake journal")
app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(FRONTEND / "index.html")

@app.get("/api/health")
def health():
    return {"status": "ok", "app": "BugDiary"}

@app.post("/api/mistakes", status_code=201)
def create_mistake(payload: MistakeIn, db: Session = Depends(get_db)):
    data = payload.model_dump()
    if data["difficulty"] not in {"Easy", "Medium", "Hard"}:
        raise HTTPException(status_code=422, detail="Difficulty must be Easy, Medium, or Hard")
    item = Mistake(**data)
    db.add(item); db.commit(); db.refresh(item)
    return serialize(item)

@app.get("/api/mistakes")
def list_mistakes(
    search: str = Query(default=""),
    language: str = Query(default=""),
    topic: str = Query(default=""),
    difficulty: str = Query(default=""),
    tag: str = Query(default=""),
    revision: str = Query(default=""),
    db: Session = Depends(get_db)
):
    q = db.query(Mistake)
    if search:
        like = f"%{search.strip()}%"
        q = q.filter(or_(Mistake.title.ilike(like), Mistake.error_message.ilike(like),
                         Mistake.language.ilike(like), Mistake.topic.ilike(like), Mistake.tags.ilike(like)))
    if language: q = q.filter(Mistake.language == language)
    if topic: q = q.filter(Mistake.topic == topic)
    if difficulty: q = q.filter(Mistake.difficulty == difficulty)
    if tag: q = q.filter(Mistake.tags.ilike(f"%{tag}%"))
    today = date.today()
    if revision == "pending": q = q.filter(Mistake.reviewed == False)
    elif revision == "due": q = q.filter(Mistake.reviewed == False, Mistake.next_revision != None, Mistake.next_revision <= today)
    elif revision == "completed": q = q.filter(Mistake.reviewed == True)
    return [serialize(m) for m in q.order_by(Mistake.created_at.desc()).all()]

@app.get("/api/mistakes/{mistake_id}")
def get_mistake(mistake_id: int, db: Session = Depends(get_db)):
    return serialize(require_mistake(db, mistake_id))

@app.put("/api/mistakes/{mistake_id}")
def update_mistake(mistake_id: int, payload: MistakeUpdate, db: Session = Depends(get_db)):
    item = require_mistake(db, mistake_id)
    data = payload.model_dump(exclude_unset=True)
    if "difficulty" in data and data["difficulty"] not in {"Easy", "Medium", "Hard"}:
        raise HTTPException(status_code=422, detail="Difficulty must be Easy, Medium, or Hard")
    for key, value in data.items():
        setattr(item, key, value)
    db.commit(); db.refresh(item)
    return serialize(item)

@app.delete("/api/mistakes/{mistake_id}")
def delete_mistake(mistake_id: int, db: Session = Depends(get_db)):
    item = require_mistake(db, mistake_id)
    db.delete(item); db.commit()
    return {"message": "Mistake deleted", "id": mistake_id}

@app.post("/api/mistakes/{mistake_id}/review")
def review_mistake(mistake_id: int, payload: ReviewIn, db: Session = Depends(get_db)):
    item = require_mistake(db, mistake_id)
    item.reviewed = True
    db.add(Review(mistake_id=item.id, note=payload.note.strip()))
    db.commit(); db.refresh(item)
    return serialize(item)

@app.post("/api/mistakes/{mistake_id}/schedule")
def schedule_revision(mistake_id: int, next_revision: date = Query(...), db: Session = Depends(get_db)):
    item = require_mistake(db, mistake_id)
    item.next_revision = next_revision
    item.reviewed = False
    db.commit(); db.refresh(item)
    return serialize(item)

@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    items = db.query(Mistake).all()
    today = date.today()
    pending = [m for m in items if not m.reviewed]
    due = [m for m in pending if m.next_revision and m.next_revision <= today]
    by_language, by_topic, repeated = {}, {}, {}
    for m in items:
        by_language[m.language] = by_language.get(m.language, 0) + 1
        by_topic[m.topic] = by_topic.get(m.topic, 0) + 1
        # Transparent category key: topic + normalized error message.
        key = " ".join(m.error_message.lower().split())[:100]
        repeated[key] = repeated.get(key, {"count": 0, "topic": m.topic, "message": m.error_message})
        repeated[key]["count"] += 1
    common = sorted([{"message": v["message"], "topic": v["topic"], "count": v["count"]} for v in repeated.values() if v["count"] > 1], key=lambda x: x["count"], reverse=True)[:5]
    weak = []
    for topic, count in by_topic.items():
        topic_items = [m for m in items if m.topic == topic]
        unresolved = sum(1 for m in topic_items if not m.reviewed)
        if count >= 2 or unresolved >= 2:
            weak.append({"topic": topic, "mistakes": count, "pending": unresolved, "reason": f"{count} recorded mistake(s), {unresolved} not yet reviewed"})
    weak.sort(key=lambda x: (x["pending"], x["mistakes"]), reverse=True)
    return {
        "total": len(items), "pending_revisions": len(pending), "due_revisions": len(due),
        "completed_reviews": sum(1 for m in items if m.reviewed),
        "by_language": by_language, "by_topic": by_topic, "repeated_errors": common,
        "weak_topics": weak[:6], "recent": [serialize(m) for m in sorted(items, key=lambda x: x.created_at or datetime.min, reverse=True)[:5]]
    }

@app.post("/api/demo-data")
def load_demo_data(db: Session = Depends(get_db)):
    existing = db.query(Mistake).filter(Mistake.is_sample == True).count()
    if existing:
        return {"message": "Demo data already exists", "count": existing}
    samples = [
        dict(title="Forgot to convert input", language="Python", topic="Input/Output", error_message="TypeError: can only concatenate str (not int) to str", incorrect_code="age = input('Age: ')\\nprint('Next year: ' + (age + 1))", corrected_code="age = int(input('Age: '))\\nprint('Next year:', age + 1)", explanation="input() returns text. Convert numeric input with int() before arithmetic.", root_cause="Assumed input() returns a number.", difficulty="Easy", tags="input,types", recorded_on=date.today(), next_revision=date.today()+timedelta(days=1), is_sample=True),
        dict(title="Off-by-one loop", language="Python", topic="Loops", error_message="IndexError: list index out of range", incorrect_code="for i in range(len(items) + 1):\\n    print(items[i])", corrected_code="for item in items:\\n    print(item)", explanation="The loop goes one position beyond the final valid index.", root_cause="Used len(items) + 1 as the range boundary.", difficulty="Medium", tags="loops,indexing", recorded_on=date.today(), next_revision=date.today(), is_sample=True),
        dict(title="Missing semicolon", language="Java", topic="Syntax", error_message="';' expected", incorrect_code="int total = 10\\nSystem.out.println(total);", corrected_code="int total = 10;\\nSystem.out.println(total);", explanation="Java statements normally end with a semicolon.", root_cause="Forgot the statement terminator.", difficulty="Easy", tags="syntax,java", recorded_on=date.today(), is_sample=True),
        dict(title="Wrong SQL filter", language="SQL", topic="Database", error_message="Query returns rows outside the requested department", incorrect_code="SELECT * FROM students WHERE department = IT;", corrected_code="SELECT * FROM students WHERE department = 'IT';", explanation="Text literals must be quoted in SQL.", root_cause="Did not quote a string literal.", difficulty="Medium", tags="sql,strings", recorded_on=date.today(), is_sample=True),
    ]
    db.add_all([Mistake(**s) for s in samples]); db.commit()
    return {"message": "Demo data loaded", "count": len(samples)}

@app.delete("/api/demo-data")
def remove_demo_data(db: Session = Depends(get_db)):
    count = db.query(Mistake).filter(Mistake.is_sample == True).count()
    db.query(Mistake).filter(Mistake.is_sample == True).delete(synchronize_session=False)
    db.commit()
    return {"message": "Demo data removed", "count": count}

@app.get("/api/options")
def options(db: Session = Depends(get_db)):
    items = db.query(Mistake).all()
    return {
        "languages": sorted({m.language for m in items}),
        "topics": sorted({m.topic for m in items}),
        "tags": sorted({tag.strip() for m in items for tag in m.tags.split(",") if tag.strip()})
    }
