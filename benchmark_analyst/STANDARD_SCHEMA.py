"""
STANDARD TASK SCHEMA for Ford Data Analyst Benchmark

All task groups will conform to this unified structure.
This ensures consistent evaluation across all task types.
"""

STANDARD_TASK_SCHEMA = {
    # ===== REQUIRED FIELDS =====
    "task_id": "string (e.g., 'BASIC_01')",
    "category": "string (e.g., 'Data Analysis', 'SQL')",
    "question": "string (the task question/prompt)",
    "answer_type": "string (text|code|number|list)",
    "points": "integer (max points for this task)",
    
    # ===== OPTIONAL BUT COMMON =====
    "difficulty": "string (easy|medium|hard, default: medium)",
    
    # ===== EVALUATION CRITERIA - UNIFIED =====
    "evaluation_criteria": {
        "required_elements": [
            "list of strings describing required code/structure elements",
            "e.g., 'HTML table structure', 'useState hook', 'GROUP BY clause'"
        ],
        "forbidden_elements": [
            "list of strings describing forbidden patterns",
            "e.g., 'hardcoded values', 'nested loops', 'ANY_VALUE in BigQuery'"
        ],
        "syntax_check": "boolean (check for valid syntax)",
        "logic_check": "boolean (check for correct logic)",
        "performance_check": "boolean (check for performance)",
        "feature_check": "boolean (check for specific features/patterns)"
    },
    
    # ===== ANSWERS & EXPECTATIONS =====
    "correct_answer": "string (expected answer or description of correctness)",
    
    # ===== CONTEXT & DATA REFERENCES =====
    "context": "string (background context for the task, optional)",
    "dataset": "string (filename e.g., 'sales_data.csv', optional)",
    "datasets": "list of strings (multiple dataset filenames, optional)",
    "document": "string (filename e.g., 'sample_spec.txt', optional)",
    
    # ===== TASK-SPECIFIC FIELDS =====
    "minimal_prompt": "boolean (is prompt intentionally minimal/vague?)",
    "tolerance": "float (for numeric answers, e.g., 0.01)",
    "target_dialect": "string (SQL dialect, e.g., 'BigQuery', 'PostgreSQL')",
    "constraints": "string (additional constraints on the answer)"
}

# ===== FIELD MAPPING FROM OLD TO NEW =====
FIELD_MAPPINGS = {
    # Old field -> New field/location
    "required_syntax": "evaluation_criteria.required_elements",
    "forbidden_syntax": "evaluation_criteria.forbidden_elements",
    "specific_features": "evaluation_criteria.required_elements",
    "forbidden_dialects": "evaluation_criteria.forbidden_elements",
    "forbidden_features": "evaluation_criteria.forbidden_elements",
    "requirements": "evaluation_criteria.required_elements",
    "expected_extraction": "evaluation_criteria.required_elements",
    "expected_answer": "correct_answer",  # Merge with correct_answer or use as description
    "expected_structure": "evaluation_criteria.required_elements",
    "sub_tasks": "evaluation_criteria.required_elements",
    "common_mistakes": "evaluation_criteria.forbidden_elements",
    "evaluation": "evaluation_criteria",  # Merge existing evaluation field
}

# Removed verbose schema output - keep schema definition clean
# Use logging if detailed schema debugging is needed during development
# import logging
# logger = logging.getLogger(__name__)
# logger.debug(f"STANDARD TASK SCHEMA DEFINED with {len(STANDARD_TASK_SCHEMA)} fields")
