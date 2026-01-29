import os
from typing import Optional, List
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mtg_internal_client import client as mtg_client

app = FastAPI(title="mtg_internal_api")

cors_origins_raw = os.environ.get("MTG_CORS_ORIGINS", "")
cors_origins = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()]
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def require_api_key(request: Request, call_next):
    expected_key = os.environ.get("MTG_API_KEY")
    if expected_key:
        provided_key = request.headers.get("x-api-key")
        if not provided_key or provided_key != expected_key:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)


# Language code to language name mapping
LANGUAGE_MAP = {
    "ja": "Japanese",
    "de": "German",
    "fr": "French",
    "en": "English",
    "japanese": "Japanese",
    "german": "German",
    "french": "French",
    "english": "English",
}


def normalize_language(lang: str) -> str:
    """Convert language code to full language name."""
    lang_lower = lang.lower().strip()
    return LANGUAGE_MAP.get(lang_lower, lang)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "db": mtg_client.get_db_path()}


@app.get("/cards")
def search_cards(
    q: str = Query(..., min_length=1, description="Card name to search"),
    limit: int = Query(10, ge=1, le=100),
):
    """Search for cards by name substring (case-insensitive). Returns paginated results."""
    if not q or len(q.strip()) == 0:
        return {"query": q, "results": [], "count": 0}

    results = mtg_client.find_cards(q, limit=limit)
    return {"query": q, "results": results, "count": len(results)}


@app.get("/cards/search")
def search_cards_by_language(
    q: str = Query(..., min_length=1, description="Card name to search"),
    lang: str = Query(
        "en",
        description="Language code or name (e.g., 'en', 'ja', 'Japanese', 'German')",
    ),
    limit: int = Query(10, ge=1, le=100),
):
    """
    Search for cards by foreign name in specified language.

    Example: /cards/search?q=ブラック&lang=ja&limit=5
             /cards/search?q=ロータス&lang=Japanese&limit=5
    """
    # Normalize language parameter
    normalized_lang = normalize_language(lang)

    if normalized_lang == "English":
        # For English, use regular card search
        results = mtg_client.find_cards(q, limit=limit)
        return {
            "query": q,
            "language": normalized_lang,
            "results": results,
            "count": len(results),
        }
    else:
        # For other languages, search foreign_data table
        results = mtg_client.find_cards_by_language(q, normalized_lang, limit=limit)
        return {
            "query": q,
            "language": normalized_lang,
            "results": results,
            "count": len(results),
        }


@app.get("/cards/advanced")
def search_cards_advanced(
    name: Optional[str] = Query(None, description="Card name (substring)"),
    colors: Optional[str] = Query(
        None, description="Colors comma-separated (W,U,B,R,G)"
    ),
    type: Optional[str] = Query(None, description="Card type (substring)"),
    mana_cost: Optional[str] = Query(None, description="Mana cost (substring)"),
    set: Optional[str] = Query(None, description="Set code (e.g., LEA, 2ED)"),
    rarity: Optional[str] = Query(
        None, description="Rarity (Common, Uncommon, Rare, Mythic Rare)"
    ),
    limit: int = Query(10, ge=1, le=100, description="Max results"),
):
    """
    Advanced multi-filter card search (AND logic).

    Example: /cards/advanced?name=Black&colors=B&type=Creature&rarity=Rare
    """
    color_list = None
    if colors:
        color_list = [c.strip().upper() for c in colors.split(",")]

    results = mtg_client.search_cards_advanced(
        name=name,
        colors=color_list,
        card_type=type,
        mana_cost=mana_cost,
        set_code=set,
        rarity=rarity,
        limit=limit,
    )

    filters = {
        k: v
        for k, v in {
            "name": name,
            "colors": colors,
            "type": type,
            "mana_cost": mana_cost,
            "set": set,
            "rarity": rarity,
        }.items()
        if v is not None
    }

    return {"filters": filters, "results": results, "count": len(results)}


@app.get("/cards/{name}")
def find_card(name: str):
    """Find first matching card by name. (Deprecated: use /cards?q=... instead)"""
    card = mtg_client.get_card_by_name(name)
    if card is None:
        return {"found": False}
    return {"found": True, "card": card}


@app.get("/sets")
def get_all_sets():
    """Get list of all available sets."""
    sets = mtg_client.get_sets()
    return {"sets": sets, "count": len(sets)}


@app.get("/stats")
def get_stats():
    """Get database statistics."""
    card_count = mtg_client.count_cards()
    sets = mtg_client.get_sets()
    return {"total_cards": card_count, "total_sets": len(sets)}


@app.get("/cards/{uuid}/translations")
def get_card_translations(uuid: str):
    """Get a card with all its foreign translations."""
    card = mtg_client.get_card_with_translations(uuid)
    if card is None:
        return {"found": False}
    return {"found": True, "card": card}


@app.get("/sets/{set_code}/cards/{card_number}")
def get_card_by_set_and_number(set_code: str, card_number: str):
    """
    Get a card by set code and card number with multi-language support.

    Example: /sets/LEA/cards/1
    """
    card = mtg_client.get_card_by_set_and_number(set_code, card_number)
    if card is None:
        return {"found": False, "set_code": set_code, "card_number": card_number}
    return {"found": True, "card": card}
