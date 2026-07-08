# requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6
aiofiles==23.2.1

# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    app_name: str = "Mwarokin Architecture Designer"
    storage_path: Path = Path("./designs")
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    cors_origins: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.storage_path.mkdir(exist_ok=True)

settings = Settings()

# app/models/design.py
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional, Any
from datetime import datetime
from enum import Enum

class ElementType(str, Enum):
    """Supported architectural element types"""
    WALL = "wall"
    ROOM = "room"
    DOOR = "door"
    WINDOW = "window"
    FURNITURE = "furniture"
    STAIRS = "stairs"

class Element(BaseModel):
    """Represents a single architectural element"""
    id: Optional[int] = None
    type: ElementType
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    layer: int = Field(ge=1, le=10)
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v: str) -> str:
        """Ensure valid hex color format"""
        return v.lower()

class DesignMetadata(BaseModel):
    """Metadata for a design project"""
    grid_size: int = Field(default=20, gt=0, le=100)
    zoom: float = Field(default=1.0, gt=0, le=10)
    created: datetime = Field(default_factory=datetime.utcnow)
    modified: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0"

class Design(BaseModel):
    """Complete design project with elements and metadata"""
    id: str
    name: str = Field(min_length=1, max_length=255)
    elements: list[Element] = Field(default_factory=list)
    metadata: DesignMetadata = Field(default_factory=DesignMetadata)
    
    @property
    def stats(self) -> dict[str, int]:
        """Calculate design statistics"""
        return {
            "total": len(self.elements),
            "walls": sum(1 for e in self.elements if e.type == ElementType.WALL),
            "rooms": sum(1 for e in self.elements if e.type == ElementType.ROOM),
            "doors": sum(1 for e in self.elements if e.type == ElementType.DOOR),
            "windows": sum(1 for e in self.elements if e.type == ElementType.WINDOW),
        }

class DesignCreate(BaseModel):
    """Request model for creating a new design"""
    name: str = Field(min_length=1, max_length=255)
    elements: list[Element] = Field(default_factory=list)

class DesignUpdate(BaseModel):
    """Request model for updating a design"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    elements: Optional[list[Element]] = None

    # app/services/design_service.py
import json
import aiofiles
from pathlib import Path
from typing import AsyncGenerator
import uuid
from ..models.design import Design, DesignCreate, DesignUpdate
from ..config import settings
import logging

logger = logging.getLogger(__name__)

class DesignService:
    """Async service for design CRUD operations"""
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
    
    async def save_design(self, design_create: DesignCreate) -> Design:
        """Save a new design to disk"""
        design_id = str(uuid.uuid4())[:8]
        design = Design(
            id=design_id,
            name=design_create.name,
            elements=design_create.elements,
            metadata=DesignMetadata()
        )
        
        file_path = self.storage_path / f"{design_id}.json"
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(design.model_dump_json(indent=2))
        
        logger.info(f"Saved design {design_id} with {len(design.elements)} elements")
        return design
    
    async def get_design(self, design_id: str) -> Design | None:
        """Retrieve a design by ID"""
        file_path = self.storage_path / f"{design_id}.json"
        
        if not file_path.exists():
            return None
        
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
                return Design(**data)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading design {design_id}: {e}")
            return None
    
    async def list_designs(self) -> AsyncGenerator[Design, None]:
        """List all saved designs"""
        for file_path in self.storage_path.glob("*.json"):
            try:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = json.loads(content)
                    yield Design(**data)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Skipping corrupted file {file_path}: {e}")
                continue
    
    async def update_design(self, design_id: str, update: DesignUpdate) -> Design | None:
        """Update an existing design"""
        design = await self.get_design(design_id)
        if not design:
            return None
        
        if update.name:
            design.name = update.name
        if update.elements is not None:
            design.elements = update.elements
        
        design.metadata.modified = datetime.utcnow()
        
        file_path = self.storage_path / f"{design_id}.json"
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(design.model_dump_json(indent=2))
        
        logger.info(f"Updated design {design_id}")
        return design
    
    async def delete_design(self, design_id: str) -> bool:
        """Delete a design"""
        file_path = self.storage_path / f"{design_id}.json"
        
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted design {design_id}")
                return True
        except IOError as e:
            logger.error(f"Error deleting design {design_id}: {e}")
        
        return False
    
    async def export_design(self, design_id: str, format: str = "json") -> bytes | None:
        """Export design in specified format"""
        design = await self.get_design(design_id)
        if not design:
            return None
        
        if format == "json":
            return design.model_dump_json(indent=2).encode('utf-8')
        
        # Future: Implement PDF export
        # if format == "pdf":
        #     return await generate_pdf(design)
        
        return None

# Singleton service instance
design_service = DesignService(settings.storage_path)

# app/api/v1/endpoints/designs.py
from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import AsyncGenerator
import io
from ...models.design import Design, DesignCreate, DesignUpdate, ElementType
from ...services.design_service import design_service
from ...config import settings

router = APIRouter(prefix="/designs", tags=["designs"])

@router.post("/", response_model=Design, status_code=status.HTTP_201_CREATED)
async def create_design(design: DesignCreate):
    """Create a new architectural design"""
    return await design_service.save_design(design)

@router.get("/", response_model=list[Design])
async def list_designs(limit: int = Query(100, ge=1, le=1000)):
    """List all designs with pagination"""
    designs = []
    async for design in design_service.list_designs():
        designs.append(design)
        if len(designs) >= limit:
            break
    return designs

@router.get("/{design_id}", response_model=Design)
async def get_design(design_id: str):
    """Get a specific design by ID"""
    design = await design_service.get_design(design_id)
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Design {design_id} not found"
        )
    return design

@router.put("/{design_id}", response_model=Design)
async def update_design(design_id: str, update: DesignUpdate):
    """Update an existing design"""
    design = await design_service.update_design(design_id, update)
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Design {design_id} not found"
        )
    return design

@router.delete("/{design_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_design(design_id: str):
    """Delete a design"""
    success = await design_service.delete_design(design_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Design {design_id} not found"
        )

@router.post("/{design_id}/export")
async def export_design(
    design_id: str,
    format: str = Query("json", enum=["json", "pdf"])
):
    """Export design as file"""
    data = await design_service.export_design(design_id, format)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Design {design_id} not found"
        )
    
    media_type = "application/json" if format == "json" else "application/pdf"
    filename = f"design-{design_id}.{format}"
    
    return io.BytesIO(data)

    # app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from pathlib import Path
from .config import settings
from .api.v1.endpoints import designs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Application lifespan context
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown"""
    logger = logging.getLogger(__name__)
    logger.info("🚀 Mwarokin Architecture Designer starting up...")
    logger.info(f"Storage path: {settings.storage_path.absolute()}")
    yield
    logger.info("⛔ Shutting down...")

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Modern architecture design tool backend",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(designs.router, prefix="/api/v1")

# Serve static files (the provided HTML/CSS/JS)
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the main application"""
    index_path = static_path / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return """
    <html>
        <head><title>Mwarokin Setup</title></head>
        <body>
            <h1>⚠️ Frontend Not Found</h1>
            <p>Place your HTML file in <code>app/static/index.html</code></p>
        </body>
    </html>
    """

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "storage": str(settings.storage_path.absolute())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

    pip install -r requirements.txt

    mkdir -p app/static app/api/v1/endpoints

    STORAGE_PATH=./designs
CORS_ORIGINS=["http://localhost:8000"]

python app/main.py