from z3 import Solver, Bool, Implies, And, Or, Not, BoolVal, Int, Real, Context, Eq
from sympy import symbols, Eq as SymEq, solve, diff, integrate, Matrix, simplify, expand, factor, latex
from sympy.parsing.sympy_parser import parse_expr
from typing import Dict, Any, List, Union, Tuple
from autogen_agentchat.tools import FunctionTool
import re
import random

class SymPySymbolicReasoner:
    def __init__(self):
        self.symbol_cache = {}
    
    def solve_symbolically(self, equation: str, variables: List[str], method: str = "all") -> Dict[str, Any]:
        """Solve equations symbolically using SymPy."""
        try:
            # Parse expression
            expr = parse_expr(equation, transformations='all')
            
            # Define symbols
            sym_vars = [symbols(var) for var in variables]
            
            # Method-specific solving
            results = {}
            
            if method in ["solve", "all"]:
                solutions = solve(expr, sym_vars)
                results["solutions"] = solutions
                
            if method in ["simplify", "all"]:
                results["simplified"] = simplify(expr)
                
            if method in ["expand", "all"]:
                results["expanded"] = expand(expr)
                
            if method in ["factor", "all"]:
                results["factored"] = factor(expr)
                
            if method in ["derivative", "all"]:
                if len(sym_vars) > 0:
                    results["derivative"] = {var: diff(expr, var) for var in sym_vars}
                    
            if method in ["integrate", "all"]:
                if len(sym_vars) > 0:
                    results["integral"] = {var: integrate(expr, var) for var in sym_vars}
                    
            if method in ["matrix", "all"] and isinstance(expr, Matrix):
                results["determinant"] = expr.det()
                results["inverse"] = expr.inv() if expr.det() != 0 else None
                
            results["latex"] = latex(expr)
            return {"status": "SUCCESS", "results": results}
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def optimize_with_derivatives(self, objective: str, constraints: List[str], variables: List[str]) -> Dict[str, Any]:
        """Find optimization using symbolic derivatives (gradient descent simulation)."""
        try:
            obj_expr = parse_expr(f"({objective})")
            sym_vars = [symbols(var) for var in variables]
            
            # Compute gradients
            gradients = {var: diff(obj_expr, var) for var in sym_vars}
            
            # Find critical points (set gradients = 0)
            critical_points = []
            for var in sym_vars:
                grad_eq = SymEq(gradients[var], 0)
                crit = solve(grad_eq, var)
                if crit:
                    critical_points.extend(crit)
            
            return {
                "status": "SUCCESS",
                "objective": objective,
                "gradients": {str(k): str(v) for k, v in gradients.items()},
                "critical_points": [str(p) for p in critical_points]
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

class EnhancedZ3Reasoner:
    def __init__(self, timeout_ms: int = 5000):
        self.solver = Solver()
        self.solver.set(precision=10)
        self.timeout = timeout_ms
        self.sympy = SymPySymbolicReasoner()
    
    def solve_hybrid(self, constraints: List[str], variables: Dict[str, type], symbolic_preprocess: bool = True) -> Dict[str, Any]:
        """Hybrid SymPy + Z3 solving: symbolic simplification then numerical solving."""
        ctx = Context()
        solver = Solver(ctx=ctx)
        solver.set(timeout=self.timeout)
        
        processed_constraints = []
        
        # Symbolic preprocessing
        if symbolic_preprocess:
            for const in constraints:
                # Try to simplify with SymPy first
                var_names = list(variables.keys())
                sym_result = self.sympy.solve_symbolically(const, var_names, method="simplify")
                if sym_result["status"] == "SUCCESS":
                    simplified = str(sym_result["results"].get("simplified", const))
                    processed_constraints.append(simplified)
                else:
                    processed_constraints.append(const)
        else:
            processed_constraints = constraints
        
        # Z3 solving with processed constraints
        for const in processed_constraints:
            expr = self._parse_expr(const, variables, ctx)
            solver.add(expr)
        
        if solver.check() == solver.sat:
            model = solver.model()
            result = {}
            for decl in model.decls():
                name = decl.name()
                if name in variables:
                    val = model[decl]
                    if variables[name] == bool:
                        result[name] = bool(val)
                    elif variables[name] in [int, float]:
                        result[name] = float(str(val))
                    else:
                        result[name] = str(val)
            return {"status": "SAT", "model": result, "preprocessed_constraints": processed_constraints}
        else:
            core = solver.unsat_core()
            return {"status": "UNSAT", "explanation": [str(c) for c in core], "preprocessed_constraints": processed_constraints}
    
    def _parse_expr(self, expr_str: str, vars_dict: Dict[str, type], ctx: Context) -> Any:
        """Enhanced parser with SymPy preprocessing."""
        from z3 import And, Or, Not, Implies, Eq
        
        local_dict = {
            'And': And,
            'Or': Or,
            'Not': Not,
            'Implies': Implies,
            'Eq': Eq,
            'True': BoolVal(True, ctx),
            'False': BoolVal(False, ctx),
        }
        
        # Declare Z3 variables
        symbols = {}
        for name, typ in vars_dict.items():
            if typ == int:
                symbols[name] = Int(name, ctx)
            elif typ == float or typ == 'real':
                symbols[name] = Real(name, ctx)
            elif typ == bool:
                symbols[name] = Bool(name, ctx)
        
        local_dict.update(symbols)
        
        # Preprocess with regex (same as before)
        expr_str = expr_str.upper()
        expr_str = re.sub(r'\bAND\b', ' & ', expr_str)
        expr_str = re.sub(r'\bOR\b', ' | ', expr_str)
        expr_str = re.sub(r'\bNOT\b', ' ~', expr_str)
        expr_str = re.sub(r'\bIMPLIES\b', ' >> ', expr_str)
        expr_str = re.sub(r'\bTRUE\b', 'True', expr_str)
        expr_str = re.sub(r'\bFALSE\b', 'False', expr_str)
        expr_str = expr_str.replace('==', ' == ')
        
        try:
            return eval(expr_str, {"__builtins__": {}}, local_dict)
        except Exception as e:
            # Fallback: try SymPy parsing then convert
            try:
                sym_expr = parse_expr(expr_str)
                # Convert SymPy to Z3 (simplified version)
                return self._sympy_to_z3(sym_expr, symbols, ctx)
            except:
                raise ValueError(f"Failed to parse '{expr_str}': {e}")
    
    def _sympy_to_z3(self, sympy_expr, z3_symbols: Dict[str, Any], ctx: Context) -> Any:
        """Convert SymPy expression to Z3 (basic conversion)."""
        # This is a simplified converter; expand for full coverage
        if sympy_expr.is_Boolean:
            return BoolVal(sympy_expr, ctx)
        elif sympy_expr.is_Number:
            return RealVal(float(sympy_expr), ctx)
        elif str(sympy_expr) in z3_symbols:
            return z3_symbols[str(sympy_expr)]
        else:
            # Fallback to string conversion
            return BoolVal(True, ctx)

# AutoGen Tools
sympy_tool = FunctionTool(
    SymPySymbolicReasoner().solve_symbolically,
    name="sympy_solver",
    description="Solve symbolic equations: Input {'equation': str, 'variables': [str], 'method': str}. Methods: solve, simplify, expand, factor, derivative, integrate, matrix."
)

hybrid_z3_tool = FunctionTool(
    EnhancedZ3Reasoner().solve_hybrid,
    name="hybrid_z3_solver",
    description="Hybrid SymPy+Z3 solving: Input {'constraints': [str], 'variables': {str: type}, 'symbolic_preprocess': bool}."
)

optimization_tool = FunctionTool(
    SymPySymbolicReasoner().optimize_with_derivatives,
    name="symbolic_optimizer",
    description="Symbolic optimization using derivatives: Input {'objective': str, 'constraints': [str], 'variables': [str]}."
)

# Enhanced Monte Carlo with SymPy sampling
def sympy_monte_carlo(equation: str, variables: List[str], samples: int = 100) -> List[Dict[str, Any]]:
    """Symbolic Monte Carlo sampling with SymPy."""
    reasoner = SymPySymbolicReasoner()
    solutions = []
    for _ in range(samples):
        # Add symbolic noise
        noisy_eq = f"({equation}) + Symbol('noise_{random.randint(1,1000)}')"
        result = reasoner.solve_symbolically(noisy_eq, variables)
        if result["status"] == "SUCCESS":
            solutions.append(result["results"])
    return solutions[:10]