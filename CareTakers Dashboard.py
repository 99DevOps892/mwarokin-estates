import asyncio
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict
import random
from collections import defaultdict
import heapq

# ============================================================================
# ENUMS AND DATA CLASSES
# ============================================================================

class TaskPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ESCALATED = "escalated"

class PropertyType(Enum):
    WATER = "water"
    TRASH = "trash"
    SECURITY = "security"
    PARKING = "parking"
    MAINTENANCE = "maintenance"
    COMMUNITY = "community"

@dataclass
class Task:
    id: str
    title: str
    description: str
    property_type: PropertyType
    priority: TaskPriority
    status: TaskStatus
    property_name: str
    created_at: datetime
    deadline: datetime
    estimated_duration: int  # minutes
    dependencies: List[str] = field(default_factory=list)
    assigned_to: Optional[str] = None
    completion_percentage: int = 0
    ai_confidence: float = 0.0
    metadata: Dict = field(default_factory=dict)

@dataclass
class PropertyStatus:
    name: str
    water_level: float
    trash_fill: float
    security_status: bool
    parking_available: int
    last_maintenance: datetime
    alerts: List[str] = field(default_factory=list)

# ============================================================================
# AI DECISION ENGINE
# ============================================================================

class AIDecisionEngine:
    """Advanced AI engine for intelligent task analysis and decision-making"""
    
    def __init__(self):
        self.learning_data = defaultdict(list)
        self.pattern_memory = {}
        
    def analyze_urgency(self, task: Task, property_status: PropertyStatus) -> Tuple[float, str]:
        """AI-powered urgency analysis with reasoning"""
        urgency_score = 0.0
        reasons = []
        
        # Time-based urgency
        time_remaining = (task.deadline - datetime.now()).total_seconds() / 3600
        if time_remaining < 2:
            urgency_score += 40
            reasons.append("Less than 2 hours to deadline")
        elif time_remaining < 24:
            urgency_score += 25
            reasons.append("Less than 24 hours to deadline")
        
        # Property-specific urgency analysis
        if task.property_type == PropertyType.WATER:
            if property_status.water_level < 20:
                urgency_score += 35
                reasons.append("Critical water level detected")
            elif property_status.water_level < 50:
                urgency_score += 15
                reasons.append("Low water level")
                
        elif task.property_type == PropertyType.SECURITY:
            if not property_status.security_status:
                urgency_score += 45
                reasons.append("Security system offline - immediate action required")
                
        elif task.property_type == PropertyType.TRASH:
            if property_status.trash_fill > 90:
                urgency_score += 30
                reasons.append("Trash container near capacity")
                
        # Priority weight
        priority_weights = {
            TaskPriority.CRITICAL: 30,
            TaskPriority.HIGH: 20,
            TaskPriority.MEDIUM: 10,
            TaskPriority.LOW: 5
        }
        urgency_score += priority_weights[task.priority]
        
        # Pattern recognition from historical data
        pattern_score = self._check_historical_patterns(task)
        urgency_score += pattern_score
        if pattern_score > 0:
            reasons.append(f"Historical pattern suggests priority increase (+{pattern_score})")
        
        return min(urgency_score, 100), " | ".join(reasons)
    
    def _check_historical_patterns(self, task: Task) -> float:
        """Analyze historical patterns for similar tasks"""
        key = f"{task.property_type.value}_{task.priority.value}"
        if key in self.pattern_memory:
            avg_completion = self.pattern_memory[key].get('avg_completion_time', 0)
            if avg_completion > task.estimated_duration * 1.5:
                return 15  # Task type typically takes longer
        return 0
    
    def predict_completion_time(self, task: Task) -> int:
        """AI prediction of actual completion time based on historical data"""
        base_time = task.estimated_duration
        
        # Complexity factors
        complexity_multiplier = 1.0
        if len(task.dependencies) > 2:
            complexity_multiplier += 0.3
        if task.property_type in [PropertyType.SECURITY, PropertyType.WATER]:
            complexity_multiplier += 0.2
            
        predicted_time = int(base_time * complexity_multiplier)
        return predicted_time
    
    def recommend_assignment(self, task: Task, available_staff: List[Dict]) -> Optional[str]:
        """AI-powered staff assignment recommendation"""
        if not available_staff:
            return None
            
        best_match = None
        best_score = 0
        
        for staff in available_staff:
            score = 0
            # Skill match
            if task.property_type.value in staff.get('skills', []):
                score += 40
            # Workload consideration
            if staff.get('current_tasks', 0) < 3:
                score += 30
            # Experience level
            score += staff.get('experience_level', 0) * 10
            
            if score > best_score:
                best_score = score
                best_match = staff['name']
                
        return best_match
    
    def detect_anomalies(self, property_status: PropertyStatus) -> List[str]:
        """AI anomaly detection for proactive issue identification"""
        anomalies = []
        
        # Statistical anomaly detection
        if property_status.water_level < 15:
            anomalies.append("CRITICAL: Water level anomaly - possible leak detected")
        
        if property_status.trash_fill > 95:
            anomalies.append("WARNING: Trash overflow risk - schedule immediate collection")
            
        if not property_status.security_status:
            anomalies.append("ALERT: Security system failure - dispatching maintenance")
            
        # Time-based anomalies
        time_since_maintenance = (datetime.now() - property_status.last_maintenance).days
        if time_since_maintenance > 30:
            anomalies.append(f"NOTICE: {time_since_maintenance} days since last maintenance")
            
        return anomalies

# ============================================================================
# TASK SCHEDULER WITH INTELLIGENT PRIORITIZATION
# ============================================================================

class IntelligentTaskScheduler:
    """Advanced task scheduler with AI-powered prioritization"""
    
    def __init__(self, ai_engine: AIDecisionEngine):
        self.ai_engine = ai_engine
        self.task_queue = []
        self.execution_history = []
        
    def add_task(self, task: Task, property_status: PropertyStatus):
        """Add task with AI-powered priority calculation"""
        urgency_score, reasoning = self.ai_engine.analyze_urgency(task, property_status)
        task.ai_confidence = urgency_score
        task.metadata['urgency_reasoning'] = reasoning
        
        # Use negative urgency for min-heap (higher urgency = lower value)
        heapq.heappush(self.task_queue, (-urgency_score, task.created_at, task))
        
    def get_next_task(self) -> Optional[Task]:
        """Retrieve next highest priority task"""
        if self.task_queue:
            _, _, task = heapq.heappop(self.task_queue)
            return task
        return None
    
    def reorder_tasks(self, property_statuses: Dict[str, PropertyStatus]):
        """Dynamic task reordering based on changing conditions"""
        temp_tasks = []
        while self.task_queue:
            _, _, task = heapq.heappop(self.task_queue)
            temp_tasks.append(task)
        
        # Recalculate priorities with current property statuses
        for task in temp_tasks:
            prop_status = property_statuses.get(task.property_name)
            if prop_status:
                self.add_task(task, prop_status)

# ============================================================================
# AUTONOMOUS AGENT SYSTEM
# ============================================================================

class AutonomousAgent:
    """Self-operating agent for task execution and monitoring"""
    
    def __init__(self, name: str, skills: List[str]):
        self.name = name
        self.skills = skills
        self.current_task: Optional[Task] = None
        self.completed_tasks = 0
        self.is_busy = False
        
    async def execute_task(self, task: Task) -> bool:
        """Execute task with simulated real-time progress"""
        self.is_busy = True
        self.current_task = task
        task.status = TaskStatus.IN_PROGRESS
        task.assigned_to = self.name
        
        print(f"\n[{self.name}] Starting: {task.title}")
        print(f"  Property: {task.property_name}")
        print(f"  Estimated: {task.estimated_duration} min")
        print(f"  AI Confidence: {task.ai_confidence:.1f}%")
        
        # Simulate real-time execution with progress updates
        steps = 5
        for i in range(steps):
            await asyncio.sleep(0.5)  # Simulated work
            task.completion_percentage = int((i + 1) / steps * 100)
            print(f"  Progress: {task.completion_percentage}%")
            
        task.status = TaskStatus.COMPLETED
        self.completed_tasks += 1
        self.is_busy = False
        self.current_task = None
        
        print(f"[{self.name}] ✓ Completed: {task.title}\n")
        return True

# ============================================================================
# PROPERTY MONITOR
# ============================================================================

class RealTimePropertyMonitor:
    """Real-time monitoring system for all properties"""
    
    def __init__(self):
        self.properties: Dict[str, PropertyStatus] = {}
        self.ai_engine = AIDecisionEngine()
        
    def initialize_properties(self):
        """Initialize property statuses"""
        properties = [
            ("Sunset Villa", 85, 45, True, 2),
            ("Green Valley Apartments", 72, 78, True, 4),
            ("Lakeview Mansion", 18, 92, False, 1)  # Critical conditions
        ]
        
        for name, water, trash, security, parking in properties:
            self.properties[name] = PropertyStatus(
                name=name,
                water_level=water,
                trash_fill=trash,
                security_status=security,
                parking_available=parking,
                last_maintenance=datetime.now() - timedelta(days=random.randint(5, 45))
            )
    
    async def monitor(self):
        """Continuous monitoring with anomaly detection"""
        while True:
            print("\n" + "="*70)
            print("REAL-TIME PROPERTY MONITORING")
            print("="*70)
            
            for prop_name, status in self.properties.items():
                print(f"\n📍 {prop_name}")
                print(f"  💧 Water: {status.water_level:.1f}%")
                print(f"  🗑️  Trash: {status.trash_fill:.1f}%")
                print(f"  🛡️  Security: {'✓ Active' if status.security_status else '✗ OFFLINE'}")
                print(f"  🅿️  Parking: {status.parking_available} spots")
                
                # AI anomaly detection
                anomalies = self.ai_engine.detect_anomalies(status)
                if anomalies:
                    print(f"  ⚠️  AI ALERTS:")
                    for anomaly in anomalies:
                        print(f"     • {anomaly}")
                        status.alerts.append(anomaly)
            
            await asyncio.sleep(5)  # Monitor every 5 seconds
    
    def update_property_status(self, property_name: str, updates: Dict):
        """Update property status (simulates real sensor data)"""
        if property_name in self.properties:
            prop = self.properties[property_name]
            for key, value in updates.items():
                if hasattr(prop, key):
                    setattr(prop, key, value)

# ============================================================================
# MAIN TASK MANAGEMENT SYSTEM
# ============================================================================

class AgenticTaskManagementSystem:
    """Central AI-powered task management orchestrator"""
    
    def __init__(self):
        self.ai_engine = AIDecisionEngine()
        self.scheduler = IntelligentTaskScheduler(self.ai_engine)
        self.monitor = RealTimePropertyMonitor()
        self.agents: List[AutonomousAgent] = []
        self.all_tasks: List[Task] = []
        
    def initialize_system(self):
        """Initialize the complete system"""
        print("🚀 Initializing AI Agentic Task Management System...")
        
        # Initialize properties
        self.monitor.initialize_properties()
        
        # Create autonomous agents
        self.agents = [
            AutonomousAgent("Agent-Alpha", ["water", "maintenance"]),
            AutonomousAgent("Agent-Beta", ["security", "trash"]),
            AutonomousAgent("Agent-Gamma", ["parking", "community"])
        ]
        
        # Generate initial tasks
        self._generate_initial_tasks()
        
        print(f"✓ System initialized with {len(self.all_tasks)} tasks")
        print(f"✓ {len(self.agents)} autonomous agents ready")
        print(f"✓ {len(self.monitor.properties)} properties under monitoring\n")
    
    def _generate_initial_tasks(self):
        """Generate initial task set based on property conditions"""
        task_templates = [
            ("Emergency Water Leak Repair", PropertyType.WATER, TaskPriority.CRITICAL, 
             "Lakeview Mansion", "Critical water level detected - immediate repair needed", 45),
            ("Security System Restoration", PropertyType.SECURITY, TaskPriority.CRITICAL,
             "Lakeview Mansion", "Security system offline - restore operations", 60),
            ("Trash Collection", PropertyType.TRASH, TaskPriority.HIGH,
             "Green Valley Apartments", "Scheduled trash collection - 78% full", 30),
            ("Water Tank Inspection", PropertyType.WATER, TaskPriority.MEDIUM,
             "Sunset Villa", "Routine water tank inspection and maintenance", 40),
            ("Parking Space Reallocation", PropertyType.PARKING, TaskPriority.LOW,
             "Lakeview Mansion", "Optimize parking space allocation", 20)
        ]
        
        for i, (title, ptype, priority, prop, desc, duration) in enumerate(task_templates):
            task = Task(
                id=f"TASK-{i+1:03d}",
                title=title,
                description=desc,
                property_type=ptype,
                priority=priority,
                status=TaskStatus.PENDING,
                property_name=prop,
                created_at=datetime.now(),
                deadline=datetime.now() + timedelta(hours=random.randint(2, 48)),
                estimated_duration=duration
            )
            
            self.all_tasks.append(task)
            prop_status = self.monitor.properties.get(prop)
            if prop_status:
                self.scheduler.add_task(task, prop_status)
    
    async def execute_task_pipeline(self):
        """Main execution pipeline with autonomous agents"""
        print("\n" + "="*70)
        print("AUTONOMOUS TASK EXECUTION PIPELINE")
        print("="*70)
        
        while self.scheduler.task_queue:
            # Find available agent
            available_agent = next((a for a in self.agents if not a.is_busy), None)
            
            if available_agent:
                task = self.scheduler.get_next_task()
                if task:
                    # Check if agent has required skills
                    if task.property_type.value in available_agent.skills:
                        await available_agent.execute_task(task)
                    else:
                        # Reassign to capable agent
                        capable_agent = next(
                            (a for a in self.agents 
                             if not a.is_busy and task.property_type.value in a.skills),
                            None
                        )
                        if capable_agent:
                            await capable_agent.execute_task(task)
                        else:
                            print(f"⚠️  No capable agent for {task.title} - re-queuing")
                            prop_status = self.monitor.properties.get(task.property_name)
                            if prop_status:
                                self.scheduler.add_task(task, prop_status)
            else:
                await asyncio.sleep(0.5)  # Wait for agent availability
    
    def generate_report(self):
        """Generate comprehensive system report"""
        print("\n" + "="*70)
        print("AI TASK MANAGEMENT SYSTEM REPORT")
        print("="*70)
        
        completed = [t for t in self.all_tasks if t.status == TaskStatus.COMPLETED]
        pending = [t for t in self.all_tasks if t.status == TaskStatus.PENDING]
        
        print(f"\n📊 TASK STATISTICS:")
        print(f"  Total Tasks: {len(self.all_tasks)}")
        print(f"  Completed: {len(completed)} ({len(completed)/len(self.all_tasks)*100:.1f}%)")
        print(f"  Pending: {len(pending)}")
        
        print(f"\n🤖 AGENT PERFORMANCE:")
        for agent in self.agents:
            print(f"  {agent.name}: {agent.completed_tasks} tasks completed")
            print(f"    Skills: {', '.join(agent.skills)}")
        
        print(f"\n🏢 PROPERTY STATUS SUMMARY:")
        for name, status in self.monitor.properties.items():
            alert_count = len(status.alerts)
            print(f"  {name}: {alert_count} alert(s)")
            if status.alerts:
                for alert in status.alerts[-3:]:  # Show last 3 alerts
                    print(f"    • {alert}")
        
        print("\n" + "="*70)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """Main execution function"""
    system = AgenticTaskManagementSystem()
    system.initialize_system()
    
    # Create concurrent tasks for monitoring and execution
    monitor_task = asyncio.create_task(system.monitor.monitor())
    execution_task = asyncio.create_task(system.execute_task_pipeline())
    
    # Run execution pipeline
    await execution_task
    
    # Cancel monitoring after execution
    monitor_task.cancel()
    
    # Generate final report
    system.generate_report()

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║   MWAROKIN AI AGENTIC TASK MANAGEMENT SYSTEM v2.0            ║
    ║   Advanced Autonomous Property Management                     ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  System shutdown initiated by user")
    except Exception as e:
        print(f"\n❌ System error: {e}")
    finally:
        print("\n✓ System terminated gracefully")