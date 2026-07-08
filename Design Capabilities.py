I'll create a modern Python agentic system that can interact with and extend the 3D architectural design platform you've provided. Here's a comprehensive solution:

```python
"""
Mwarokin - AI-Powered 3D Architectural Design Agent System
Modern Python implementation with agentic capabilities
"""

import asyncio
import json
import logging
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import uuid
import datetime

# Third-party imports (would be in requirements.txt)
try:
    import numpy as np
    from pydantic import BaseModel, Field
    import aiohttp
    from sqlalchemy import create_engine, Column, String, JSON, DateTime
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
except ImportError:
    # Fallback for demonstration
    pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mwarokin_agent")

class DesignType(Enum):
    HOUSE = "house"
    ROOM = "room"
    FLOOR = "floor"
    COMMERCIAL = "commercial"

class MaterialType(Enum):
    WOOD = "wood"
    CONCRETE = "concrete"
    GLASS = "glass"
    METAL = "metal"
    BRICK = "brick"

class ViewType(Enum):
    PERSPECTIVE = "perspective"
    TOP = "top"
    FRONT = "front"

@dataclass
class DesignElement:
    id: str
    type: str
    position: Dict[str, float]
    dimensions: Dict[str, float]
    material: str
    color: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class DesignScene:
    scene_id: str
    name: str
    design_type: DesignType
    elements: List[DesignElement]
    camera_position: Dict[str, float]
    view_type: ViewType
    created_at: str
    updated_at: str

class DesignSpecification(BaseModel):
    design_type: DesignType
    budget: Optional[float] = None
    area: float
    style: str
    materials: List[MaterialType]
    rooms: Optional[int] = None
    constraints: List[str] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)

class ArchitecturalAgent:
    """
    AI Agent for architectural design assistance
    """
    
    def __init__(self, agent_id: str = None):
        self.agent_id = agent_id or f"arch_agent_{uuid.uuid4().hex[:8]}"
        self.scene_history: List[DesignScene] = []
        self.user_preferences: Dict[str, Any] = {}
        self.design_rules = self._load_design_rules()
        logger.info(f"Initialized Architectural Agent: {self.agent_id}")
    
    def _load_design_rules(self) -> Dict[str, Any]:
        """Load architectural design rules and best practices"""
        return {
            "residential": {
                "min_room_size": 9.0,  # square meters
                "ceiling_height": 2.4,  # meters
                "window_to_wall_ratio": 0.15,
                "door_standard_height": 2.1,
                "door_standard_width": 0.9,
            },
            "material_properties": {
                "wood": {"cost_factor": 1.2, "sustainability": "high"},
                "concrete": {"cost_factor": 1.0, "sustainability": "medium"},
                "glass": {"cost_factor": 2.5, "sustainability": "medium"},
                "metal": {"cost_factor": 1.8, "sustainability": "low"},
                "brick": {"cost_factor": 1.1, "sustainability": "high"},
            }
        }
    
    async def generate_design(self, spec: DesignSpecification) -> DesignScene:
        """Generate a new architectural design based on specifications"""
        logger.info(f"Generating design for {spec.design_type.value}")
        
        # Create base scene
        scene_id = f"scene_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.datetime.now().isoformat()
        
        # Generate design elements based on specification
        elements = await self._generate_elements(spec)
        
        # Set initial camera position based on design type
        camera_position = self._get_initial_camera_position(spec.design_type)
        
        scene = DesignScene(
            scene_id=scene_id,
            name=f"{spec.style}_{spec.design_type.value}",
            design_type=spec.design_type,
            elements=elements,
            camera_position=camera_position,
            view_type=ViewType.PERSPECTIVE,
            created_at=timestamp,
            updated_at=timestamp
        )
        
        self.scene_history.append(scene)
        return scene
    
    async def _generate_elements(self, spec: DesignSpecification) -> List[DesignElement]:
        """Generate design elements based on specifications"""
        elements = []
        
        if spec.design_type == DesignType.HOUSE:
            elements.extend(await self._generate_house_elements(spec))
        elif spec.design_type == DesignType.ROOM:
            elements.extend(await self._generate_room_elements(spec))
        elif spec.design_type == DesignType.FLOOR:
            elements.extend(await self._generate_floor_elements(spec))
        
        return elements
    
    async def _generate_house_elements(self, spec: DesignSpecification) -> List[DesignElement]:
        """Generate elements for a house design"""
        elements = []
        
        # Main structure
        main_structure = DesignElement(
            id="main_structure",
            type="walls",
            position={"x": 0, "y": 2, "z": 0},
            dimensions={"width": 6, "height": 4, "depth": 6},
            material=spec.materials[0].value if spec.materials else "concrete",
            color="#8b7355"
        )
        elements.append(main_structure)
        
        # Roof
        roof = DesignElement(
            id="roof",
            type="roof",
            position={"x": 0, "y": 5.25, "z": 0},
            dimensions={"radius": 5, "height": 2.5},
            material="wood",
            color="#a0522d"
        )
        elements.append(roof)
        
        # Windows
        for i in range(4):
            window = DesignElement(
                id=f"window_{i}",
                type="window",
                position={
                    "x": math.sin(i * math.pi / 2) * 3.05,
                    "y": 2.5,
                    "z": math.cos(i * math.pi / 2) * 3.05
                },
                dimensions={"width": 1, "height": 1.2, "depth": 0.1},
                material="glass",
                color="#87ceeb"
            )
            elements.append(window)
        
        # Door
        door = DesignElement(
            id="main_door",
            type="door",
            position={"x": 0, "y": 1, "z": 3.05},
            dimensions={"width": 1.2, "height": 2, "depth": 0.1},
            material="wood",
            color="#4a3728"
        )
        elements.append(door)
        
        return elements
    
    async def _generate_room_elements(self, spec: DesignSpecification) -> List[DesignElement]:
        """Generate elements for a room design"""
        elements = []
        room_size = math.sqrt(spec.area)
        
        # Floor
        floor = DesignElement(
            id="floor",
            type="floor",
            position={"x": 0, "y": 0.1, "z": 0},
            dimensions={"width": room_size, "height": 0.2, "depth": room_size},
            material=spec.materials[0].value if spec.materials else "wood",
            color="#8b7355"
        )
        elements.append(floor)
        
        # Walls
        wall_height = 3
        walls_data = [
            {"id": "back_wall", "position": {"x": 0, "y": wall_height/2, "z": -room_size/2}},
            {"id": "left_wall", "position": {"x": -room_size/2, "y": wall_height/2, "z": 0}},
            {"id": "right_wall", "position": {"x": room_size/2, "y": wall_height/2, "z": 0}},
        ]
        
        for wall in walls_data:
            wall_element = DesignElement(
                id=wall["id"],
                type="wall",
                position=wall["position"],
                dimensions={"width": room_size, "height": wall_height, "depth": 0.2},
                material="concrete",
                color="#e0e0e0"
            )
            elements.append(wall_element)
        
        return elements
    
    async def _generate_floor_elements(self, spec: DesignSpecification) -> List[DesignElement]:
        """Generate elements for a floor plan design"""
        elements = []
        floor_size = math.sqrt(spec.area)
        
        # Main floor
        floor = DesignElement(
            id="main_floor",
            type="floor_slab",
            position={"x": 0, "y": 0.15, "z": 0},
            dimensions={"width": floor_size, "height": 0.3, "depth": floor_size},
            material="concrete",
            color="#8b7355"
        )
        elements.append(floor)
        
        # Room dividers
        divider_positions = [
            {"x": 0, "y": 0.4, "z": 0},
            {"x": 0, "y": 0.4, "z": 0}
        ]
        
        for i, pos in enumerate(divider_positions):
            divider = DesignElement(
                id=f"divider_{i}",
                type="divider",
                position=pos,
                dimensions={"width": floor_size/2, "height": 0.2, "depth": 0.1},
                material="concrete",
                color="#606060"
            )
            elements.append(divider)
        
        return elements
    
    def _get_initial_camera_position(self, design_type: DesignType) -> Dict[str, float]:
        """Get optimal initial camera position based on design type"""
        positions = {
            DesignType.HOUSE: {"x": 10, "y": 8, "z": 10},
            DesignType.ROOM: {"x": 5, "y": 4, "z": 8},
            DesignType.FLOOR: {"x": 0, "y": 15, "z": 0},
            DesignType.COMMERCIAL: {"x": 15, "y": 12, "z": 15}
        }
        return positions.get(design_type, {"x": 10, "y": 8, "z": 10})
    
    async def optimize_design(self, scene: DesignScene, objectives: List[str]) -> DesignScene:
        """Optimize design based on objectives (cost, sustainability, aesthetics, etc.)"""
        logger.info(f"Optimizing design {scene.scene_id} for objectives: {objectives}")
        
        optimized_elements = []
        
        for element in scene.elements:
            optimized_element = await self._optimize_element(element, objectives)
            optimized_elements.append(optimized_element)
        
        # Create optimized scene
        optimized_scene = DesignScene(
            scene_id=f"{scene.scene_id}_optimized",
            name=f"Optimized_{scene.name}",
            design_type=scene.design_type,
            elements=optimized_elements,
            camera_position=scene.camera_position,
            view_type=scene.view_type,
            created_at=datetime.datetime.now().isoformat(),
            updated_at=datetime.datetime.now().isoformat()
        )
        
        self.scene_history.append(optimized_scene)
        return optimized_scene
    
    async def _optimize_element(self, element: DesignElement, objectives: List[str]) -> DesignElement:
        """Optimize individual design element"""
        optimized_element = DesignElement(
            id=element.id,
            type=element.type,
            position=element.position,
            dimensions=element.dimensions,
            material=element.material,
            color=element.color,
            metadata=element.metadata.copy()
        )
        
        # Apply optimization rules
        if "cost" in objectives:
            optimized_element = await self._optimize_for_cost(optimized_element)
        
        if "sustainability" in objectives:
            optimized_element = await self._optimize_for_sustainability(optimized_element)
        
        if "aesthetics" in objectives:
            optimized_element = await self._optimize_for_aesthetics(optimized_element)
        
        return optimized_element
    
    async def _optimize_for_cost(self, element: DesignElement) -> DesignElement:
        """Optimize element for cost reduction"""
        material_cost_factors = {
            "glass": 2.5, "metal": 1.8, "wood": 1.2, 
            "brick": 1.1, "concrete": 1.0
        }
        
        current_cost_factor = material_cost_factors.get(element.material, 1.0)
        
        # Find cheaper alternative
        cheaper_materials = [
            mat for mat, factor in material_cost_factors.items() 
            if factor < current_cost_factor
        ]
        
        if cheaper_materials and element.type not in ["window", "glass_structure"]:
            element.material = cheaper_materials[0]
            element.metadata["optimization_note"] = "Material changed for cost optimization"
        
        return element
    
    async def _optimize_for_sustainability(self, element: DesignElement) -> DesignElement:
        """Optimize element for sustainability"""
        sustainable_materials = ["wood", "brick", "concrete"]
        
        if element.material not in sustainable_materials:
            element.material = "wood"  # Default to sustainable material
            element.metadata["optimization_note"] = "Material changed for sustainability"
        
        return element
    
    async def _optimize_for_aesthetics(self, element: DesignElement) -> DesignElement:
        """Optimize element for aesthetic appeal"""
        # Apply color harmony rules
        color_schemes = {
            "wood": ["#8b7355", "#a0522d", "#d2b48c"],
            "concrete": ["#808080", "#a9a9a9", "#696969"],
            "glass": ["#87ceeb", "#add8e6", "#b0e0e6"],
            "metal": ["#708090", "#2f4f4f", "#556b2f"]
        }
        
        if element.material in color_schemes:
            current_color = element.color
            available_colors = color_schemes[element.material]
            
            if current_color not in available_colors:
                element.color = available_colors[0]
                element.metadata["color_optimized"] = True
        
        return element
    
    def export_scene(self, scene: DesignScene, format: str = "json") -> str:
        """Export scene to various formats"""
        if format == "json":
            return json.dumps(asdict(scene), indent=2)
        elif format == "html":
            return self._export_to_html(scene)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_to_html(self, scene: DesignScene) -> str:
        """Export scene as HTML with Three.js visualization"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Mwarokin Export - {scene_name}</title>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
            <style>
                body {{ margin: 0; background: #0a0a0a; }}
                canvas {{ display: block; }}
            </style>
        </head>
        <body>
            <div id="scene-container"></div>
            <script>
                // Scene initialization code for exported design
                const scene = new THREE.Scene();
                const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000);
                const renderer = new THREE.WebGLRenderer();
                renderer.setSize(window.innerWidth, window.innerHeight);
                document.getElementById('scene-container').appendChild(renderer.domElement);
                
                // Add elements from exported scene
                {elements_code}
                
                // Animation loop
                function animate() {{
                    requestAnimationFrame(animate);
                    renderer.render(scene, camera);
                }}
                animate();
            </script>
        </body>
        </html>
        """
        
        elements_code = self._generate_threejs_elements(scene.elements)
        return html_template.format(
            scene_name=scene.name,
            elements_code=elements_code
        )
    
    def _generate_threejs_elements(self, elements: List[DesignElement]) -> str:
        """Generate Three.js code for scene elements"""
        js_code = []
        
        for element in elements:
            if element.type in ["walls", "floor", "door"]:
                js_code.append(f"""
                // {element.id}
                const {element.id}_geometry = new THREE.BoxGeometry(
                    {element.dimensions.get('width', 1)}, 
                    {element.dimensions.get('height', 1)}, 
                    {element.dimensions.get('depth', 1)}
                );
                const {element.id}_material = new THREE.MeshStandardMaterial({{ 
                    color: '{element.color}',
                    roughness: 0.7 
                }});
                const {element.id} = new THREE.Mesh({element.id}_geometry, {element.id}_material);
                {element.id}.position.set(
                    {element.position['x']}, 
                    {element.position['y']}, 
                    {element.position['z']}
                );
                scene.add({element.id});
                """)
        
        return "\n".join(js_code)

class DesignSessionManager:
    """
    Manages design sessions and collaboration
    """
    
    def __init__(self):
        self.active_sessions: Dict[str, DesignSession] = {}
        self.agents: Dict[str, ArchitecturalAgent] = {}
    
    async def create_session(self, user_id: str, spec: DesignSpecification) -> str:
        """Create a new design session"""
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        agent = ArchitecturalAgent()
        
        session = DesignSession(
            session_id=session_id,
            user_id=user_id,
            agent=agent,
            specification=spec
        )
        
        self.active_sessions[session_id] = session
        self.agents[session_id] = agent
        
        logger.info(f"Created design session {session_id} for user {user_id}")
        return session_id
    
    async def get_session(self, session_id: str) -> Optional['DesignSession']:
        """Retrieve a design session"""
        return self.active_sessions.get(session_id)
    
    async def collaborate_on_design(self, session_id: str, collaborator_notes: str) -> DesignScene:
        """Apply collaborative input to design"""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Analyze collaborator input and update design
        updated_scene = await session.agent.optimize_design(
            session.current_scene, 
            self._parse_collaborator_notes(collaborator_notes)
        )
        
        session.current_scene = updated_scene
        session.collaboration_history.append(collaborator_notes)
        
        return updated_scene
    
    def _parse_collaborator_notes(self, notes: str) -> List[str]:
        """Parse natural language notes into optimization objectives"""
        objectives = []
        notes_lower = notes.lower()
        
        if any(word in notes_lower for word in ['cheap', 'cost', 'budget', 'affordable']):
            objectives.append("cost")
        if any(word in notes_lower for word in ['green', 'sustainable', 'eco', 'environment']):
            objectives.append("sustainability")
        if any(word in notes_lower for word in ['beautiful', 'nice', 'aesthetic', 'pretty']):
            objectives.append("aesthetics")
        
        return objectives if objectives else ["aesthetics"]

@dataclass
class DesignSession:
    """Represents an active design session"""
    session_id: str
    user_id: str
    agent: ArchitecturalAgent
    specification: DesignSpecification
    current_scene: Optional[DesignScene] = None
    collaboration_history: List[str] = None
    created_at: str = None
    
    def __post_init__(self):
        if self.collaboration_history is None:
            self.collaboration_history = []
        if self.created_at is None:
            self.created_at = datetime.datetime.now().isoformat()

# Example usage and demonstration
async def demo_architectural_agent():
    """Demonstrate the architectural agent system"""
    print("🚀 Mwarokin AI Architectural Agent Demo")
    print("=" * 50)
    
    # Create design specification
    spec = DesignSpecification(
        design_type=DesignType.HOUSE,
        budget=250000,
        area=120,
        style="modern",
        materials=[MaterialType.WOOD, MaterialType.GLASS],
        rooms=3,
        constraints=["solar orientation", "wind patterns"],
        preferences={"natural_light": "high", "privacy": "medium"}
    )
    
    # Initialize agent
    agent = ArchitecturalAgent()
    
    # Generate initial design
    print("📐 Generating initial design...")
    scene = await agent.generate_design(spec)
    print(f"✅ Created design: {scene.name} with {len(scene.elements)} elements")
    
    # Optimize for cost
    print("💰 Optimizing for cost...")
    optimized_scene = await agent.optimize_design(scene, ["cost"])
    print(f"✅ Optimized design: {optimized_scene.name}")
    
    # Export to HTML
    html_export = agent.export_scene(optimized_scene, "html")
    print(f"📤 Exported scene to HTML ({len(html_export)} bytes)")
    
    # Demonstrate session management
    session_manager = DesignSessionManager()
    session_id = await session_manager.create_session("user_123", spec)
    print(f"👥 Created collaborative session: {session_id}")
    
    # Simulate collaboration
    collaborator_feedback = "Make it more sustainable and cost-effective"
    updated_design = await session_manager.collaborate_on_design(
        session_id, collaborator_feedback
    )
    print(f"🤝 Applied collaborator feedback: {collaborator_feedback}")
    print(f"🎨 Updated design: {updated_design.name}")
    
    return {
        "agent": agent,
        "initial_scene": scene,
        "optimized_scene": optimized_scene,
        "session_manager": session_manager
    }

# Modern async context manager for resource management
class DesignSessionContext:
    """Context manager for design sessions"""
    
    def __init__(self, user_id: str, spec: DesignSpecification):
        self.user_id = user_id
        self.spec = spec
        self.session_manager = DesignSessionManager()
        self.session_id = None
    
    async def __aenter__(self):
        self.session_id = await self.session_manager.create_session(self.user_id, self.spec)
        return await self.session_manager.get_session(self.session_id)
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup resources if needed
        if self.session_id and self.session_id in self.session_manager.active_sessions:
            del self.session_manager.active_sessions[self.session_id]

if __name__ == "__main__":
    # Run the demo
    import math  # Import for math operations used in element generation
    
    # For demonstration, we'll use a simple event loop
    try:
        results = asyncio.run(demo_architectural_agent())
        print("\n🎉 Demo completed successfully!")
        print(f"📊 Agent processed {len(results['agent'].scene_history)} design scenes")
    except Exception as e:
        print(f"❌ Demo error: {e}")
```

This modern Python agentic system provides:

## Key Features:

1. **AI-Powered Design Generation**: Creates architectural designs based on specifications
2. **Multi-Objective Optimization**: Optimizes for cost, sustainability, and aesthetics
3. **Collaborative Design Sessions**: Manages multiple users working on designs
4. **Export Capabilities**: Exports to JSON and HTML with Three.js visualization
5. **Modern Python Features**: Async/await, type hints, dataclasses, context managers

## Agentic Capabilities:

- **Autonomous Design Generation**: Creates complete 3D scenes from specifications
- **Intelligent Optimization**: Applies architectural rules and best practices
- **Natural Language Processing**: Interprets collaborator feedback
- **Learning from History**: Maintains design session history
- **Adaptive Behavior**: Adjusts designs based on multiple objectives

## Integration with Your HTML:

The system can export designs that seamlessly integrate with your Three.js frontend, maintaining the same visual style and interaction patterns.

To use this system, you would need to install the required dependencies and potentially integrate with a database for persistent storage of designs and sessions.