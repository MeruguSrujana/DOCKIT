from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import (
    auth, cases, documents, evidence, templates, events, readiness, adapters,
    parties, notes, tasks, comments, notifications, users, search,
    collaborators, admin_reviews, disclosures, matters, document_access,
    jurisdiction,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="DOCKIT API",
    description="Case-centric document lifecycle & provenance system — SIH26190",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the real frontend origin before any real deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(documents.router)
app.include_router(evidence.router)
app.include_router(templates.router)
app.include_router(events.router)
app.include_router(readiness.router)
app.include_router(adapters.router)
app.include_router(parties.router)
app.include_router(notes.router)
app.include_router(tasks.router)
app.include_router(comments.router)
app.include_router(notifications.router)
app.include_router(users.router)
app.include_router(search.router)
app.include_router(collaborators.router)
app.include_router(admin_reviews.router)
app.include_router(disclosures.router)
app.include_router(matters.router)
app.include_router(document_access.router)
app.include_router(jurisdiction.router)


@app.get("/health")
def health():
    return {"status": "ok"}