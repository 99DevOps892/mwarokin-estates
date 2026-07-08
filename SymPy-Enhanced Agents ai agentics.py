from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.xai import GrokChatCompletionClient
from tools import sympy_tool, hybrid_z3_tool, optimization_tool, sympy_monte_carlo

# LLM Client
model_client = GrokChatCompletionClient(model="grok-4")

# Layer 8: Meta-Evolver Agent (Enhanced with symbolic optimization)
meta_evolver = AssistantAgent(
    name="meta_evolver",
    system_message="""Evolve agent strategies using symbolic mathematics and logic. 
    Use sympy_solver for equation manipulation, symbolic_optimizer for performance optimization,
    and hybrid_z3_solver for constraint validation of evolved strategies.""",
    llm_config={"config_list": [{"model": "grok-4", "api_key": "env:GROK_API_KEY"}]},
    tools=[sympy_tool, hybrid_z3_tool, optimization_tool],
    max_consecutive_auto_reply=5,
    description="Optimizes crew configurations using symbolic calculus and logic."
)

# Layer 6: Logical & Symbolic Reasoner Agent
symbolic_reasoner = AssistantAgent(
    name="symbolic_reasoner",
    system_message="""You are a mathematical and logical reasoning expert. 
    Use sympy_solver for symbolic manipulation (solve, simplify, derivatives, integrals).
    Use hybrid_z3_solver for constraint satisfaction with symbolic preprocessing.
    For optimization problems, use symbolic_optimizer.
    
    Examples:
    - Equation solving: 'x**2 + 2*x + 1 = 0', variables=['x'], method='solve'
    - Optimization: 'profit = 3*x + 4*y', constraints=['x + y <= 10'], variables=['x', 'y']
    - Logic with math: 'x > 5 AND sin(y) > 0', variables={'x': int, 'y': float}""",
    llm_config={"config_list": [{"model": "grok-4", "api_key": "env:GROK_API_KEY"}]},
    tools=[sympy_tool, hybrid_z3_tool, optimization_tool, 
           FunctionTool(sympy_monte_carlo, name="sympy_monte_carlo", 
                       description="Symbolic Monte Carlo sampling.")],
    max_tool_iterations=5,
    description="Handles symbolic mathematics, calculus, and hybrid logical solving."
)

# Layer 7: Strategic Orchestrator Agent (Enhanced)
orchestrator = AssistantAgent(
    name="orchestrator",
    system_message="""Coordinate multi-layer symbolic and logical reasoning. 
    Delegate mathematical problems to symbolic_reasoner, optimization to meta_evolver.
    Use mathematical modeling for strategic planning and constraint-based decision making.""",
    llm_config={"config_list": [{"model": "grok-4", "api_key": "env:GROK_API_KEY"}]},
    tools=[sympy_tool, hybrid_z3_tool, optimization_tool],
    human_input_mode="NEVER",
    description="Executes symbolic multi-layer strategic thinking."
)

# Fusion Agent (Enhanced for mathematical data fusion)
fusion_agent = AssistantAgent(
    name="fusion_agent",
    system_message="""Synthesize multi-modal data using mathematical fusion techniques. 
    Use SymPy for equation-based data integration, matrix operations for multi-source fusion,
    and hybrid Z3 solving for consistency checking across mathematical models.""",
    llm_config={"config_list": [{"model": "grok-4", "api_key": "env:GROK_API_KEY"}]},
    tools=[sympy_tool, hybrid_z3_tool],
    description="Mathematical multi-source data fusion and validation."
)

# New: Mathematical Analyst Agent
math_analyst = AssistantAgent(
    name="math_analyst",
    system_message="""Specialized in applied mathematics for SaaS analytics. 
    Model business metrics, optimize algorithms, perform statistical analysis,
    and generate mathematical proofs for system reliability.""",
    llm_config={"config_list": [{"model": "grok-4", "api_key": "env:GROK_API_KEY"}]},
    tools=[sympy_tool, optimization_tool, hybrid_z3_tool],
    description="Applied mathematics for business intelligence and optimization."
)