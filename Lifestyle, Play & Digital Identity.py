Here’s a complete **modern FastAPI backend** for **Page 16 – Lifestyle, Play & Digital Identity** with real endpoints, Pydantic models, mutable state, and interactive actions.

```python
# main.py
"""
Mwarokin Estates – Page 16 Backend
Lifestyle, Play & Digital Identity
FastAPI · Python 3.11+
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="Mwarokin Estates API – Page 16",
    description="Lifestyle, Play & Digital Identity backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────

class ChessStat(BaseModel):
    label: str
    value: str
    sub: str


class MatchStatus(str, Enum):
    live = "live"
    upcoming = "upcoming"
    completed = "completed"


class Player(BaseModel):
    initials: str
    name: str
    rating: int
    color: str
    winner: bool = False


class ChessMatch(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    round: str
    status: MatchStatus
    player1: Player
    player2: Player
    detail: str


class NFT(BaseModel):
    id: str
    icon: str
    visual: str
    name: str
    meta: str
    tokenId: str
    valuation: str
    blocks: str
    standard: str = "ERC-721"


class Recipe(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    emoji: str
    visual: str
    name: str
    author: str
    initials: str
    color: str
    time: str
    tags: List[str]
    rating: float = Field(ge=0, le=5)
    reviews: int = 0


class AstrologyInsight(BaseModel):
    icon: str
    title: str
    subtitle: str
    content: str
    score: int = Field(ge=0, le=100)


class PetsStat(BaseModel):
    label: str
    value: str
    sub: str


class Pet(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    emoji: str
    type: str  # dog | cat | bird | fish
    name: str
    breed: str
    owner: str
    property: str
    vaccinated: bool
    license: str


class Performance(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    initials: str
    name: str
    song: str
    score: float = Field(ge=0, le=10)
    color: str


class SportsStat(BaseModel):
    sport: str
    label: str
    value: str
    sub: str


class LeagueTeam(BaseModel):
    rank: int
    initials: str
    name: str
    property: str
    color: str
    played: int
    wins: int
    draws: int
    losses: int
    points: int


class VotePerformanceRequest(BaseModel):
    performance_id: str
    score: float = Field(ge=0, le=10)


class ContactPetOwnerRequest(BaseModel):
    pet_id: str
    message: Optional[str] = None


class RateRecipeRequest(BaseModel):
    recipe_id: str
    rating: float = Field(ge=1, le=5)


class ChallengeMatchRequest(BaseModel):
    opponent_name: str
    message: Optional[str] = None


# ──────────────────────────────────────────────────────────────
# In-memory store
# ──────────────────────────────────────────────────────────────

chess_stats: List[ChessStat] = [
    ChessStat(label="Your Rank", value="#12", sub="Out of 184 players"),
    ChessStat(label="Win Rate", value="68%", sub="142 games played"),
    ChessStat(label="Best Opening", value="Sicilian", sub="Defense rating: A+"),
    ChessStat(label="Tournaments Won", value="3", sub="2025 season"),
]

matches: List[ChessMatch] = [
    ChessMatch(
        round="Quarter Final", status=MatchStatus.live,
        player1=Player(initials="GW", name="Grace Wanjiku", rating=1820, color="#c8972a"),
        player2=Player(initials="AH", name="Amina Hassan", rating=1795, color="#6b4c9a"),
        detail="Move 24 · Grace to move · Time: 8:42",
    ),
    ChessMatch(
        round="Semi Final", status=MatchStatus.upcoming,
        player1=Player(initials="DO", name="David Ochieng", rating=1880, color="#2c6b9e"),
        player2=Player(initials="SK", name="Sarah Kilonzo", rating=1750, color="#b5447a"),
        detail="Scheduled: Apr 20, 2025 · 6 PM",
    ),
    ChessMatch(
        round="Final", status=MatchStatus.completed,
        player1=Player(initials="GW", name="Grace Wanjiku", rating=1820, color="#c8972a", winner=True),
        player2=Player(initials="PN", name="Peter Njoroge", rating=1680, color="#1e8e5c"),
        detail="Grace won in 38 moves · Caro-Kann Defense",
    ),
]

nfts: List[NFT] = [
    NFT(id="#MWK-001", icon="🏢", visual="nairobi", name="Kilimani Court",
        meta="Minted Feb 2024 · Verified ownership",
        tokenId="0x8f3a...c2e1", valuation="KSh 128M", blocks="#52,847,291"),
    NFT(id="#MWK-002", icon="🌊", visual="mombasa", name="Nyali Beach Resort",
        meta="Minted Jan 2024 · Fractional shares",
        tokenId="0x4b9c...d7a3", valuation="KSh 320M", blocks="#52,846,108"),
    NFT(id="#MWK-003", icon="🏔", visual="kisumu", name="Kisumu Lakefront",
        meta="Minted Mar 2024 · Land title verified",
        tokenId="0x2e7f...a9b4", valuation="KSh 186M", blocks="#52,845,002"),
    NFT(id="#MWK-004", icon="🦁", visual="nakuru", name="Nakuru Business Park",
        meta="Minted Apr 2024 · Commercial property",
        tokenId="0x9d1b...f5c8", valuation="KSh 240M", blocks="#52,844,889"),
]

recipes: List[Recipe] = [
    Recipe(emoji="🍚", visual="ugali", name="Classic Ugali & Sukuma Wiki",
           author="Mary Njoki", initials="MN", color="#b5447a", time="25 min",
           tags=["Kenyan", "Vegetarian", "Family"], rating=4.9, reviews=142),
    Recipe(emoji="🍛", visual="pilau", name="Coastal Beef Pilau",
           author="Amina Hassan", initials="AH", color="#6b4c9a", time="55 min",
           tags=["Swahili", "Spiced", "Festive"], rating=4.8, reviews=98),
    Recipe(emoji="🥬", visual="sukuma", name="Creamed Sukuma Wiki",
           author="John Wachira", initials="JW", color="#c8972a", time="20 min",
           tags=["Kenyan", "Quick", "Healthy"], rating=4.7, reviews=76),
    Recipe(emoji="🫓", visual="chapati", name="Soft Layered Chapati",
           author="Lucy Muthoni", initials="LM", color="#6b4c9a", time="40 min",
           tags=["Kenyan", "Breakfast", "Baking"], rating=5.0, reviews=204),
    Recipe(emoji="🥩", visual="nyama", name="Nyama Choma with Kachumbari",
           author="Brian Kamau", initials="BK", color="#2c6b9e", time="1.5 hrs",
           tags=["Kenyan", "BBQ", "Weekend"], rating=4.9, reviews=168),
    Recipe(emoji="☕", visual="tea", name="Kenyan Chai ya Tangawizi",
           author="Sarah Kilonzo", initials="SK", color="#b5447a", time="10 min",
           tags=["Kenyan", "Beverage", "Ginger"], rating=4.8, reviews=88),
]

astrology_insights: List[AstrologyInsight] = [
    AstrologyInsight(
        icon="fa-coins", title="Financial Fortune", subtitle="Today · Apr 19, 2025",
        content="Jupiter aligns with your natal sun, bringing <strong>financial clarity</strong>. Excellent day for property negotiations and reviewing mortgage rates.",
        score=88,
    ),
    AstrologyInsight(
        icon="fa-handshake", title="Tenant Relations", subtitle="This week",
        content="Mercury retrograde ends tomorrow. Expect <strong>improved communication</strong> with tenants. Best days for difficult conversations: Tue & Thu.",
        score=72,
    ),
    AstrologyInsight(
        icon="fa-home", title="Property Growth", subtitle="This month",
        content="Venus in Taurus favors <strong>real estate investments</strong>. Consider expanding your portfolio between Apr 22–30 when opportunities peak.",
        score=92,
    ),
    AstrologyInsight(
        icon="fa-heart", title="Personal Wellness", subtitle="Today",
        content="Moon in Cancer asks you to <strong>prioritize rest</strong>. Take breaks between meetings. Avoid major decisions after 6 PM.",
        score=65,
    ),
]

pets_stats: List[PetsStat] = [
    PetsStat(label="Registered Pets", value="84", sub="Across all properties"),
    PetsStat(label="Dogs", value="38", sub="Largest category"),
    PetsStat(label="Cats", value="32", sub="Community favorites"),
    PetsStat(label="Others", value="14", sub="Birds, fish, rabbits"),
]

pets: List[Pet] = [
    Pet(emoji="🐕", type="dog", name="Simba", breed="German Shepherd · 3 yrs",
        owner="John Wachira", property="Kilimani Court · 3B",
        vaccinated=True, license="PET-KC-0142"),
    Pet(emoji="🐱", type="cat", name="Malaika", breed="Tabby · 2 yrs",
        owner="Mary Njoki", property="Westlands Heights · 5A",
        vaccinated=True, license="PET-WH-0088"),
    Pet(emoji="🦜", type="bird", name="Tweety", breed="African Grey · 5 yrs",
        owner="Amina Hassan", property="South B Apartments · 12",
        vaccinated=True, license="PET-SB-0056"),
    Pet(emoji="🐠", type="fish", name="Bubbles", breed="Goldfish · 1 yr",
        owner="Brian Kamau", property="South B Apartments · 12",
        vaccinated=False, license="PET-SB-0057"),
    Pet(emoji="🐕", type="dog", name="Rex", breed="Labrador · 4 yrs",
        owner="Lucy Muthoni", property="Lavington Suites · 7C",
        vaccinated=True, license="PET-LS-0144"),
    Pet(emoji="🐈", type="cat", name="Zuri", breed="Persian · 3 yrs",
        owner="Sarah Kilonzo", property="Runda Gardens · 2A",
        vaccinated=True, license="PET-RG-0032"),
]

performances: List[Performance] = [
    Performance(initials="GW", name="Grace Wanjiku", song='"Hakuna Matata" · Lion King', score=9.6, color="#c8972a"),
    Performance(initials="JM", name="James Mwangi", song='"Bohemian Rhapsody" · Queen', score=8.8, color="#2c6b9e"),
    Performance(initials="AH", name="Amina Hassan", song='"Kiss From a Rose" · Seal', score=9.2, color="#6b4c9a"),
    Performance(initials="DO", name="David Ochieng", song='"Hallelujah" · Leonard Cohen', score=8.4, color="#2c6b9e"),
    Performance(initials="PN", name="Peter Njoroge", song='"Sultans of Swing" · Dire Straits', score=7.9, color="#1e8e5c"),
    Performance(initials="MN", name="Mary Njoki", song='"Waka Waka" · Shakira', score=9.0, color="#b5447a"),
]

sports_stats: List[SportsStat] = [
    SportsStat(sport="football", label="Football League", value="12", sub="Active teams"),
    SportsStat(sport="basketball", label="Basketball", value="8", sub="Teams registered"),
    SportsStat(sport="athletics", label="Running Club", value="62", sub="Active members"),
    SportsStat(sport="swimming", label="Swimming", value="24", sub="Monthly swimmers"),
]

league_standings: List[LeagueTeam] = [
    LeagueTeam(rank=1, initials="KC", name="Kilimani Court FC", property="Kilimani Court",
               color="#c8972a", played=12, wins=10, draws=1, losses=1, points=31),
    LeagueTeam(rank=2, initials="WH", name="Westlands Warriors", property="Westlands Heights",
               color="#6b4c9a", played=12, wins=9, draws=2, losses=1, points=29),
    LeagueTeam(rank=3, initials="SB", name="South B United", property="South B Apartments",
               color="#2c6b9e", played=12, wins=8, draws=2, losses=2, points=26),
    LeagueTeam(rank=4, initials="LS", name="Lavington Lions", property="Lavington Suites",
               color="#b5447a", played=12, wins=7, draws=3, losses=2, points=24),
    LeagueTeam(rank=5, initials="RG", name="Runda Rangers", property="Runda Gardens",
               color="#1e8e5c", played=12, wins=6, draws=3, losses=3, points=21),
    LeagueTeam(rank=6, initials="EP", name="Eastleigh Eagles", property="Eastleigh Plaza",
               color="#c4622a", played=12, wins=5, draws=4, losses=3, points=19),
]

action_log: List[dict] = []


def log_action(action: str, detail: dict) -> None:
    action_log.append({
        "id": str(uuid4()),
        "action": action,
        "detail": detail,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })


# ──────────────────────────────────────────────────────────────
# Chess & Strategy Club
# ──────────────────────────────────────────────────────────────

@app.get("/api/chess/stats", response_model=List[ChessStat])
def get_chess_stats():
    return chess_stats


@app.get("/api/chess/matches", response_model=List[ChessMatch])
def get_chess_matches(status: Optional[MatchStatus] = None):
    if status:
        return [m for m in matches if m.status == status]
    return matches


@app.get("/api/chess/profile")
def get_chess_profile():
    return {
        "elo": 1784,
        "rank": 12,
        "total_players": 184,
        "stats": chess_stats,
        "matches": matches,
    }


@app.post("/api/chess/challenge")
def challenge_player(req: ChallengeMatchRequest):
    log_action("chess_challenge", {
        "opponent": req.opponent_name,
        "message": req.message,
    })
    return {
        "status": "challenge_sent",
        "message": f"Challenge sent to {req.opponent_name}. They will be notified.",
    }


# ──────────────────────────────────────────────────────────────
# NFT & Digital Twin Registry
# ──────────────────────────────────────────────────────────────

@app.get("/api/nfts", response_model=List[NFT])
def list_nfts():
    return nfts


@app.get("/api/nfts/{nft_id}", response_model=NFT)
def get_nft(nft_id: str):
    nft = next((n for n in nfts if n.id == nft_id or n.id == f"#{nft_id}"), None)
    if not nft:
        raise HTTPException(status_code=404, detail="NFT not found")
    return nft


@app.get("/api/nfts/{nft_id}/onchain")
def view_onchain(nft_id: str):
    nft = next((n for n in nfts if n.id == nft_id or n.id == f"#{nft_id}"), None)
    if not nft:
        raise HTTPException(status_code=404, detail="NFT not found")
    log_action("nft_viewed_onchain", {"nft_id": nft.id, "name": nft.name})
    return {
        "explorer": f"https://polygonscan.com/token/{nft.tokenId}",
        "chain": "Polygon Mainnet",
        "nft": nft,
    }


# ──────────────────────────────────────────────────────────────
# Cooking & Recipe Exchange
# ──────────────────────────────────────────────────────────────

@app.get("/api/recipes", response_model=List[Recipe])
def list_recipes(tag: Optional[str] = None):
    if tag:
        return [r for r in recipes if tag.lower() in [t.lower() for t in r.tags]]
    return recipes


@app.get("/api/recipes/{recipe_id}", response_model=Recipe)
def get_recipe(recipe_id: str):
    recipe = next((r for r in recipes if r.id == recipe_id), None)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@app.post("/api/recipes", response_model=Recipe, status_code=status.HTTP_201_CREATED)
def create_recipe(recipe: Recipe):
    recipes.append(recipe)
    log_action("recipe_created", recipe.model_dump())
    return recipe


@app.post("/api/recipes/rate")
def rate_recipe(req: RateRecipeRequest):
    recipe = next((r for r in recipes if r.id == req.recipe_id), None)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    # Simple running average
    total = recipe.rating * recipe.reviews + req.rating
    recipe.reviews += 1
    recipe.rating = round(total / recipe.reviews, 1)
    log_action("recipe_rated", {
        "recipe_id": req.recipe_id,
        "name": recipe.name,
        "new_rating": recipe.rating,
        "reviews": recipe.reviews,
    })
    return {"status": "rated", "recipe": recipe}


@app.get("/api/recipes/summary")
def recipes_summary():
    return {
        "total_shared": 248,
        "count": len(recipes),
        "recipes": recipes,
    }


# ──────────────────────────────────────────────────────────────
# Astrology & Fortune
# ──────────────────────────────────────────────────────────────

@app.get("/api/astrology/insights", response_model=List[AstrologyInsight])
def get_astrology_insights():
    return astrology_insights


@app.get("/api/astrology/profile")
def get_astrology_profile():
    return {
        "sign": "Leo",
        "symbol": "♌",
        "date_range": "Jul 23 – Aug 22",
        "insights": astrology_insights,
    }


# ──────────────────────────────────────────────────────────────
# Pet Management
# ──────────────────────────────────────────────────────────────

@app.get("/api/pets/stats", response_model=List[PetsStat])
def get_pets_stats():
    return pets_stats


@app.get("/api/pets", response_model=List[Pet])
def list_pets(type: Optional[str] = None, vaccinated: Optional[bool] = None):
    result = pets
    if type:
        result = [p for p in result if p.type == type]
    if vaccinated is not None:
        result = [p for p in result if p.vaccinated == vaccinated]
    return result


@app.get("/api/pets/{pet_id}", response_model=Pet)
def get_pet(pet_id: str):
    pet = next((p for p in pets if p.id == pet_id), None)
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
    return pet


@app.post("/api/pets", response_model=Pet, status_code=status.HTTP_201_CREATED)
def register_pet(pet: Pet):
    pets.append(pet)
    log_action("pet_registered", pet.model_dump())
    return pet


@app.post("/api/pets/contact")
def contact_pet_owner(req: ContactPetOwnerRequest):
    pet = next((p for p in pets if p.id == req.pet_id), None)
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
    log_action("pet_owner_contacted", {
        "pet_id": req.pet_id,
        "pet_name": pet.name,
        "owner": pet.owner,
        "message": req.message,
    })
    return {
        "status": "contacted",
        "message": f"Message sent to {pet.owner} regarding {pet.name}",
        "pet": pet,
    }


@app.get("/api/pets/{pet_id}/records")
def get_pet_records(pet_id: str):
    pet = next((p for p in pets if p.id == pet_id), None)
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
    return {
        "pet": pet,
        "vaccinations": [
            {"date": "2024-11-12", "type": "Rabies", "status": "valid"},
            {"date": "2025-02-03", "type": "DHPP", "status": "valid" if pet.vaccinated else "pending"},
        ],
        "license_expires": "2026-04-15",
    }


# ──────────────────────────────────────────────────────────────
# Karaoke & Talent Show
# ──────────────────────────────────────────────────────────────

@app.get("/api/karaoke/performances", response_model=List[Performance])
def list_performances():
    return sorted(performances, key=lambda p: p.score, reverse=True)


@app.get("/api/karaoke/champion")
def get_champion():
    champion = max(performances, key=lambda p: p.score)
    return {
        "next_event": "Apr 26 · 7 PM",
        "champion": champion,
        "blurb": (
            f"{champion.name} wowed the crowd with their rendition, "
            f"earning the highest score in Mwarokin history. The bar has been set!"
        ),
    }


@app.post("/api/karaoke/vote")
def vote_performance(req: VotePerformanceRequest):
    perf = next((p for p in performances if p.id == req.performance_id), None)
    if not perf:
        raise HTTPException(status_code=404, detail="Performance not found")
    # Simple re-average (demo)
    perf.score = round((perf.score + req.score) / 2, 1)
    log_action("karaoke_voted", {
        "performance_id": req.performance_id,
        "name": perf.name,
        "new_score": perf.score,
    })
    return {"status": "voted", "performance": perf}


@app.post("/api/karaoke/performances", response_model=Performance, status_code=status.HTTP_201_CREATED)
def submit_performance(perf: Performance):
    performances.append(perf)
    log_action("performance_submitted", perf.model_dump())
    return perf


# ──────────────────────────────────────────────────────────────
# Sports League
# ──────────────────────────────────────────────────────────────

@app.get("/api/sports/stats", response_model=List[SportsStat])
def get_sports_stats():
    return sports_stats


@app.get("/api/sports/league", response_model=List[LeagueTeam])
def get_league_table():
    return sorted(league_standings, key=lambda t: t.points, reverse=True)


@app.get("/api/sports/summary")
def sports_summary():
    return {
        "stats": sports_stats,
        "league": sorted(league_standings, key=lambda t: t.points, reverse=True),
    }


# ──────────────────────────────────────────────────────────────
# Full Page 16 payload
# ──────────────────────────────────────────────────────────────

@app.get("/api/page16")
def page16_data():
    return {
        "chess": {
            "elo": 1784,
            "stats": chess_stats,
            "matches": matches,
        },
        "nfts": nfts,
        "recipes": {
            "total_shared": 248,
            "items": recipes,
        },
        "astrology": {
            "sign": "Leo",
            "symbol": "♌",
            "date_range": "Jul 23 – Aug 22",
            "insights": astrology_insights,
        },
        "pets": {
            "stats": pets_stats,
            "items": pets,
        },
        "karaoke": {
            "next_event": "Apr 26 · 7 PM",
            "champion": max(performances, key=lambda p: p.score),
            "performances": sorted(performances, key=lambda p: p.score, reverse=True),
        },
        "sports": {
            "stats": sports_stats,
            "league": sorted(league_standings, key=lambda t: t.points, reverse=True),
        },
    }


@app.get("/api/actions")
def get_action_log(limit: int = 50):
    return action_log[-limit:]


@app.get("/")
def root():
    return {
        "service": "Mwarokin Estates – Lifestyle, Play & Digital Identity",
        "page": 16,
        "version": "1.0.0",
        "docs": "/docs",
        "page16": "/api/page16",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### Run it

```bash
pip install fastapi uvicorn pydantic
python main.py
```

→ **http://localhost:8000/docs**

### Real functionality map

| Feature              | Key endpoints                                      | Real behaviour                          |
|----------------------|----------------------------------------------------|-----------------------------------------|
| Chess Club           | `GET /api/chess/*`, `POST /api/chess/challenge`    | Profile, live matches, send challenges  |
| NFT Registry         | `GET /api/nfts`, `GET /api/nfts/{id}/onchain`      | View on-chain details                   |
| Recipe Exchange      | `GET/POST /api/recipes`, `POST /api/recipes/rate`  | Create recipes, rate (updates average)  |
| Astrology            | `GET /api/astrology/*`                             | Zodiac profile + insights               |
| Pet Management       | `GET/POST /api/pets`, `POST /api/pets/contact`      | Register, filter, contact owner, records|
| Karaoke              | `GET /api/karaoke/*`, `POST /api/karaoke/vote`     | Vote, submit performances, champion     |
| Sports League        | `GET /api/sports/*`                                | Stats + live league table               |
| Full page            | `GET /api/page16`                                  | Everything in one call                  |
| Audit log            | `GET /api/actions`                                 | Every write is recorded                 |

All write operations mutate state and are logged. Swap the in-memory lists for SQLAlchemy + SQLite/Postgres when you need persistence — the API surface stays the same.