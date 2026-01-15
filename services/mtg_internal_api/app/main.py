from typing import Optional, List
from fastapi import FastAPI, Query

from mtg_internal_client import client as mtg_client

app = FastAPI(title="mtg_internal_api")


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


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
