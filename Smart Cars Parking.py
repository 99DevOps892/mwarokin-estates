I'll create a modern Python agentic system for the SmartPark parking management system. This will implement the core functionality using advanced Python patterns and async capabilities.

```python
"""
SmartPark Agentic System
Modern Python implementation of an intelligent parking management system
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, Callable, Any, Awaitable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
import logging
from functools import wraps
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smartpark")

# Type aliases
LicensePlate = str
VehicleType = str
ParkingSpotId = str
AgentId = str

class ParkingStatus(Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"

class VehicleType(Enum):
    STANDARD = "standard"
    SUV = "suv"
    EV = "electric"
    MOTORCYCLE = "motorcycle"

class PaymentStatus(Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"

@dataclass
class Vehicle:
    license_plate: LicensePlate
    vehicle_type: VehicleType
    owner_id: Optional[str] = None
    is_recognized: bool = False

@dataclass
class ParkingSpot:
    id: ParkingSpotId
    zone: str
    number: str
    status: ParkingStatus
    vehicle_type: VehicleType
    hourly_rate: float
    current_vehicle: Optional[Vehicle] = None
    reserved_until: Optional[datetime] = None

@dataclass
class ParkingSession:
    id: str
    vehicle: Vehicle
    spot: ParkingSpot
    entry_time: datetime
    exit_time: Optional[datetime] = None
    total_cost: float = 0.0
    payment_status: PaymentStatus = PaymentStatus.PENDING
    location_pinned: bool = False

@dataclass
class ParkingEvent:
    type: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    agent_id: Optional[AgentId] = None

# Agent Base Class
class Agent(ABC):
    def __init__(self, agent_id: AgentId):
        self.agent_id = agent_id
        self.message_handlers: Dict[str, Callable] = {}
        self.event_handlers: Dict[str, Callable] = {}
        
    @abstractmethod
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    def register_handler(self, message_type: str, handler: Callable):
        self.message_handlers[message_type] = handler
    
    def register_event_handler(self, event_type: str, handler: Callable):
        self.event_handlers[event_type] = handler

# Modern async decorators
def retry_async(max_attempts: int = 3, delay: float = 1.0):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                        await asyncio.sleep(delay)
            raise last_exception
        return wrapper
    return decorator

def timed_async(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = datetime.now()
        result = await func(*args, **kwargs)
        duration = (datetime.now() - start).total_seconds()
        logger.info(f"{func.__name__} completed in {duration:.2f}s")
        return result
    return wrapper

# Core Agents
class LicensePlateRecognitionAgent(Agent):
    def __init__(self, agent_id: AgentId):
        super().__init__(agent_id)
        self.registered_plates = {
            "ABC123": VehicleType.STANDARD,
            "XYZ789": VehicleType.SUV,
            "EV2023": VehicleType.EV,
        }
        self.register_handler("scan_plate", self.handle_scan_plate)
    
    @retry_async(max_attempts=3)
    @timed_async
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        handler = self.message_handlers.get(message.get("type"))
        if handler:
            return await handler(message)
        return {"status": "error", "message": "Unknown message type"}
    
    async def handle_scan_plate(self, message: Dict[str, Any]) -> Dict[str, Any]:
        plate_image_data = message.get("plate_image_data")
        # Simulate plate recognition
        await asyncio.sleep(0.5)  # Simulate processing time
        
        # Mock recognition logic
        recognized_plate = random.choice(list(self.registered_plates.keys()) + ["UNKNOWN"])
        is_recognized = recognized_plate in self.registered_plates
        
        vehicle = Vehicle(
            license_plate=recognized_plate,
            vehicle_type=self.registered_plates.get(recognized_plate, VehicleType.STANDARD),
            is_recognized=is_recognized
        )
        
        return {
            "status": "success",
            "vehicle": vehicle,
            "confidence": 0.95 if is_recognized else 0.3
        }

class ParkingSpotManagerAgent(Agent):
    def __init__(self, agent_id: AgentId):
        super().__init__(agent_id)
        self.spots: Dict[ParkingSpotId, ParkingSpot] = self._initialize_spots()
        self.register_handler("find_available_spot", self.handle_find_spot)
        self.register_handler("reserve_spot", self.handle_reserve_spot)
        self.register_handler("assign_vehicle", self.handle_assign_vehicle)
    
    def _initialize_spots(self) -> Dict[ParkingSpotId, ParkingSpot]:
        spots = {}
        for zone in ["A", "B"]:
            for i in range(1, 6):
                spot_id = f"{zone}{i}"
                spots[spot_id] = ParkingSpot(
                    id=spot_id,
                    zone=zone,
                    number=str(i),
                    status=ParkingStatus.AVAILABLE,
                    vehicle_type=VehicleType.STANDARD,
                    hourly_rate=4.0
                )
        return spots
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        handler = self.message_handlers.get(message.get("type"))
        if handler:
            return await handler(message)
        return {"status": "error", "message": "Unknown message type"}
    
    async def handle_find_spot(self, message: Dict[str, Any]) -> Dict[str, Any]:
        vehicle_type = message.get("vehicle_type", VehicleType.STANDARD)
        available_spots = [
            spot for spot in self.spots.values()
            if spot.status == ParkingStatus.AVAILABLE and spot.vehicle_type == vehicle_type
        ]
        
        if available_spots:
            selected_spot = random.choice(available_spots)
            return {
                "status": "success",
                "spot": selected_spot,
                "available_count": len(available_spots)
            }
        else:
            return {"status": "error", "message": "No available spots"}
    
    async def handle_reserve_spot(self, message: Dict[str, Any]) -> Dict[str, Any]:
        spot_id = message.get("spot_id")
        duration_minutes = message.get("duration_minutes", 30)
        
        if spot_id not in self.spots:
            return {"status": "error", "message": "Invalid spot ID"}
        
        spot = self.spots[spot_id]
        if spot.status != ParkingStatus.AVAILABLE:
            return {"status": "error", "message": "Spot not available"}
        
        spot.status = ParkingStatus.RESERVED
        spot.reserved_until = datetime.now() + timedelta(minutes=duration_minutes)
        
        return {"status": "success", "spot": spot}
    
    async def handle_assign_vehicle(self, message: Dict[str, Any]) -> Dict[str, Any]:
        spot_id = message.get("spot_id")
        vehicle = message.get("vehicle")
        
        if spot_id not in self.spots:
            return {"status": "error", "message": "Invalid spot ID"}
        
        spot = self.spots[spot_id]
        spot.current_vehicle = vehicle
        spot.status = ParkingStatus.OCCUPIED
        
        return {"status": "success", "spot": spot}

class PaymentProcessingAgent(Agent):
    def __init__(self, agent_id: AgentId):
        super().__init__(agent_id)
        self.register_handler("process_payment", self.handle_process_payment)
        self.register_handler("calculate_cost", self.handle_calculate_cost)
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        handler = self.message_handlers.get(message.get("type"))
        if handler:
            return await handler(message)
        return {"status": "error", "message": "Unknown message type"}
    
    async def handle_calculate_cost(self, message: Dict[str, Any]) -> Dict[str, Any]:
        entry_time = message.get("entry_time")
        exit_time = message.get("exit_time", datetime.now())
        hourly_rate = message.get("hourly_rate", 4.0)
        vehicle_type = message.get("vehicle_type", VehicleType.STANDARD)
        
        if isinstance(entry_time, str):
            entry_time = datetime.fromisoformat(entry_time)
        if isinstance(exit_time, str):
            exit_time = datetime.fromisoformat(exit_time)
        
        duration_hours = (exit_time - entry_time).total_seconds() / 3600
        base_cost = duration_hours * hourly_rate
        
        # Apply vehicle type surcharges
        surcharges = {
            VehicleType.STANDARD: 0.0,
            VehicleType.SUV: 2.0,
            VehicleType.EV: -1.0,  # Discount for EVs
            VehicleType.MOTORCYCLE: -2.0
        }
        
        total_cost = max(0, base_cost + surcharges.get(vehicle_type, 0.0))
        
        return {
            "status": "success",
            "total_cost": round(total_cost, 2),
            "duration_hours": round(duration_hours, 2),
            "base_cost": round(base_cost, 2),
            "surcharge": surcharges.get(vehicle_type, 0.0)
        }
    
    @retry_async(max_attempts=2)
    async def handle_process_payment(self, message: Dict[str, Any]) -> Dict[str, Any]:
        amount = message.get("amount")
        payment_method = message.get("payment_method", "credit_card")
        
        # Simulate payment processing
        await asyncio.sleep(0.3)
        
        # Mock payment gateway response
        success = random.random() > 0.1  # 90% success rate
        
        if success:
            return {
                "status": "success",
                "transaction_id": str(uuid.uuid4()),
                "amount_charged": amount,
                "payment_method": payment_method,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": "Payment processing failed",
                "error_code": "INSUFFICIENT_FUNDS"
            }

class BarrierControlAgent(Agent):
    def __init__(self, agent_id: AgentId):
        super().__init__(agent_id)
        self.entry_barrier_open = False
        self.exit_barrier_open = False
        self.register_handler("open_entry_barrier", self.handle_open_entry)
        self.register_handler("open_exit_barrier", self.handle_open_exit)
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        handler = self.message_handlers.get(message.get("type"))
        if handler:
            return await handler(message)
        return {"status": "error", "message": "Unknown message type"}
    
    async def handle_open_entry(self, message: Dict[str, Any]) -> Dict[str, Any]:
        self.entry_barrier_open = True
        logger.info("Entry barrier opened")
        
        # Simulate barrier closing after delay
        asyncio.create_task(self._close_barrier_after_delay("entry"))
        
        return {"status": "success", "barrier": "entry", "state": "open"}
    
    async def handle_open_exit(self, message: Dict[str, Any]) -> Dict[str, Any]:
        self.exit_barrier_open = True
        logger.info("Exit barrier opened")
        
        # Simulate barrier closing after delay
        asyncio.create_task(self._close_barrier_after_delay("exit"))
        
        return {"status": "success", "barrier": "exit", "state": "open"}
    
    async def _close_barrier_after_delay(self, barrier_type: str):
        await asyncio.sleep(5)  # Barrier stays open for 5 seconds
        if barrier_type == "entry":
            self.entry_barrier_open = False
        else:
            self.exit_barrier_open = False
        logger.info(f"{barrier_type} barrier closed")

# Main Orchestrator Agent
class SmartParkOrchestrator:
    def __init__(self):
        self.agents: Dict[AgentId, Agent] = {}
        self.active_sessions: Dict[str, ParkingSession] = {}
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize all specialized agents"""
        agents = [
            LicensePlateRecognitionAgent("lpr_agent"),
            ParkingSpotManagerAgent("spot_manager_agent"),
            PaymentProcessingAgent("payment_agent"),
            BarrierControlAgent("barrier_agent"),
        ]
        
        for agent in agents:
            self.agents[agent.agent_id] = agent
    
    async def send_message(self, agent_id: AgentId, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send message to specific agent"""
        if agent_id not in self.agents:
            return {"status": "error", "message": f"Unknown agent: {agent_id}"}
        
        agent = self.agents[agent_id]
        return await agent.process_message(message)
    
    async def process_vehicle_entry(self, plate_image_data: str) -> Dict[str, Any]:
        """Complete vehicle entry process"""
        logger.info("Processing vehicle entry...")
        
        # Step 1: License plate recognition
        lpr_result = await self.send_message("lpr_agent", {
            "type": "scan_plate",
            "plate_image_data": plate_image_data
        })
        
        if lpr_result["status"] != "success":
            return lpr_result
        
        vehicle = lpr_result["vehicle"]
        
        # Step 2: Find available parking spot
        spot_result = await self.send_message("spot_manager_agent", {
            "type": "find_available_spot",
            "vehicle_type": vehicle.vehicle_type
        })
        
        if spot_result["status"] != "success":
            return spot_result
        
        spot = spot_result["spot"]
        
        # Step 3: Assign vehicle to spot
        assign_result = await self.send_message("spot_manager_agent", {
            "type": "assign_vehicle",
            "spot_id": spot.id,
            "vehicle": vehicle
        })
        
        # Step 4: Create parking session
        session = ParkingSession(
            id=str(uuid.uuid4()),
            vehicle=vehicle,
            spot=spot,
            entry_time=datetime.now()
        )
        self.active_sessions[session.id] = session
        
        # Step 5: Open entry barrier
        barrier_result = await self.send_message("barrier_agent", {
            "type": "open_entry_barrier"
        })
        
        return {
            "status": "success",
            "session_id": session.id,
            "vehicle": vehicle,
            "assigned_spot": spot,
            "barrier_status": barrier_result
        }
    
    async def process_vehicle_exit(self, session_id: str, plate_image_data: str) -> Dict[str, Any]:
        """Complete vehicle exit process"""
        logger.info(f"Processing vehicle exit for session {session_id}")
        
        if session_id not in self.active_sessions:
            return {"status": "error", "message": "Invalid session ID"}
        
        session = self.active_sessions[session_id]
        session.exit_time = datetime.now()
        
        # Step 1: Verify license plate
        lpr_result = await self.send_message("lpr_agent", {
            "type": "scan_plate",
            "plate_image_data": plate_image_data
        })
        
        if (lpr_result["status"] != "success" or 
            lpr_result["vehicle"].license_plate != session.vehicle.license_plate):
            return {"status": "error", "message": "License plate verification failed"}
        
        # Step 2: Calculate parking cost
        cost_result = await self.send_message("payment_agent", {
            "type": "calculate_cost",
            "entry_time": session.entry_time.isoformat(),
            "exit_time": session.exit_time.isoformat(),
            "hourly_rate": session.spot.hourly_rate,
            "vehicle_type": session.vehicle.vehicle_type
        })
        
        if cost_result["status"] != "success":
            return cost_result
        
        session.total_cost = cost_result["total_cost"]
        
        # Step 3: Process payment
        payment_result = await self.send_message("payment_agent", {
            "type": "process_payment",
            "amount": session.total_cost
        })
        
        if payment_result["status"] == "success":
            session.payment_status = PaymentStatus.PROCESSED
            
            # Step 4: Open exit barrier
            barrier_result = await self.send_message("barrier_agent", {
                "type": "open_exit_barrier"
            })
            
            # Step 5: Free up parking spot
            await self.send_message("spot_manager_agent", {
                "type": "assign_vehicle",
                "spot_id": session.spot.id,
                "vehicle": None
            })
            
            # Remove session
            del self.active_sessions[session_id]
            
            return {
                "status": "success",
                "session": session,
                "payment": payment_result,
                "barrier_status": barrier_result
            }
        else:
            return payment_result
    
    async def get_parking_status(self) -> Dict[str, Any]:
        """Get current parking lot status"""
        spot_manager = self.agents["spot_manager_agent"]
        available_spots = len([s for s in spot_manager.spots.values() if s.status == ParkingStatus.AVAILABLE])
        total_spots = len(spot_manager.spots.values())
        
        return {
            "total_spots": total_spots,
            "available_spots": available_spots,
            "occupancy_rate": (total_spots - available_spots) / total_spots,
            "active_sessions": len(self.active_sessions),
            "timestamp": datetime.now().isoformat()
        }

# Advanced async context manager for session management
@asynccontextmanager
async def parking_session_manager(orchestrator: SmartParkOrchestrator, plate_image: str):
    """Context manager for parking session lifecycle"""
    entry_result = await orchestrator.process_vehicle_entry(plate_image)
    
    try:
        yield entry_result
    except Exception as e:
        logger.error(f"Parking session error: {e}")
        raise
    finally:
        # Cleanup logic if needed
        pass

# Modern functional programming utilities
class ParkingSystem:
    def __init__(self):
        self.orchestrator = SmartParkOrchestrator()
    
    @staticmethod
    def compose_agents(*agents: Agent) -> Callable:
        """Function composition for agent processing pipeline"""
        def composed_pipeline(input_data: Dict[str, Any]) -> Awaitable[Dict[str, Any]]:
            async def process():
                result = input_data
                for agent in agents:
                    result = await agent.process_message(result)
                return result
            return process()
        return composed_pipeline
    
    async def run_agent_pipeline(self, pipeline: Callable, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent pipeline with error handling"""
        try:
            return await pipeline(input_data)
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def create_entry_pipeline(self) -> Callable:
        """Create a composed pipeline for vehicle entry"""
        lpr_agent = self.orchestrator.agents["lpr_agent"]
        spot_agent = self.orchestrator.agents["spot_manager_agent"]
        barrier_agent = self.orchestrator.agents["barrier_agent"]
        
        return self.compose_agents(lpr_agent, spot_agent, barrier_agent)

# Example usage and simulation
async def simulate_parking_operations():
    """Simulate complete parking operations"""
    system = ParkingSystem()
    
    logger.info("Starting SmartPark simulation...")
    
    # Simulate multiple vehicles entering and exiting
    vehicles = [
        "plate_car_1.jpg",
        "plate_car_2.jpg", 
        "plate_suv_1.jpg",
        "plate_ev_1.jpg"
    ]
    
    sessions = []
    
    # Vehicle entries
    for i, plate_image in enumerate(vehicles):
        logger.info(f"Vehicle {i+1} arriving...")
        
        async with parking_session_manager(system.orchestrator, plate_image) as entry_result:
            if entry_result["status"] == "success":
                sessions.append(entry_result["session_id"])
                logger.info(f"Vehicle parked at {entry_result['assigned_spot'].id}")
            
            await asyncio.sleep(2)  # Simulate time between arrivals
    
    # Check parking status
    status = await system.orchestrator.get_parking_status()
    logger.info(f"Parking status: {status}")
    
    # Vehicle exits
    for session_id in sessions:
        logger.info(f"Vehicle with session {session_id} exiting...")
        
        exit_result = await system.orchestrator.process_vehicle_exit(
            session_id, "exit_plate.jpg"
        )
        
        if exit_result["status"] == "success":
            session = exit_result["session"]
            logger.info(f"Vehicle exited. Paid ${session.total_cost}")
        
        await asyncio.sleep(3)  # Simulate time between exits
    
    # Final status
    final_status = await system.orchestrator.get_parking_status()
    logger.info(f"Final parking status: {final_status}")

if __name__ == "__main__":
    # Run the simulation
    asyncio.run(simulate_parking_operations())
```

This modern Python agentic system implements:

## Key Features:

1. **Agent-Based Architecture**: Specialized agents for LPR, spot management, payments, and barrier control
2. **Async/Await Patterns**: Full asynchronous operation for high concurrency
3. **Functional Programming**: Composable agent pipelines and decorators
4. **Modern Python Features**:
   - Type hints throughout
   - Dataclasses for data structures
   - Async context managers
   - Custom decorators for retry and timing
   - Enum classes for state management

5. **Advanced Patterns**:
   - Message passing between agents
   - Error handling with retry logic
   - Event-driven architecture
   - Resource management with context managers

6. **Realistic Simulation**:
   - Complete parking workflow
   - Payment processing with failure simulation
   - Dynamic spot management
   - Real-time status monitoring

The system is designed to be scalable, maintainable, and can easily integrate with real hardware components while maintaining clean separation of concerns through the agentic architecture.