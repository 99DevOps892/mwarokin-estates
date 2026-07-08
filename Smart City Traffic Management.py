I'll create an AI automated agentic Python system for smart city monitoring that can work with your 3D visualization. Here's a comprehensive solution:

```python
import asyncio
import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass
import aiohttp
import websockets
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SmartCityAgent")

class TrafficLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CONGESTED = "congested"

class IncidentType(Enum):
    ACCIDENT = "accident"
    CONSTRUCTION = "construction"
    ROAD_CLOSURE = "road_closure"
    WEATHER = "weather"
    VEHICLE_BREAKDOWN = "vehicle_breakdown"

@dataclass
class Vehicle:
    id: str
    vehicle_type: str
    position: Dict[str, float]
    speed: float
    route: List[Dict[str, float]]
    emergency: bool = False
    ev_vehicle: bool = False

@dataclass
class TrafficIncident:
    id: str
    incident_type: IncidentType
    location: Dict[str, float]
    severity: str
    description: str
    timestamp: datetime
    affected_vehicles: List[str]
    resolved: bool = False

@dataclass
class TrafficMetrics:
    flow_rate: float
    average_speed: float
    congestion_level: TrafficLevel
    vehicle_count: int
    incident_count: int
    timestamp: datetime

class SmartCityTrafficAgent:
    """
    AI Agent for autonomous smart city traffic monitoring and management
    """
    
    def __init__(self, city_name: str = "Mwarokin"):
        self.city_name = city_name
        self.vehicles: Dict[str, Vehicle] = {}
        self.incidents: Dict[str, TrafficIncident] = {}
        self.traffic_metrics = TrafficMetrics(0, 0, TrafficLevel.LOW, 0, 0, datetime.now())
        self.emergency_vehicles: List[str] = []
        self.ev_stations = []
        self.parking_facilities = []
        self.is_running = False
        
        # AI Decision thresholds
        self.congestion_threshold = 0.7
        self.emergency_clearance_priority = 10
        self.reporting_interval = 5  # seconds
        
    async def initialize_city_infrastructure(self):
        """Initialize smart city infrastructure"""
        logger.info(f"Initializing {self.city_name} smart city infrastructure")
        
        # Simulate EV charging stations
        self.ev_stations = [
            {"id": "ev_1", "location": {"x": 25, "z": 25}, "available_ports": 4, "in_use": 2},
            {"id": "ev_2", "location": {"x": -25, "z": -25}, "available_ports": 6, "in_use": 3},
            {"id": "ev_3", "location": {"x": 25, "z": -25}, "available_ports": 2, "in_use": 1},
        ]
        
        # Simulate parking facilities
        self.parking_facilities = [
            {"id": "parking_1", "location": {"x": 15, "z": 15}, "capacity": 100, "available": 45},
            {"id": "parking_2", "location": {"x": -15, "z": -15}, "capacity": 150, "available": 89},
        ]
        
        # Generate initial vehicle population
        await self.generate_initial_vehicles(50)
        
        logger.info("City infrastructure initialized successfully")
    
    async def generate_initial_vehicles(self, count: int):
        """Generate initial vehicle population"""
        vehicle_types = ["sedan", "suv", "truck", "bus", "motorcycle", "emergency"]
        
        for i in range(count):
            vehicle_id = f"vehicle_{i+1:04d}"
            vehicle_type = random.choice(vehicle_types)
            is_emergency = vehicle_type == "emergency"
            is_ev = random.random() < 0.3  # 30% chance of being EV
            
            # Generate random position on roads
            position = self._generate_road_position()
            
            vehicle = Vehicle(
                id=vehicle_id,
                vehicle_type=vehicle_type,
                position=position,
                speed=random.uniform(5, 15) if not is_emergency else random.uniform(10, 25),
                route=self._generate_route(position),
                emergency=is_emergency,
                ev_vehicle=is_ev
            )
            
            self.vehicles[vehicle_id] = vehicle
            
            if is_emergency:
                self.emergency_vehicles.append(vehicle_id)
    
    def _generate_road_position(self) -> Dict[str, float]:
        """Generate a position on the road network"""
        road_positions = [-40, -20, 0, 20, 40]
        is_horizontal = random.choice([True, False])
        
        if is_horizontal:
            return {"x": random.uniform(-45, 45), "z": random.choice(road_positions)}
        else:
            return {"x": random.choice(road_positions), "z": random.uniform(-45, 45)}
    
    def _generate_route(self, start_position: Dict[str, float]) -> List[Dict[str, float]]:
        """Generate a route for a vehicle"""
        route = [start_position]
        
        # Add 2-4 additional points to the route
        num_points = random.randint(2, 4)
        for _ in range(num_points):
            route.append(self._generate_road_position())
        
        return route
    
    async def start_monitoring(self):
        """Start the autonomous monitoring system"""
        self.is_running = True
        logger.info("Starting smart city traffic monitoring system")
        
        # Start all monitoring tasks
        monitoring_tasks = [
            self.continuous_traffic_analysis(),
            self.incident_detection_system(),
            self.emergency_response_coordination(),
            self.traffic_flow_optimization(),
            self.data_reporting_service(),
            self.simulate_real_time_events()
        ]
        
        await asyncio.gather(*monitoring_tasks)
    
    async def continuous_traffic_analysis(self):
        """Continuously analyze traffic patterns and metrics"""
        while self.is_running:
            try:
                # Calculate traffic metrics
                total_vehicles = len(self.vehicles)
                if total_vehicles > 0:
                    avg_speed = sum(v.speed for v in self.vehicles.values()) / total_vehicles
                    flow_rate = self._calculate_flow_rate()
                    congestion_level = self._assess_congestion_level(flow_rate, avg_speed)
                    
                    self.traffic_metrics = TrafficMetrics(
                        flow_rate=flow_rate,
                        average_speed=avg_speed,
                        congestion_level=congestion_level,
                        vehicle_count=total_vehicles,
                        incident_count=len([i for i in self.incidents.values() if not i.resolved]),
                        timestamp=datetime.now()
                    )
                
                await asyncio.sleep(2)  # Analyze every 2 seconds
                
            except Exception as e:
                logger.error(f"Error in traffic analysis: {e}")
                await asyncio.sleep(5)
    
    def _calculate_flow_rate(self) -> float:
        """Calculate traffic flow rate (0-1 scale)"""
        max_vehicles = 100  # Theoretical maximum for the city
        current_vehicles = len(self.vehicles)
        
        # Adjust flow rate based on average speed and incidents
        base_flow = current_vehicles / max_vehicles
        speed_factor = sum(v.speed for v in self.vehicles.values()) / (len(self.vehicles) * 25)  # Normalize by max speed
        incident_factor = 1 - (len(self.incidents) * 0.1)  # Each incident reduces flow
        
        return min(1.0, base_flow * speed_factor * incident_factor)
    
    def _assess_congestion_level(self, flow_rate: float, avg_speed: float) -> TrafficLevel:
        """Assess current congestion level"""
        if flow_rate < 0.3 or avg_speed > 20:
            return TrafficLevel.LOW
        elif flow_rate < 0.6 or avg_speed > 15:
            return TrafficLevel.MEDIUM
        elif flow_rate < 0.8 or avg_speed > 10:
            return TrafficLevel.HIGH
        else:
            return TrafficLevel.CONGESTED
    
    async def incident_detection_system(self):
        """AI-powered incident detection and management"""
        while self.is_running:
            try:
                # Simulate random incident detection
                if random.random() < 0.05:  # 5% chance per cycle
                    await self._detect_and_handle_incident()
                
                # Check for incident resolution
                await self._check_incident_resolution()
                
                await asyncio.sleep(3)  # Check every 3 seconds
                
            except Exception as e:
                logger.error(f"Error in incident detection: {e}")
                await asyncio.sleep(5)
    
    async def _detect_and_handle_incident(self):
        """Detect and handle new traffic incidents"""
        incident_types = list(IncidentType)
        incident_type = random.choice(incident_types)
        
        # Generate incident location
        location = self._generate_road_position()
        
        # Create incident
        incident_id = f"incident_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        incident = TrafficIncident(
            id=incident_id,
            incident_type=incident_type,
            location=location,
            severity=random.choice(["low", "medium", "high"]),
            description=f"{incident_type.value.replace('_', ' ').title()} detected",
            timestamp=datetime.now(),
            affected_vehicles=self._find_affected_vehicles(location)
        )
        
        self.incidents[incident_id] = incident
        
        # Take automatic actions based on incident type and severity
        await self._handle_incident_actions(incident)
        
        logger.warning(f"New incident detected: {incident.description} at {location}")
    
    def _find_affected_vehicles(self, location: Dict[str, float]) -> List[str]:
        """Find vehicles affected by an incident"""
        affected = []
        for vehicle_id, vehicle in self.vehicles.items():
            distance = ((vehicle.position['x'] - location['x'])**2 + 
                       (vehicle.position['z'] - location['z'])**2)**0.5
            if distance < 15:  # Vehicles within 15 units are affected
                affected.append(vehicle_id)
        return affected
    
    async def _handle_incident_actions(self, incident: TrafficIncident):
        """Take automatic actions for detected incidents"""
        if incident.incident_type == IncidentType.ACCIDENT and incident.severity == "high":
            # Dispatch nearest emergency vehicle
            await self._dispatch_emergency_services(incident)
        
        elif incident.incident_type == IncidentType.CONSTRUCTION:
            # Reroute traffic around construction
            await self._reroute_traffic(incident.location, 20)
        
        elif incident.incident_type == IncidentType.WEATHER:
            # Adjust speed limits for safety
            await self._adjust_speed_limits(0.7)  # Reduce to 70% of normal
    
    async def _dispatch_emergency_services(self, incident: TrafficIncident):
        """Dispatch emergency services to incident location"""
        if not self.emergency_vehicles:
            logger.warning("No emergency vehicles available for dispatch")
            return
        
        # Find nearest available emergency vehicle
        nearest_vehicle_id = min(
            self.emergency_vehicles,
            key=lambda vid: self._calculate_distance(
                self.vehicles[vid].position, incident.location
            )
        )
        
        # Update vehicle route to incident location
        emergency_vehicle = self.vehicles[nearest_vehicle_id]
        emergency_vehicle.route = [emergency_vehicle.position, incident.location]
        emergency_vehicle.speed = 25  # High speed for emergency response
        
        logger.info(f"Dispatched emergency vehicle {nearest_vehicle_id} to incident {incident.id}")
    
    async def _reroute_traffic(self, location: Dict[str, float], radius: float):
        """Reroute traffic around a specific location"""
        rerouted_count = 0
        for vehicle in self.vehicles.values():
            if not vehicle.emergency:  # Don't reroute emergency vehicles
                distance = self._calculate_distance(vehicle.position, location)
                if distance < radius:
                    # Generate new route avoiding the area
                    vehicle.route = self._generate_avoidance_route(vehicle.position, location, radius)
                    rerouted_count += 1
        
        logger.info(f"Rerouted {rerouted_count} vehicles around restricted area")
    
    def _generate_avoidance_route(self, start: Dict[str, float], avoid: Dict[str, float], radius: float) -> List[Dict[str, float]]:
        """Generate a route that avoids a specific area"""
        # Simple avoidance: move perpendicular to direct path
        route = [start]
        
        # Calculate direction vector from start to avoid
        dx = avoid['x'] - start['x']
        dz = avoid['z'] - start['z']
        
        # Create a waypoint that goes around the avoidance area
        if abs(dx) > abs(dz):
            # Go around in z-direction
            waypoint = {"x": start['x'], "z": start['z'] + (radius * 2 if dz >= 0 else -radius * 2)}
        else:
            # Go around in x-direction
            waypoint = {"x": start['x'] + (radius * 2 if dx >= 0 else -radius * 2), "z": start['z']}
        
        route.append(waypoint)
        
        # Add final destination (simplified)
        final_dest = self._generate_road_position()
        route.append(final_dest)
        
        return route
    
    async def _adjust_speed_limits(self, factor: float):
        """Adjust speed limits for all vehicles"""
        for vehicle in self.vehicles.values():
            if not vehicle.emergency:
                vehicle.speed *= factor
        
        logger.info(f"Adjusted speed limits to {factor*100}% of normal")
    
    async def _check_incident_resolution(self):
        """Check and resolve old incidents"""
        current_time = datetime.now()
        resolved_incidents = []
        
        for incident_id, incident in self.incidents.items():
            if not incident.resolved:
                time_since_incident = current_time - incident.timestamp
                
                # Auto-resolve incidents after a certain time
                if time_since_incident > timedelta(minutes=5):
                    incident.resolved = True
                    resolved_incidents.append(incident_id)
                    
                    # Restore normal operations
                    await self._restore_normal_operations(incident)
        
        for incident_id in resolved_incidents:
            logger.info(f"Incident {incident_id} has been resolved")
    
    async def _restore_normal_operations(self, incident: TrafficIncident):
        """Restore normal operations after incident resolution"""
        # Reset speed limits if they were adjusted
        if incident.incident_type == IncidentType.WEATHER:
            for vehicle in self.vehicles.values():
                if not vehicle.emergency:
                    vehicle.speed = random.uniform(5, 15)  # Restore normal speed range
    
    async def emergency_response_coordination(self):
        """Coordinate emergency vehicle movement and priority"""
        while self.is_running:
            try:
                for vehicle_id in self.emergency_vehicles:
                    vehicle = self.vehicles[vehicle_id]
                    
                    # Clear path for emergency vehicles
                    await self._clear_emergency_path(vehicle)
                    
                    # Update emergency vehicle movement
                    await self._update_emergency_vehicle_movement(vehicle)
                
                await asyncio.sleep(1)  # Update every second
                
            except Exception as e:
                logger.error(f"Error in emergency coordination: {e}")
                await asyncio.sleep(3)
    
    async def _clear_emergency_path(self, emergency_vehicle: Vehicle):
        """Clear path for emergency vehicles by rerouting nearby traffic"""
        clearance_radius = 30  # Units
        
        for vehicle in self.vehicles.values():
            if not vehicle.emergency:
                distance = self._calculate_distance(vehicle.position, emergency_vehicle.position)
                if distance < clearance_radius:
                    # Reroute non-emergency vehicles away from emergency vehicle
                    avoidance_vector = self._calculate_avoidance_vector(vehicle.position, emergency_vehicle.position)
                    new_position = {
                        'x': vehicle.position['x'] + avoidance_vector['x'],
                        'z': vehicle.position['z'] + avoidance_vector['z']
                    }
                    
                    # Ensure new position is on road
                    new_position = self._snap_to_road(new_position)
                    vehicle.position = new_position
    
    def _calculate_avoidance_vector(self, vehicle_pos: Dict[str, float], emergency_pos: Dict[str, float]) -> Dict[str, float]:
        """Calculate vector to move vehicle away from emergency vehicle"""
        dx = vehicle_pos['x'] - emergency_pos['x']
        dz = vehicle_pos['z'] - emergency_pos['z']
        
        # Normalize and scale
        distance = max(0.1, (dx**2 + dz**2)**0.5)
        scale = 5 / distance  # Move 5 units away
        
        return {'x': dx * scale, 'z': dz * scale}
    
    def _snap_to_road(self, position: Dict[str, float]) -> Dict[str, float]:
        """Snap a position to the nearest road"""
        road_positions = [-40, -20, 0, 20, 40]
        
        # Find closest road in x and z directions
        closest_x = min(road_positions, key=lambda x: abs(x - position['x']))
        closest_z = min(road_positions, key=lambda z: abs(z - position['z']))
        
        # Determine if horizontal or vertical road is closer
        dist_to_horizontal = abs(position['z'] - closest_z)
        dist_to_vertical = abs(position['x'] - closest_x)
        
        if dist_to_horizontal < dist_to_vertical:
            return {'x': position['x'], 'z': closest_z}
        else:
            return {'x': closest_x, 'z': position['z']}
    
    async def _update_emergency_vehicle_movement(self, vehicle: Vehicle):
        """Update emergency vehicle movement along its route"""
        if len(vehicle.route) > 1:
            current_target = vehicle.route[1]
            current_pos = vehicle.position
            
            # Move toward target
            dx = current_target['x'] - current_pos['x']
            dz = current_target['z'] - current_pos['z']
            distance = (dx**2 + dz**2)**0.5
            
            if distance < 2:  # Reached target
                vehicle.route.pop(0)  # Remove current position
                if len(vehicle.route) == 1:  # Reached final destination
                    vehicle.route = self._generate_route(vehicle.position)
            else:
                # Move toward target
                move_distance = min(vehicle.speed * 0.1, distance)  # Scale speed for animation
                vehicle.position['x'] += (dx / distance) * move_distance
                vehicle.position['z'] += (dz / distance) * move_distance
    
    async def traffic_flow_optimization(self):
        """AI-driven traffic flow optimization"""
        while self.is_running:
            try:
                # Analyze traffic patterns and optimize flow
                if self.traffic_metrics.congestion_level in [TrafficLevel.HIGH, TrafficLevel.CONGESTED]:
                    await self._implement_traffic_optimization()
                
                await asyncio.sleep(10)  # Optimize every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in traffic optimization: {e}")
                await asyncio.sleep(10)
    
    async def _implement_traffic_optimization(self):
        """Implement traffic optimization strategies"""
        logger.info("Implementing traffic flow optimization strategies")
        
        # Strategy 1: Dynamic lane management
        await self._adjust_traffic_distribution()
        
        # Strategy 2: Coordinate traffic light timing (simulated)
        await self._optimize_traffic_signals()
        
        # Strategy 3: Suggest alternative routes
        await self._suggest_alternative_routes()
    
    async def _adjust_traffic_distribution(self):
        """Adjust traffic distribution across the city"""
        # Analyze traffic density in different areas
        areas = {
            "northeast": {"x_range": (0, 50), "z_range": (0, 50)},
            "northwest": {"x_range": (-50, 0), "z_range": (0, 50)},
            "southeast": {"x_range": (0, 50), "z_range": (-50, 0)},
            "southwest": {"x_range": (-50, 0), "z_range": (-50, 0)},
        }
        
        area_density = {}
        for area_name, bounds in areas.items():
            count = sum(1 for v in self.vehicles.values() 
                       if bounds['x_range'][0] <= v.position['x'] <= bounds['x_range'][1] and
                          bounds['z_range'][0] <= v.position['z'] <= bounds['z_range'][1])
            area_density[area_name] = count
        
        # Reroute vehicles from congested areas
        max_density_area = max(area_density, key=area_density.get)
        min_density_area = min(area_density, key=area_density.get)
        
        if area_density[max_density_area] > area_density[min_density_area] * 1.5:
            await self._balance_traffic_distribution(max_density_area, min_density_area, areas)
    
    async def _balance_traffic_distribution(self, from_area: str, to_area: str, areas: Dict):
        """Balance traffic between two areas"""
        bounds_from = areas[from_area]
        bounds_to = areas[to_area]
        
        rerouted = 0
        for vehicle in self.vehicles.values():
            if (bounds_from['x_range'][0] <= vehicle.position['x'] <= bounds_from['x_range'][1] and
                bounds_from['z_range'][0] <= vehicle.position['z'] <= bounds_from['z_range'][1]):
                
                # Generate route toward less congested area
                target_pos = {
                    'x': random.uniform(bounds_to['x_range'][0], bounds_to['x_range'][1]),
                    'z': random.uniform(bounds_to['z_range'][0], bounds_to['z_range'][1])
                }
                target_pos = self._snap_to_road(target_pos)
                
                vehicle.route = [vehicle.position, target_pos]
                rerouted += 1
                
                if rerouted >= 5:  # Limit number of reroutes per cycle
                    break
        
        if rerouted > 0:
            logger.info(f"Rerouted {rerouted} vehicles from {from_area} to {to_area}")
    
    async def _optimize_traffic_signals(self):
        """Optimize traffic signal timing (simulated)"""
        # In a real implementation, this would interface with traffic light APIs
        logger.info("Optimizing traffic signal timing based on current flow patterns")
    
    async def _suggest_alternative_routes(self):
        """Suggest alternative routes to drivers (simulated)"""
        # In a real implementation, this would push notifications to navigation apps
        logger.info("Broadcasting alternative route suggestions for congested areas")
    
    async def data_reporting_service(self):
        """Provide real-time data reporting for the dashboard"""
        while self.is_running:
            try:
                # Generate comprehensive report
                report = self._generate_traffic_report()
                
                # In a real implementation, this would send data to the frontend
                # via WebSocket or REST API
                
                await asyncio.sleep(self.reporting_interval)
                
            except Exception as e:
                logger.error(f"Error in data reporting: {e}")
                await asyncio.sleep(5)
    
    def _generate_traffic_report(self) -> Dict[str, Any]:
        """Generate comprehensive traffic report"""
        return {
            "timestamp": datetime.now().isoformat(),
            "city_name": self.city_name,
            "metrics": {
                "traffic_flow": self.traffic_metrics.flow_rate,
                "average_speed": self.traffic_metrics.average_speed,
                "congestion_level": self.traffic_metrics.congestion_level.value,
                "vehicle_count": self.traffic_metrics.vehicle_count,
                "incident_count": self.traffic_metrics.incident_count,
            },
            "vehicles": [
                {
                    "id": v.id,
                    "type": v.vehicle_type,
                    "position": v.position,
                    "speed": v.speed,
                    "emergency": v.emergency,
                    "ev": v.ev_vehicle
                } for v in self.vehicles.values()
            ],
            "incidents": [
                {
                    "id": i.id,
                    "type": i.incident_type.value,
                    "location": i.location,
                    "severity": i.severity,
                    "description": i.description,
                    "resolved": i.resolved,
                    "affected_vehicles": i.affected_vehicles
                } for i in self.incidents.values() if not i.resolved
            ],
            "infrastructure": {
                "ev_stations": self.ev_stations,
                "parking_facilities": self.parking_facilities
            }
        }
    
    async def simulate_real_time_events(self):
        """Simulate real-time city events"""
        while self.is_running:
            try:
                # Random vehicle events
                await self._simulate_vehicle_events()
                
                # Infrastructure updates
                await self._update_infrastructure_status()
                
                await asyncio.sleep(8)  # Simulate events every 8 seconds
                
            except Exception as e:
                logger.error(f"Error in event simulation: {e}")
                await asyncio.sleep(10)
    
    async def _simulate_vehicle_events(self):
        """Simulate random vehicle events"""
        # Randomly add or remove vehicles
        if random.random() < 0.1:  # 10% chance to add vehicle
            await self._add_random_vehicle()
        
        if len(self.vehicles) > 60 and random.random() < 0.05:  # 5% chance to remove vehicle if many exist
            await self._remove_random_vehicle()
        
        # Random vehicle behavior changes
        for vehicle in list(self.vehicles.values()):
            if random.random() < 0.02:  # 2% chance per vehicle
                # Change speed
                if vehicle.emergency:
                    vehicle.speed = random.uniform(15, 25)
                else:
                    vehicle.speed = random.uniform(5, 15)
                
                # Occasionally change route
                if random.random() < 0.1:
                    vehicle.route = self._generate_route(vehicle.position)
    
    async def _add_random_vehicle(self):
        """Add a random vehicle to the simulation"""
        vehicle_id = f"vehicle_{len(self.vehicles) + 1:04d}"
        vehicle_types = ["sedan", "suv", "truck", "bus", "motorcycle"]
        
        vehicle = Vehicle(
            id=vehicle_id,
            vehicle_type=random.choice(vehicle_types),
            position=self._generate_road_position(),
            speed=random.uniform(5, 15),
            route=self._generate_route(self._generate_road_position()),
            emergency=False,
            ev_vehicle=random.random() < 0.3
        )
        
        self.vehicles[vehicle_id] = vehicle
        logger.debug(f"Added new vehicle: {vehicle_id}")
    
    async def _remove_random_vehicle(self):
        """Remove a random vehicle from the simulation"""
        if self.vehicles:
            vehicle_id = random.choice(list(self.vehicles.keys()))
            if vehicle_id not in self.emergency_vehicles:  # Don't remove emergency vehicles
                del self.vehicles[vehicle_id]
                logger.debug(f"Removed vehicle: {vehicle_id}")
    
    async def _update_infrastructure_status(self):
        """Update infrastructure status (EV stations, parking, etc.)"""
        # Update EV station availability
        for station in self.ev_stations:
            station["in_use"] = random.randint(0, station["available_ports"])
        
        # Update parking availability
        for parking in self.parking_facilities:
            parking["available"] = random.randint(0, parking["capacity"])
    
    def _calculate_distance(self, pos1: Dict[str, float], pos2: Dict[str, float]) -> float:
        """Calculate distance between two positions"""
        return ((pos1['x'] - pos2['x'])**2 + (pos1['z'] - pos2['z'])**2)**0.5
    
    async def stop_monitoring(self):
        """Stop the monitoring system"""
        self.is_running = False
        logger.info("Smart city traffic monitoring system stopped")
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current system state for external access"""
        return self._generate_traffic_report()


class WebSocketDataServer:
    """WebSocket server to provide real-time data to the frontend"""
    
    def __init__(self, traffic_agent: SmartCityTrafficAgent, host: str = "localhost", port: int = 8765):
        self.traffic_agent = traffic_agent
        self.host = host
        self.port = port
        self.connected_clients = set()
    
    async def start_server(self):
        """Start the WebSocket server"""
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()  # Run forever
    
    async def handle_client(self, websocket, path):
        """Handle incoming WebSocket connections"""
        self.connected_clients.add(websocket)
        logger.info("New client connected to WebSocket server")
        
        try:
            # Send initial data
            initial_data = self.traffic_agent.get_current_state()
            await websocket.send(json.dumps(initial_data))
            
            # Keep connection alive and send periodic updates
            while True:
                await asyncio.sleep(5)  # Send updates every 5 seconds
                current_data = self.traffic_agent.get_current_state()
                await websocket.send(json.dumps(current_data))
                
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected from WebSocket server")
        finally:
            self.connected_clients.remove(websocket)


# Main execution
async def main():
    """Main function to run the smart city monitoring system"""
    
    # Initialize the AI traffic agent
    traffic_agent = SmartCityTrafficAgent("Mwarokin")
    
    # Initialize city infrastructure
    await traffic_agent.initialize_city_infrastructure()
    
    # Start WebSocket server for frontend communication
    websocket_server = WebSocketDataServer(traffic_agent)
    
    # Run both the monitoring system and WebSocket server
    await asyncio.gather(
        traffic_agent.start_monitoring(),
        websocket_server.start_server()
    )


if __name__ == "__main__":
    # Run the smart city monitoring system
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Smart city monitoring system shutdown requested")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
```

This AI automated agentic system provides:

## Key Features:

1. **Autonomous Traffic Monitoring**: Continuous analysis of traffic patterns, flow rates, and congestion levels

2. **AI-Powered Incident Detection**: Automatic detection and handling of traffic incidents with appropriate responses

3. **Emergency Vehicle Coordination**: Priority routing and path clearing for emergency services

4. **Traffic Flow Optimization**: Dynamic routing, traffic distribution balancing, and congestion management

5. **Real-time Data Reporting**: Comprehensive reporting system for dashboard integration

6. **Smart Infrastructure Management**: EV station monitoring, parking availability, and infrastructure updates

## Integration with Your 3D Visualization:

The system includes a WebSocket server that can provide real-time data to your frontend. To integrate:

1. **Add this to your HTML** (after the existing script):
```html
<script>
// WebSocket connection for real-time data
const socket = new WebSocket('ws://localhost:8765');

socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    updateVisualizationWithRealData(data);
};

function updateVisualizationWithRealData(trafficData) {
    // Update vehicles in 3D scene
    trafficData.vehicles.forEach(vehicle => {
        updateOrCreateVehicle(vehicle.id, vehicle.position, vehicle.type, vehicle.emergency);
    });
    
    // Update incidents
    trafficData.incidents.forEach(incident => {
        showIncidentOnMap(incident.location, incident.type, incident.severity);
    });
    
    // Update metrics display
    document.querySelector('.stat-item:first-child .stat-value').textContent = 
        Math.round(trafficData.metrics.traffic_flow * 100) + '%';
    
    // Update traffic status
    updateTrafficStatus(trafficData.metrics.congestion_level);
}

function updateTrafficStatus(level) {
    const indicator = document.querySelector('.status-indicator');
    const text = document.querySelector('.traffic-status span:last-child');
    
    indicator.className = 'status-indicator status-' + level;
    text.textContent = level.charAt(0).toUpperCase() + level.slice(1) + ' Traffic';
}
</script>
```

2. **Run the Python system**:
```bash
pip install asyncio websockets aiohttp
python smart_city_agent.py
```

The system is completely autonomous and will manage the city traffic while providing real-time data to your 3D visualization interface!