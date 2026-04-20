"""
AST-based Code Comparator

Compares code based on Abstract Syntax Tree (AST) to ignore formatting differences
while focusing on actual logic.
"""

import ast
import re
from typing import Tuple, List, Set
from dataclasses import dataclass


@dataclass
class CodeStructure:
    """Represents the logical structure of a code snippet."""
    functions: Set[str]
    classes: Set[str]
    imports: Set[str]
    function_calls: Set[str]
    assignments: Set[str]
    control_flow: Set[str]  # if, for, while, try, etc.


class ASTCodeComparator:
    """Compare Python code based on AST structure."""
    
    def __init__(self):
        """Initialize the comparator."""
        pass
    
    def _extract_structure(self, code: str) -> Tuple[CodeStructure, List[str]]:
        """
        Extract logical structure from Python code.
        
        Returns:
            (CodeStructure, list of issues)
        """
        issues = []
        structure = CodeStructure(
            functions=set(),
            classes=set(),
            imports=set(),
            function_calls=set(),
            assignments=set(),
            control_flow=set()
        )
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return structure, [f"Syntax error: {str(e)}"]
        
        # Walk the AST
        for node in ast.walk(tree):
            # Functions
            if isinstance(node, ast.FunctionDef):
                structure.functions.add(node.name)
            
            # Classes
            elif isinstance(node, ast.ClassDef):
                structure.classes.add(node.name)
            
            # Imports
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    structure.imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    structure.imports.add(f"{module}.{alias.name}" if module else alias.name)
            
            # Function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    structure.function_calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    # method calls like df.fillna()
                    if isinstance(node.func.value, ast.Name):
                        structure.function_calls.add(f"{node.func.value.id}.{node.func.attr}")
            
            # Assignments
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        structure.assignments.add(target.id)
            
            # Control flow
            elif isinstance(node, (ast.If, ast.For, ast.While, ast.Try)):
                flow_type = node.__class__.__name__.lower()
                structure.control_flow.add(flow_type)
        
        return structure, issues
    
    def compare(self, expected: str, actual: str) -> Tuple[float, List[str]]:
        """
        Compare two Python code snippets semantically.
        
        Returns:
            (similarity_score: 0-1, list of issues)
        """
        issues = []
        score = 1.0
        
        if not expected or not actual:
            return 0.0, ["Empty code snippet"]
        
        # Extract structures
        expected_struct, exp_issues = self._extract_structure(expected)
        actual_struct, act_issues = self._extract_structure(actual)
        
        issues.extend(act_issues)
        
        if act_issues:
            # If actual code has syntax errors, return lower score
            return 0.0, issues
        
        # Compare functions
        if expected_struct.functions != actual_struct.functions:
            missing = expected_struct.functions - actual_struct.functions
            extra = actual_struct.functions - expected_struct.functions
            
            if missing:
                issues.append(f"Missing functions: {missing}")
                score *= 0.8
            if extra:
                issues.append(f"Extra functions: {extra}")
                score *= 0.95
        else:
            score *= 1.0
        
        # Compare classes
        if expected_struct.classes != actual_struct.classes:
            missing = expected_struct.classes - actual_struct.classes
            extra = actual_struct.classes - expected_struct.classes
            
            if missing:
                issues.append(f"Missing classes: {missing}")
                score *= 0.8
            if extra:
                issues.append(f"Extra classes: {extra}")
                score *= 0.95
        
        # Compare imports
        if expected_struct.imports != actual_struct.imports:
            missing = expected_struct.imports - actual_struct.imports
            extra = actual_struct.imports - expected_struct.imports
            
            if missing:
                issues.append(f"Missing imports: {missing}")
                score *= 0.85
            if extra:
                issues.append(f"Extra imports: {extra}")
                score *= 0.95
        
        # Compare key function calls (error handling, logging, etc.)
        expected_key_calls = self._extract_key_calls(expected_struct.function_calls)
        actual_key_calls = self._extract_key_calls(actual_struct.function_calls)
        
        if expected_key_calls != actual_key_calls:
            missing = expected_key_calls - actual_key_calls
            
            if missing:
                issues.append(f"Missing critical functions: {missing}")
                score *= 0.75
        
        # Compare control flow structures
        if expected_struct.control_flow == actual_struct.control_flow:
            # Both have same control flow (good)
            pass
        else:
            expected_cf = expected_struct.control_flow
            actual_cf = actual_struct.control_flow
            
            # Check if actual has at least what expected needs
            if not expected_cf <= actual_cf:  # If expected has more control flow, it's a problem
                missing = expected_cf - actual_cf
                issues.append(f"Missing control flow: {missing}")
                score *= 0.75
        
        return max(0.0, min(1.0, score)), issues
    
    def _extract_key_calls(self, all_calls: Set[str]) -> Set[str]:
        """Extract critical function calls like error handling, logging."""
        key_patterns = {
            'try', 'except', 'raise', 'assert',
            'log', 'print', 'error', 'warning', 'debug',
            'fillna', 'dropna', 'isnull', 'notnull',
            'validate', 'check', 'verify',
            'df', 'pd', 'numpy', 'np'
        }
        
        return {call for call in all_calls 
                if any(pattern in call.lower() for pattern in key_patterns)}
