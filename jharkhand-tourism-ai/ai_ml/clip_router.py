"""
CLIP API Router
================
Exposes CLIP service as HTTP endpoints.
Called by the backend (port 8000) which calls us (port 8001).

Endpoints:
  POST /clip/search/text   → Search destinations by text description
  POST /clip/search/image  → Search destinations by uploaded photo (visual search)
  POST /clip/index         → Add a new destination to the search index
  GET  /clip/status        → Check if CLIP model is loaded
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from pydantic import BaseModel
import tempfile, os

router = APIRouter()


# ─── Request/Response Models ──────────────────────────────────────────────────

class TextSearchRequest(BaseModel):
    query: str               # e.g., "show me tribal villages with waterfalls"
    top_k: int = 5           # Number of results to return


class SearchResult(BaseModel):
    rank: int
    destination: str
    similarity_score: float


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/status")
async def clip_status(request: Request):
    """Check if CLIP model is ready."""
    clip = request.app.state.clip
    return {
        "loaded": clip.is_loaded,
        "indexed_destinations": clip.faiss_index.ntotal if clip.faiss_index else 0,
        "device": clip.device,
    }


@router.post("/search/text", response_model=list[SearchResult])
async def search_by_text(body: TextSearchRequest, request: Request):
    """
    Find destinations matching a text description.

    Example request:
        POST /clip/search/text
        {"query": "ancient temple in forest", "top_k": 5}

    Example response:
        [
          {"rank": 1, "destination": "Rajrappa Temple", "similarity_score": 0.89},
          {"rank": 2, "destination": "Deoghar", "similarity_score": 0.82},
          ...
        ]
    """
    clip = request.app.state.clip
    if not clip.is_loaded:
        raise HTTPException(503, "CLIP model not loaded yet")

    results = await clip.search_by_text(body.query, body.top_k)
    return results


@router.post("/search/image", response_model=list[SearchResult])
async def search_by_image(
    request: Request,
    file: UploadFile = File(...),
    top_k: int = 5
):
    """
    Visual search — upload a photo, get similar destinations.

    Tourist uploads: photo of a waterfall from their last trip
    Returns: ["Hundru Falls", "Dassam Falls", "Jonha Falls"]

    The magic: CLIP encodes both the photo and destination images
    into the same vector space, so similar-looking places have
    similar vectors → FAISS finds them instantly.
    """
    clip = request.app.state.clip
    if not clip.is_loaded:
        raise HTTPException(503, "CLIP model not loaded yet")

    # Save uploaded file temporarily
    suffix = os.path.splitext(file.filename)[1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        results = await clip.search_by_image(tmp_path, top_k)
        return results
    finally:
        os.unlink(tmp_path)  # Clean up temp file


@router.post("/index")
async def index_destination(
    request: Request,
    destination_name: str,
    image: UploadFile = File(...)
):
    """
    Add a new destination to the CLIP search index.
    Called by admin when adding new destinations to the platform.
    """
    clip = request.app.state.clip
    if not clip.is_loaded:
        raise HTTPException(503, "CLIP model not loaded yet")

    suffix = os.path.splitext(image.filename)[1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await image.read())
        tmp_path = tmp.name

    try:
        await clip.add_destination(destination_name, tmp_path)
        return {
            "message": f"'{destination_name}' added to search index",
            "total_indexed": clip.faiss_index.ntotal
        }
    finally:
        os.unlink(tmp_path)
