import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Tuple
import difflib
import re
import time
import sys

# Import semantic SQL comparator for intelligent query matching
try:
    from semantic_sql_comparator import SemanticSQLComparator
except ImportError:
    SemanticSQLComparator = None

# Import AST-based code comparator for Python code
try:
    from ast_code_comparator import ASTCodeComparator
except ImportError:
    ASTCodeComparator = None


class BenchmarkScorer:
    """Scores AI responses against the Ford Data Analyst Super Benchmark."""
    
    def __init__(self, benchmark_dir: str):
        """Initialize the scorer with benchmark directory."""
        self.benchmark_dir = Path(benchmark_dir)
        
        # Support both old structure (tasks/ at root) and new structure (data/tasks/)
        if (self.benchmark_dir / "data" / "tasks").exists():
            self.tasks_dir = self.benchmark_dir / "data" / "tasks"
            self.datasets_dir = self.benchmark_dir / "data" / "datasets"
            self.docs_dir = self.benchmark_dir / "data" / "documents"
        else:
            # Fallback to old structure
            self.tasks_dir = self.benchmark_dir / "tasks"
            self.datasets_dir = self.benchmark_dir / "datasets"
            self.docs_dir = self.benchmark_dir / "documents"
        # Initialize semantic SQL comparator
        self.sql_comparator = SemanticSQLComparator() if SemanticSQLComparator else None
        # Initialize AST-based code comparator
        self.ast_code_comparator = ASTCodeComparator() if ASTCodeComparator else None
        self.results = {
            "total_score": 0,
            "max_score": 0,
            "sections": {},
            "detailed_results": [],
            "timing_stats": {}
        }
        self.sql_dialects = {
            "BigQuery": {
                "keywords": ["EXCEPT", "ARRAY_AGG", "STRUCT", "SAFE_DIVIDE", "TIMESTAMP"],
                "forbidden_keywords": ["LIMIT 1 OFFSET", "@@"],
                "functions": ["SAFE_DIVIDE", "ARRAY_AGG", "SAFE.OFFSET"]
            },
            "MySQL": {
                "keywords": ["LIMIT", "OFFSET", "@@"],
                "forbidden_keywords": ["EXCEPT", "ARRAY_AGG", "STRUCT"],
                "functions": ["GROUP_CONCAT", "DATE_FORMAT"]
            },
            "PostgreSQL": {
                "keywords": ["WITH RECURSIVE", "EXCEPT", "WINDOW"],
                "forbidden_keywords": ["LIMIT 1 OFFSET", "@@"],
                "functions": ["ARRAY_AGG", "WINDOW"]
            }
        }
    
    def load_tasks(self) -> Dict[str, List[Dict]]:
        """Load all task files."""
        tasks = {}
        for task_file in self.tasks_dir.glob("*.json"):
            with open(task_file, 'r') as f:
                tasks[task_file.stem] = json.load(f)
        return tasks
    
    def load_datasets(self) -> Dict[str, pd.DataFrame]:
        """Load all CSV datasets."""
        datasets = {}
        for csv_file in self.datasets_dir.glob("*.csv"):
            datasets[csv_file.name] = pd.read_csv(csv_file)
        return datasets
    
    def load_document(self, filename: str) -> str:
        """Load a document file by name from the documents directory."""
        doc_path = self.docs_dir / filename
        if not doc_path.exists():
            return f"[Document file not found: {filename}]"
        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"[Error loading document {filename}: {str(e)}]"
    
    def load_dataset_preview(self, filename: str, max_rows: int = 5) -> str:
        """Load a CSV dataset preview by name from the datasets directory."""
        dataset_path = self.datasets_dir / filename
        if not dataset_path.exists():
            return f"[Dataset file not found: {filename}]"
        try:
            df = pd.read_csv(dataset_path)
            preview = df.head(max_rows).to_string()
            return f"Dataset: {filename}\nShape: {df.shape}\nPreview:\n{preview}"
        except Exception as e:
            return f"[Error loading dataset {filename}: {str(e)}]"
    
    def get_referenced_files(self, task: Dict) -> Dict[str, str]:
        """
        Extract and load all referenced files for a task.
        Returns dict with file type as key and content as value.
        """
        referenced_files = {}
        
        # Load document if referenced
        if "document" in task and task["document"]:
            doc_content = self.load_document(task["document"])
            referenced_files["document"] = {
                "filename": task["document"],
                "content": doc_content
            }
        
        # Load dataset if referenced
        if "dataset" in task and task["dataset"]:
            dataset_content = self.load_dataset_preview(task["dataset"])
            referenced_files["dataset"] = {
                "filename": task["dataset"],
                "content": dataset_content
            }
        
        # Load multiple datasets if referenced as a list
        if "datasets" in task and task["datasets"]:
            referenced_files["datasets"] = []
            for dataset_filename in task["datasets"]:
                dataset_content = self.load_dataset_preview(dataset_filename)
                referenced_files["datasets"].append({
                    "filename": dataset_filename,
                    "content": dataset_content
                })
        
        return referenced_files
    
    def score_exact_match(self, response: str, correct: Any, task_type: str, is_sql: bool = False) -> float:
        """Score based on exact match. Uses semantic comparison for SQL queries."""
        # Use semantic SQL comparison for SQL queries
        if is_sql and self.sql_comparator:
            score, _ = self.sql_comparator.compare(str(correct), str(response))
            return score
        
        if task_type == "number":
            try:
                response_val = float(response)
                correct_val = float(correct)
                if abs(response_val - correct_val) < 0.01:
                    return 1.0
            except ValueError:
                return 0.0
        elif task_type == "text":
            similarity = difflib.SequenceMatcher(
                None, 
                str(response).lower().strip(), 
                str(correct).lower().strip()
            ).ratio()
            return min(similarity, 1.0)
        elif task_type == "list":
            response_items = [item.lower().strip() for item in response.split(",")]
            correct_items = [item.lower().strip() for item in correct]
            matches = sum(1 for item in response_items if item in correct_items)
            return matches / len(correct_items) if correct_items else 0.0
        
        return 0.0
    
    def score_reasoning(self, response: str, question: str) -> float:
        """Score quality of reasoning based on response length and keywords."""
        response = str(response).strip()
        
        # Length-based scoring - less harsh for brief answers
        word_count = len(response.split())
        if word_count < 5:
            reasoning_score = 0.5  # Neutral score for brief factual answers
        elif word_count < 20:
            reasoning_score = 0.6
        else:
            reasoning_score = 0.8
        
        # Check for analytical keywords
        analytical_keywords = [
            "because", "indicates", "suggests", "correlation", "relationship",
            "pattern", "trend", "analysis", "conclude", "evidence", "data",
            "statistically", "significant", "investigate", "issue"
        ]
        
        keyword_count = sum(
            1 for keyword in analytical_keywords 
            if keyword in response.lower()
        )
        if keyword_count > 0:
            reasoning_score = min(reasoning_score + 0.2, 1.0)
        
        return reasoning_score
    
    def check_sql_dialect(self, code: str, target_dialect: str) -> Tuple[float, List[str]]:
        """Check if code follows target SQL dialect."""
        issues = []
        score = 1.0
        
        code_upper = code.upper()
        
        # Check for forbidden keywords
        if target_dialect in self.sql_dialects:
            forbidden = self.sql_dialects[target_dialect].get("forbidden_keywords", [])
            for keyword in forbidden:
                if keyword in code_upper:
                    issues.append(f"Uses {keyword} which is not standard in {target_dialect}")
                    score -= 0.2
        
        # Check for required patterns
        if "ANY_VALUE" in code_upper and target_dialect == "BigQuery":
            issues.append("ANY_VALUE is non-deterministic in Dataform - use ARRAY_AGG instead")
            score -= 0.3
        
        return max(0.0, score), issues
    
    def check_code_syntax(self, code: str, language: str = "sql") -> Tuple[float, List[str]]:
        """Basic code syntax validation."""
        issues = []
        score = 1.0
        
        # Simple syntax checks
        if language == "sql":
            # Check for balanced parentheses
            if code.count('(') != code.count(')'):
                issues.append("Unbalanced parentheses")
                score -= 0.2
            
            # Check for SELECT presence
            if "SELECT" not in code.upper():
                issues.append("Missing SELECT statement")
                score -= 0.3
        
        elif language == "python":
            # Check for syntax errors
            try:
                compile(code, '<string>', 'exec')
            except SyntaxError as e:
                issues.append(f"Syntax error: {str(e)}")
                score = 0.0
        
        return max(0.0, score), issues
    
    def _validate_response_format(self, response: str, expected_type: str) -> float:
        """Validate that response matches expected format (text/code/number)."""
        response_str = str(response).strip()
        
        if expected_type == "text":
            # For text, just check if it's not empty and not SQL/code
            if not response_str:
                return 0.0
            
            # Penalize if output looks like code when text was expected
            code_indicators = ["select ", "from ", "where ", "def ", "class ", "import ", "return ", "for ", "if "]
            if any(indicator in response_str.lower() for indicator in code_indicators):
                return 0.5  # Half credit - wrong format but substantive content
            
            return 1.0  # Text format is correct
        
        elif expected_type == "code":
            # For code, check if it looks like actual code
            if not response_str:
                return 0.0
            
            # Check for code-like patterns
            code_patterns = ["select ", "from ", "def ", "class ", "return ", "=", "{", "}", "[", "]"]
            has_code_pattern = any(pattern in response_str.lower() for pattern in code_patterns)
            
            if not has_code_pattern:
                return 0.3  # Wrong format - expected code but got prose
            
            # Try to validate syntax if it's SQL or Python
            if "select " in response_str.lower():
                # Possible SQL
                if response_str.count("(") == response_str.count(")"):
                    return 1.0  # Well-formed SQL syntax
                else:
                    return 0.7  # Has SQL structure but syntax issues
            else:
                # Assume it's code-like
                return 0.8  # Code format detected, minor syntax concerns
        
        elif expected_type == "number":
            # For numbers, check if response is numeric
            try:
                float(response_str)
                return 1.0  # Valid number
            except ValueError:
                return 0.2  # Text provided when number expected
        
        elif expected_type == "list":
            # For lists, check if it's comma-separated or formatted as list
            if "," in response_str or "[" in response_str or any(c.isdigit() for c in response_str):
                return 0.9
            else:
                return 0.5  # Unclear list format
        
        return 0.5  # Unknown type, partial credit
    
    def score_instruction_following(self, response: str, task: Dict) -> float:
        """Score how well instructions were followed."""
        sub_tasks = task.get("sub_tasks", [])
        correct_flow = task.get("correct_flow", "")
        common_mistakes = task.get("common_mistakes", [])
        
        score = 1.0
        
        # Check for common mistakes
        for mistake in common_mistakes:
            if mistake.lower() in response.lower():
                score -= 0.3
        
        # Check if response addresses sub-tasks in order
        response_lower = response.lower()
        last_position = -1
        for i, subtask in enumerate(sub_tasks):
            if subtask.lower() in response_lower:
                current_position = response_lower.find(subtask.lower())
                if current_position < last_position:
                    score -= 0.15  # Penalty for wrong order
                last_position = current_position
            else:
                score -= 0.2  # Penalty for missing subtask
        
        # Check for proper structure/sections
        if ":" in response or "\n" in response:
            score = min(1.0, score + 0.1)  # Bonus for structured response
        
        return max(0.0, score)
    
    def score_code_quality(self, code: str, language: str = "sql") -> float:
        """Score code quality: readability, comments, best practices."""
        score = 0.7  # Start at base score
        
        # Bonus for comments
        if language == "sql" and "--" in code:
            score += 0.1
        elif language == "python" and "#" in code:
            score += 0.1
        
        # Check for readability (indentation, line length)
        lines = code.split('\n')
        long_lines = sum(1 for line in lines if len(line) > 120)
        if long_lines > 0:
            score -= 0.05
        
        # Check for proper naming conventions
        if language == "sql":
            if "stg_" in code or "dim_" in code or "fact_" in code:
                score += 0.1
        
        return min(1.0, max(0.0, score))
    
    def check_evaluation_criteria(self, response: str, task: Dict) -> Dict[str, Any]:
        """
        Check response against standard evaluation_criteria from task.
        Returns dict with criteria results and overall criteria_score.
        """
        criteria_result = {
            "required_elements_found": [],
            "required_elements_missing": [],
            "forbidden_elements_found": [],
            "syntax_valid": True,
            "logic_valid": True,
            "criteria_score": 1.0
        }
        
        eval_criteria = task.get("evaluation_criteria", {})
        if not eval_criteria:
            return criteria_result
        
        response_lower = response.lower()
        
        # Check required elements
        required = eval_criteria.get("required_elements", [])
        for element in required:
            element_lower = element.lower()
            if element_lower in response_lower:
                criteria_result["required_elements_found"].append(element)
            else:
                criteria_result["required_elements_missing"].append(element)
                criteria_result["criteria_score"] -= 0.15  # Penalty per missing element
        
        # Check forbidden elements
        forbidden = eval_criteria.get("forbidden_elements", [])
        for element in forbidden:
            element_lower = element.lower()
            if element_lower in response_lower:
                criteria_result["forbidden_elements_found"].append(element)
                criteria_result["criteria_score"] -= 0.2  # Penalty per forbidden element found
        
        # Should we check syntax?
        if eval_criteria.get("syntax_check", False):
            answer_type = task.get("answer_type", "text")
            if answer_type == "code":
                # Determine language based on task
                language = "python" if "python" in task.get("question", "").lower() else "sql"
                _, syntax_issues = self.check_code_syntax(response, language=language)
                if syntax_issues:
                    criteria_result["syntax_valid"] = False
                    criteria_result["criteria_score"] -= 0.2
        
        # Should we check logic?
        if eval_criteria.get("logic_check", False):
            # For logic check, we'd need semantic comparison
            # Use semantic SQL comparator if available
            answer_type = task.get("answer_type", "text")
            if answer_type == "code" and "sql" in task.get("question", "").lower():
                correct = task.get("correct_answer", "")
                if correct and self.sql_comparator:
                    logic_score, _ = self.sql_comparator.compare(str(correct), str(response))
                    if logic_score < 0.7:
                        criteria_result["logic_valid"] = False
                        criteria_result["criteria_score"] -= 0.15
        
        # Normalize criteria score to 0.0-1.0 range
        criteria_result["criteria_score"] = max(0.0, min(1.0, criteria_result["criteria_score"]))
        
        return criteria_result
    
    def score_task(self, task: Dict, response: str, response_time: float = None) -> Dict:
        """
        Score a single task response using standardized schema.
        All tasks now follow the same evaluation_criteria structure.
        Uses task-specific weights: factual answers (high accuracy), code/explanations (balanced).
        """
        question = task.get("question", "")
        answer_type = task.get("answer_type", "text")
        correct_answer = task.get("correct_answer", "")
        points = task.get("points", 10)
        category = task.get("category", "")
        
        result = {
            "task_id": task.get("task_id"),
            "category": category,
            "points": points,
            "response_time_seconds": response_time,
        }
        
        # Load referenced files (documents, datasets) if any
        referenced_files = self.get_referenced_files(task)
        if referenced_files:
            result["referenced_files"] = referenced_files
        
        # STANDARD EVALUATION for all tasks
        # All tasks now use evaluation_criteria from the standard schema
        
        # Calculate component scores
        reasoning = self.score_reasoning(response, question)
        insight = reasoning * 0.8
        communication = 0.7 if len(str(response).split()) > 5 else 0.4
        
        # Check evaluation_criteria if present
        criteria_result = self.check_evaluation_criteria(response, task)
        criteria_score = criteria_result.get("criteria_score", 0.5)
        
        # Determine what to score on
        if correct_answer and str(correct_answer).strip():
            # Scoring approach 1: Has correct answer - use accuracy + criteria
            is_sql_query = "sql" in question.lower() and "query" in question.lower()
            accuracy = self.score_exact_match(response, correct_answer, answer_type, is_sql=is_sql_query)
            
            # TASK-SPECIFIC WEIGHTING
            # For factual/short answers (number, single word): weight accuracy heavily
            # For code/explanations: balanced weighting
            is_factual = answer_type in ["number"] or (
                answer_type == "text" and 
                len(str(correct_answer).split()) <= 3 and
                "sql" not in question.lower() and
                "code" not in question.lower() and
                "query" not in question.lower()
            )
            
            if is_factual:
                # FACTUAL TASK WEIGHTING: Accuracy (70%), Criteria (20%), Reasoning (10%)
                # Skips communication penalty for brief answers
                weighted_score = (
                    accuracy * 0.70 +
                    criteria_score * 0.20 +
                    reasoning * 0.10
                ) * points
            else:
                # CODE/EXPLANATION WEIGHTING: Accuracy (40%), Criteria (30%), Reasoning (20%), Communication (10%)
                weighted_score = (
                    accuracy * 0.40 +
                    criteria_score * 0.30 +
                    reasoning * 0.20 +
                    communication * 0.10
                ) * points
            
            result.update({
                "accuracy": accuracy,
                "criteria_score": criteria_score,
                "reasoning": reasoning,
                "communication": communication,
            })
        else:
            # Scoring approach 2: No correct answer - use format + criteria + reasoning
            format_score = self._validate_response_format(response, answer_type)
            
            # Weight: format (25%), criteria (35%), reasoning (25%), communication (15%)
            weighted_score = (
                format_score * 0.25 +
                criteria_score * 0.35 +
                reasoning * 0.25 +
                communication * 0.15
            ) * points
            
            result.update({
                "format_match": format_score,
                "criteria_score": criteria_score,
                "reasoning": reasoning,
                "communication": communication,
            })
        
        # Add evaluation details
        if criteria_result.get("required_elements_found"):
            result["required_elements_found"] = criteria_result["required_elements_found"]
        if criteria_result.get("required_elements_missing"):
            result["required_elements_missing"] = criteria_result["required_elements_missing"]
        if criteria_result.get("forbidden_elements_found"):
            result["forbidden_elements_found"] = criteria_result["forbidden_elements_found"]
        
        result["score"] = weighted_score
        result["max_points"] = points
        
        return result
    
    def score_benchmark(self, responses: Dict[str, Dict[str, Any]]) -> Dict:
        """Score entire benchmark given user responses."""
        tasks = self.load_tasks()
        results = {
            "sections": {},
            "total_score": 0,
            "max_score": 0,
            "task_results": [],
            "timing_analysis": {
                "total_time": 0,
                "avg_time_per_task": 0,
                "slowest_task": None,
                "fastest_task": None,
                "task_times": []
            }
        }
        
        all_times = []
        min_time = float('inf')
        max_time = 0
        slowest_id = None
        fastest_id = None
        
        for level_name, level_tasks in tasks.items():
            section_results = {
                "name": level_name,
                "score": 0,
                "max_points": 0,
                "task_count": len(level_tasks),
                "tasks": []
            }
            
            for task in level_tasks:
                task_id = task.get("task_id")
                response_data = responses.get(task_id, {})
                
                # Handle both simple string responses and dict responses with timing
                if isinstance(response_data, dict):
                    response = response_data.get("response", "")
                    response_time = response_data.get("time_seconds", None)
                else:
                    response = str(response_data)
                    response_time = None
                
                task_result = self.score_task(task, response, response_time)
                section_results["tasks"].append(task_result)
                section_results["score"] += task_result["score"]
                section_results["max_points"] += task_result["max_points"]
                results["total_score"] += task_result["score"]
                results["max_score"] += task_result["max_points"]
                results["task_results"].append(task_result)
                
                # Track timing
                if response_time:
                    all_times.append(response_time)
                    results["timing_analysis"]["task_times"].append({
                        "task_id": task_id,
                        "time_seconds": response_time
                    })
                    
                    if response_time < min_time:
                        min_time = response_time
                        fastest_id = task_id
                    if response_time > max_time:
                        max_time = response_time
                        slowest_id = task_id
            
            results["sections"][level_name] = section_results
        
        # Calculate timing stats
        if all_times:
            results["timing_analysis"]["total_time"] = sum(all_times)
            results["timing_analysis"]["avg_time_per_task"] = sum(all_times) / len(all_times)
            results["timing_analysis"]["fastest_task"] = {"id": fastest_id, "time": min_time}
            results["timing_analysis"]["slowest_task"] = {"id": slowest_id, "time": max_time}
        
        return results
    
    def generate_report(self, results: Dict) -> str:
        """Generate a formatted benchmark report."""
        report = "=" * 90 + "\n"
        report += "FORD DATA ANALYST SUPER BENCHMARK (FDASB) - ENHANCED RESULTS REPORT\n"
        report += "=" * 90 + "\n\n"
        
        total_score = results["total_score"]
        max_score = results["max_score"]
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        
        report += f"OVERALL SCORE: {total_score:.1f} / {max_score} ({percentage:.1f}%)\n\n"
        
        # Timing analysis
        if results.get("timing_analysis", {}).get("total_time"):
            timing = results["timing_analysis"]
            report += "-" * 90 + "\n"
            report += "TIMING ANALYSIS\n"
            report += "-" * 90 + "\n"
            report += f"Total Time: {timing['total_time']:.1f} seconds\n"
            report += f"Average per Task: {timing['avg_time_per_task']:.1f} seconds\n"
            if timing.get("fastest_task"):
                report += f"Fastest: {timing['fastest_task']['id']} ({timing['fastest_task']['time']:.2f}s)\n"
            if timing.get("slowest_task"):
                report += f"Slowest: {timing['slowest_task']['id']} ({timing['slowest_task']['time']:.2f}s)\n"
            report += "\n"
        
        # Section breakdown
        report += "-" * 90 + "\n"
        report += "SECTION BREAKDOWN\n"
        report += "-" * 90 + "\n"
        for section_name, section_data in results["sections"].items():
            section_score = section_data["score"]
            section_max = section_data["max_points"]
            section_pct = (section_score / section_max * 100) if section_max > 0 else 0
            task_count = section_data.get("task_count", len(section_data.get("tasks", [])))
            report += f"{section_name}: {section_score:.1f} / {section_max} ({section_pct:.1f}%) - {task_count} tasks\n"
        
        report += "\n" + "-" * 90 + "\n"
        report += "DETAILED TASK RESULTS (Summary)\n"
        report += "-" * 90 + "\n"
        
        # Show top and bottom performers
        task_results = results["task_results"]
        task_results_sorted = sorted(task_results, key=lambda x: x["score"], reverse=True)
        
        report += f"\nTOP 5 PERFORMING TASKS:\n"
        for i, task in enumerate(task_results_sorted[:5], 1):
            report += f"{i}. {task['task_id']}: {task['score']:.1f}/{task['max_points']} "
            if task.get("response_time_seconds"):
                report += f"({task['response_time_seconds']:.1f}s)\n"
            else:
                report += "\n"
        
        report += f"\nBOTTOM 5 PERFORMING TASKS:\n"
        for i, task in enumerate(task_results_sorted[-5:], 1):
            report += f"{i}. {task['task_id']}: {task['score']:.1f}/{task['max_points']} "
            if task.get("response_time_seconds"):
                report += f"({task['response_time_seconds']:.1f}s)\n"
            else:
                report += "\n"
        
        # Category breakdown by performance
        report += "\n" + "-" * 90 + "\n"
        report += "PERFORMANCE BY CATEGORY\n"
        report += "-" * 90 + "\n"
        
        categories = {}
        for task in task_results:
            category = task.get("category", "Unknown")
            if category not in categories:
                categories[category] = {"score": 0, "max": 0, "count": 0}
            categories[category]["score"] += task["score"]
            categories[category]["max"] += task["max_points"]
            categories[category]["count"] += 1
        
        for category in sorted(categories.keys()):
            data = categories[category]
            pct = (data["score"] / data["max"] * 100) if data["max"] > 0 else 0
            report += f"{category}: {data['score']:.1f} / {data['max']} ({pct:.1f}%) - {data['count']} tasks\n"
        
        report += "\n" + "=" * 90 + "\n"
        
        return report


def run_example_scoring():
    """Run an example scoring."""
    scorer = BenchmarkScorer(".")
    
    # Example responses
    example_responses = {
        "BASIC_01": "F150",
        "BASIC_02": "328000",
        "BASIC_03": "US",
        "BASIC_04": "4",
        "BASIC_05": "10",
        "CLEAN_01": "missing mileage, negative repair cost",
        "CLEAN_02": "Escape",
        "CLEAN_03": "No obvious inconsistencies found",
        "CLEAN_04": "Remove the row or impute with mean",
        "EDA_01": "D14",
        "EDA_02": "Engine temp spike at time 4 indicates overheating",
        "EDA_03": "Escape appears most frequently suggesting quality issues",
        "EDA_04": "US region has strongest sales overall",
        "EDA_05": "F150, Escape, Bronco, Mustang",
        "STAT_01": "372",
        "STAT_02": "Median around 390, similar to mean",
        "STAT_03": "High variation indicates different demand across models",
        "STAT_04": "Yes D14 is unusual at 110 claims vs average 26",
        "SQL_01": "SELECT region, SUM(units_sold) FROM sales GROUP BY region",
        "SQL_02": "SELECT model, AVG(units_sold) FROM sales GROUP BY model",
        "SQL_03": "SELECT model, AVG(repair_cost) FROM warranties GROUP BY model ORDER BY avg DESC",
        "SQL_04": "SELECT * FROM sales WHERE units_sold > 100000",
        "BIZ_01": "Increase EV in EU, maintain F150 in US, explore Asia",
        "BIZ_02": "Escape needs investigation due to high claim frequency",
        "BIZ_03": "Investigate D14 for operational issues and provide support",
        "BIZ_04": "Engine failure risk increases warranty and recall costs"
    }
    
    results = scorer.score_benchmark(example_responses)
    report = scorer.generate_report(results)
    print(report)
    
    # Save results
    results_file = Path("evaluation/results.json")
    results_file.parent.mkdir(exist_ok=True)
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\nResults saved to evaluation/results.json")


if __name__ == "__main__":
    run_example_scoring()
