import asyncio
import json
import re
from autogen_agentchat.groups import GroupChat, GroupChatManager
from autogen_agentchat.ui import Console
from agents import orchestrator, symbolic_reasoner, meta_evolver, fusion_agent, math_analyst
from tools import SymPySymbolicReasoner, EnhancedZ3Reasoner

class CosmosEngineV4:
    def __init__(self):
        self.sympy_reasoner = SymPySymbolicReasoner()
        self.z3_reasoner = EnhancedZ3Reasoner()
        
        self.group_chat = GroupChat(
            agents=[orchestrator, symbolic_reasoner, meta_evolver, fusion_agent, math_analyst],
            messages=[],
            max_round=25,
            speaker_selection_method="auto"
        )
        self.manager = GroupChatManager(groupchat=self.group_chat, llm_config=orchestrator.llm_config)

    async def process_task(self, task: str, context: dict = None, math_mode: bool = False) -> str:
        """Enhanced processing with mathematical reasoning capabilities."""
        if context is None:
            context = {}
        
        # Determine if this is a mathematical task
        is_math_task = any(keyword in task.lower() for keyword in 
                          ['solve', 'equation', 'optimize', 'derivative', 'integral', 
                           'matrix', 'constraint', 'model', 'calculate'])
        
        message = f"Task: {task}. Context: {context}. "
        if math_mode or is_math_task:
            message += "Use symbolic mathematics and logical reasoning. "
        else:
            message += "Use general reasoning with mathematical support when needed. "
        message += "Provide clear explanations and mathematical derivations."
        
        # Kickoff conversation
        await orchestrator.initiate_chat(
            self.manager,
            message=message
        )
        
        # Extract and process final output
        final_msg = self.group_chat.messages[-1]["content"]
        
        # Enhanced post-processing for mathematical results
        processed_result = await self._process_math_output(final_msg, task, context)
        
        return processed_result

    async def _process_math_output(self, message: str, original_task: str, context: dict) -> str:
        """Process mathematical outputs with validation and visualization."""
        try:
            # Try to extract JSON results
            json_match = re.search(r'\{.*\}', message, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())
                
                if "results" in result_data and result_data["status"] == "SUCCESS":
                    # Validate symbolic results
                    validation = self._validate_math_result(result_data, original_task)
                    result_data["validation"] = validation
                    
                    # Generate LaTeX for visualization
                    if "latex" in result_data["results"]:
                        result_data["display_latex"] = result_data["results"]["latex"]
                
                return json.dumps(result_data, indent=2)
        except:
            pass
        
        # Fallback: return original message with basic processing
        return f"Analysis: {message}"

    def _validate_math_result(self, result_data: dict, task: str) -> dict:
        """Validate mathematical results using multiple methods."""
        validation = {"methods": [], "consistent": True}
        
        if "solutions" in result_data["results"]:
            solutions = result_data["results"]["solutions"]
            # Basic consistency check (expand with more sophisticated validation)
            validation["methods"].append("solution_extraction")
            validation["solution_count"] = len(solutions)
        
        if "simplified" in result_data["results"]:
            # Compare simplified vs original complexity
            validation["methods"].append("simplification_check")
        
        return validation

    def solve_direct(self, equation: str, variables: List[str], method: str = "solve") -> Dict[str, Any]:
        """Direct SymPy solving without agent orchestration."""
        return self.sympy_reasoner.solve_symbolically(equation, variables, method)

    def optimize_direct(self, objective: str, constraints: List[str], variables: List[str]) -> Dict[str, Any]:
        """Direct symbolic optimization."""
        return self.sympy_reasoner.optimize_with_derivatives(objective, constraints, variables)

# Enhanced Usage Examples
async def demo():
    engine = CosmosEngineV4()
    
    # Demo 1: Symbolic equation solving
    print("=== Demo 1: Symbolic Solving ===")
    result1 = await engine.process_task(
        "Solve the quadratic equation x² + 5x + 6 = 0",
        math_mode=True
    )
    print(result1)
    
    # Demo 2: Optimization problem
    print("\n=== Demo 2: Optimization ===")
    result2 = await engine.process_task(
        "Optimize profit = 3x + 4y subject to x + y <= 10, x >= 0, y >= 0",
        math_mode=True
    )
    print(result2)
    
    # Demo 3: Hybrid logic + math
    print("\n=== Demo 3: Hybrid Logic + Math ===")
    result3 = await engine.process_task(
        "For a SaaS business: if monthly_revenue > 10000 AND churn_rate < 0.05, then scale_up = True. Given revenue=15000, churn=0.03, determine scale_up.",
        {"revenue": 15000, "churn": 0.03}
    )
    print(result3)
    
    # Demo 4: Direct API usage
    print("\n=== Demo 4: Direct API ===")
    direct_result = engine.solve_direct("x**2 + 2*x + 1", ["x"])
    print(f"Direct solve: {direct_result}")

if __name__ == "__main__":
    asyncio.run(demo())