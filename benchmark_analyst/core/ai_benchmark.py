"""
AI Benchmark runner - Provider-agnostic benchmark execution system.
Supports multiple AI providers (Gemini, etc.) and generates evaluations.
"""
import os
import json
import re
import datetime
import csv as csv_module
import time
from pathlib import Path
from typing import List, Tuple, Dict, Callable, Optional
from benchmark_analyst.core.ai_client import create_client


def extract_final_answer(response_text):
    """
    Extract the final answer from response text using smart heuristics.
    
    Strategies (in order):
    1. Look for **Answer:** or **Final Answer:** marker AFTER any code blocks
    2. Check if extracted text is pandas metadata - if so, try to parse pandas output
    3. Look for **Answer:** at the start of a line (could be before code)
    4. If response contains code blocks and answer marker points to code, extract the code
    5. Fall back to extracting model ranking from pandas output
    6. Fall back to last non-empty line
    
    Args:
        response_text: The full response text
        
    Returns:
        The extracted final answer as a string
    """
    text = response_text.strip()
    
    # Strategy 1: Find ALL **Answer:** occurrences and use the LAST one
    # This handles cases where code is in between multiple answer markers
    answer_pattern = r'\*\*(?:Final\s+)?Answer:\*\*\s*(.+?)(?:\n\n(?=\*\*)|$)'
    matches = list(re.finditer(answer_pattern, text, re.DOTALL | re.IGNORECASE))
    if matches:
        # Try each match from last to first, looking for valid content
        for match in reversed(matches):
            extracted = match.group(1).strip()
            
            # Skip if it's just pandas metadata
            if extracted.startswith('```') and 'dtype' in extracted and 'Name:' in extracted:
                # This looks like pandas output metadata, try to extract model names from it
                models = _extract_models_from_pandas(extracted)
                if models:
                    return models
                continue
            
            # Clean up if it starts with code block marker
            if extracted.startswith('```'):
                # Extract code from this block
                code_pattern = r'```(?:\w+)?\n(.*?)\n```'
                code_match = re.search(code_pattern, extracted, re.DOTALL)
                if code_match:
                    code = code_match.group(1).strip()
                    if code:
                        return code
            elif extracted and len(extracted) > 0:
                # For explanation questions, check if this ends abruptly (likely cut off)
                # If it ends with ":" it's probably incomplete
                if extracted.rstrip().endswith(':'):
                    # This looks incomplete, try to get more content
                    # Look for the answer marker and grab everything after it more generously
                    full_answer_match = re.search(r'\*\*(?:Final\s+)?Answer:\*\*\s*(.+?)(?=\n(?:\*\*|$))', text, re.DOTALL | re.IGNORECASE)
                    if full_answer_match:
                        full_extracted = full_answer_match.group(1).strip()
                        if len(full_extracted) > len(extracted):
                            return full_extracted
                
                return extracted
    
    # Strategy 2: Try to extract ranking from pandas output in code blocks
    models = _extract_models_from_pandas(text)
    if models:
        return models
    
    # Strategy 3: Look for Answer: pattern without markdown
    answer_pattern2 = r'(?:^|\n)(?:Final\s+)?Answer:\s*(.+?)(?=\n\n|\n\*\*|$)'
    match2 = re.search(answer_pattern2, text, re.DOTALL | re.IGNORECASE)
    if match2:
        extracted = match2.group(1).strip()
        if extracted and len(extracted) > 0 and not extracted.startswith('```'):
            return extracted
    
    # Strategy 4: If response has code blocks, extract ONLY if substantial and no Answer marker found
    code_pattern = r'```(?:\w+)?\n(.*?)\n```'
    code_match = re.search(code_pattern, text, re.DOTALL)
    if code_match and not matches:  # Only if we didn't find Answer markers
        code = code_match.group(1).strip()
        if code and len(code) > 50:  # Substantial code only
            return code
    
    # Strategy 5: Fall back to last non-empty line
    lines = text.split('\n')
    for line in reversed(lines):
        stripped = line.strip().replace('**', '').replace('_', '').replace('`', '').strip()
        if stripped and not stripped.startswith('```') and len(stripped) > 2:
            return stripped
    
    return ''


def _extract_models_from_pandas(text):
    """
    Extract model names from pandas series/dataframe output.
    
    Looks for patterns like:
    model
    Fiesta      2419406
    Focus       2188894
    etc.
    
    Returns comma-separated list of model names in order, or empty string if not found.
    """
    # Look for lines with model names followed by numbers
    # Common Ford models: Fiesta, Focus, F150, Mustang, Bronco, Escape, Explorer, Fusion, Ranger, EdgeSUV
    ford_models = ['Fiesta', 'Focus', 'F150', 'Mustang', 'Bronco', 'Escape', 'Explorer', 'Fusion', 'Ranger', 'EdgeSUV']
    
    # Find all model mentions with numbers in the text
    found_models = []
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        # Skip metadata lines and headers
        if not line or 'dtype' in line or 'Name:' in line or line == 'model':
            continue
        
        # Check if line starts with a Ford model followed by whitespace and numbers
        for model in ford_models:
            if line.startswith(model) and any(c.isdigit() for c in line):
                if model not in found_models:
                    found_models.append(model)
                break
    
    if found_models:
        return ', '.join(found_models)
    
    return ''


def add_answer_formatting_instructions(question):
    """
    Append clear instructions for answer formatting to the question.
    This helps the AI provide structured answers that can be reliably extracted.
    
    Args:
        question: The original question text
        
    Returns:
        The question with appended formatting instructions
    """
    formatting_instructions = """

---
IMPORTANT - ANSWER FORMAT INSTRUCTIONS:
Please provide your response with the final answer clearly marked.

For simple answers (numbers, single words, names):
**Answer:** [your direct answer]

For code snippets (SQL, Python, etc.):
**Answer:**
```[language]
[your code]
```

For explanations with a clear conclusion:
**Answer:** [summary of your conclusion]

This format helps ensure your answer is correctly evaluated.
---"""
    return question + formatting_instructions


class AIBenchmark:
    """Manages benchmark execution for AI providers."""
    
    def __init__(self, benchmark_dir: str = "benchmark_analyst"):
        """
        Initialize benchmark runner.
        
        Args:
            benchmark_dir: Base directory containing tasks, datasets, and documents
        """
        self.benchmark_dir = benchmark_dir
        self.tasks_dir = f"{benchmark_dir}/data/tasks"
        self.datasets_dir = f"{benchmark_dir}/data/datasets"
        self.documents_dir = f"{benchmark_dir}/data/documents"
        self.results_dir = "response_models"
        Path(self.results_dir).mkdir(parents=True, exist_ok=True)
    
    def scan_tasks(self) -> List[Tuple[str, str]]:
        """
        Scan tasks directory for JSON files with questions.
        
        Returns:
            List of tuples: (filename, display_name)
        """
        task_files = list(Path(self.tasks_dir).glob("*.json"))
        
        # Sort by numeric task_group extracted from filename
        def extract_level(tf):
            m = re.match(r"task_group(\d+)_", tf.name)
            return int(m.group(1)) if m else 999
        
        task_files.sort(key=extract_level)
        groups = []
        
        for tf in task_files:
            base = tf.stem
            base = re.sub(r'^task_group\d+_', '', base)
            group_name = ' '.join(word.capitalize() for word in base.split('_'))
            groups.append((tf.name, group_name))
        
        return groups
    
    def count_questions(self, task_files: List[str]) -> int:
        """
        Count total questions across selected task files.
        
        Args:
            task_files: List of task filenames to count
            
        Returns:
            Total question count
        """
        total = 0
        for task_file in task_files:
            try:
                with open(f"{self.tasks_dir}/{task_file}", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        total += sum(1 for item in data if isinstance(item, dict) and item.get("question"))
                    elif isinstance(data, dict) and data.get("question"):
                        total += 1
            except Exception:
                pass
        
        return total
    
    def run_benchmark(
        self,
        provider: str,
        api_key: str,
        custom_endpoint: str = None,
        model: str = None,
        task_files: List[str] = None,
        progress_callback: Optional[Callable[[int, int, str, int, int], None]] = None,
        should_stop_flag: Optional[Dict] = None
    ) -> Tuple[str, Dict]:
        """
        Execute benchmark for selected tasks.
        
        Args:
            provider: AI provider (e.g., 'gemini')
            api_key: API key for provider
            custom_endpoint: Optional custom endpoint URL for the API
            model: Model identifier to use
            task_files: List of task filenames to process
            progress_callback: Optional callback for progress updates (current, total, message, task_group_progress, task_group_total)
            should_stop_flag: Optional dict with 'should_stop' key that can signal the benchmark to stop
            
        Returns:
            Tuple of (results_filename, results_dict)
        """
        # Initialize client
        client = create_client(provider, api_key, custom_endpoint=custom_endpoint)
        
        results = []
        total_questions = self.count_questions(task_files)
        current_question = 0
        
        if progress_callback:
            progress_callback(0, total_questions, "Loading tasks and initializing benchmark...")
        
        api_stats = {
            "total_time": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "response_times": [],
            "question_count": 0
        }
        
        # Process each task file
        for task_file_idx, task_file in enumerate(task_files, 1):
            if progress_callback:
                progress_callback(current_question, total_questions, f"Processing {task_file}...")
            
            # Extract task name from filename (e.g., "task_group1_basic.json" -> "Basic")
            task_name = task_file.replace("task_group", "").replace(".json", "")
            # Extract just the name part after the number (e.g., "1_basic" -> "basic")
            if "_" in task_name:
                task_name = task_name.split("_", 1)[1].replace("_", " ").title()
            
            # Load questions
            try:
                with open(f"{self.tasks_dir}/{task_file}", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        questions = [item["question"] for item in data if isinstance(item, dict) and item.get("question")]
                    elif isinstance(data, dict) and data.get("question"):
                        questions = [data["question"]]
                    else:
                        questions = []
            except Exception as e:
                if progress_callback:
                    progress_callback(current_question, total_questions, f"Error loading {task_file}: {str(e)}")
                continue
            
            # Process each question
            for idx, question in enumerate(questions, 1):
                # Check if stop was requested
                if should_stop_flag and should_stop_flag.get('should_stop'):
                    print("[DEBUG] Stop requested during question processing - exiting early")
                    # Return what we have so far with partial results
                    break
                
                current_question += 1
                
                # Get task metadata (category, dataset, document, etc.)
                task_metadata = {}
                category = "Uncategorized"
                dataset_name = None
                document_name = None
                try:
                    with open(f"{self.tasks_dir}/{task_file}", "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for item in data:
                                if item.get("question") == question:
                                    category = item.get("category", "Uncategorized")
                                    dataset_name = item.get("dataset")
                                    document_name = item.get("document")
                                    task_metadata = item
                                    break
                        elif isinstance(data, dict) and data.get("question") == question:
                            category = data.get("category", "Uncategorized")
                            dataset_name = data.get("dataset")
                            document_name = data.get("document")
                            task_metadata = data
                except Exception:
                    pass
                
                # Load dataset preview
                dataset_preview = ""
                if dataset_name:
                    dataset_path = Path(self.datasets_dir) / dataset_name
                    if dataset_path.exists():
                        try:
                            with open(dataset_path, "r", encoding="utf-8") as f:
                                reader = csv_module.reader(f)
                                rows = list(reader)
                            header = rows[0] if rows else []
                            preview_rows = rows[1:] if len(rows) > 1 else []
                            csv_block = "\n".join([", ".join(row) for row in preview_rows])
                            dataset_preview = f"Dataset '{dataset_name}'\nColumns: {', '.join(header)}\nPreview:\n{csv_block}\n"
                        except Exception:
                            dataset_preview = f"Dataset '{dataset_name}' could not be loaded."
                
                # Load document content
                document_content = ""
                if document_name:
                    document_path = Path(self.documents_dir) / document_name
                    if document_path.exists():
                        try:
                            with open(document_path, "r", encoding="utf-8") as f:
                                doc_text = f.read()
                            document_content = f"Document '{document_name}':\n{doc_text}\n"
                        except Exception:
                            document_content = f"Document '{document_name}' could not be loaded."
                
                # Build prompt
                question_with_instructions = add_answer_formatting_instructions(question)
                prompt_parts = []
                if dataset_preview:
                    prompt_parts.append(dataset_preview)
                if document_content:
                    prompt_parts.append(document_content)
                prompt_parts.append(question_with_instructions)
                full_prompt = "\n".join(prompt_parts)
                
                # Call model
                if progress_callback:
                    progress_callback(
                        current_question,
                        total_questions,
                        f"Task: {task_name} - Question {idx}/{len(questions)}",
                        task_group_progress=idx,
                        task_group_total=len(questions)
                    )
                
                start_time = time.time()
                try:
                    # Call the API with timeout
                    timeout_seconds = 300  # 5 minutes per question
                    resp = client.generate_content(model, full_prompt, timeout_seconds=timeout_seconds)
                    response_time = time.time() - start_time
                    
                    text = getattr(resp, "text", None)
                    if text is None:
                        try:
                            text = json.dumps(resp, default=str)
                        except Exception:
                            text = str(resp)
                    
                    # Extract token information
                    usage_metadata = getattr(resp, "usage_metadata", None)
                    input_tokens = 0
                    output_tokens = 0
                    if usage_metadata:
                        input_tokens = getattr(usage_metadata, "prompt_token_count", 0)
                        output_tokens = getattr(usage_metadata, "candidates_token_count", 0)
                    
                    # Track stats
                    api_stats["total_time"] += response_time
                    api_stats["total_input_tokens"] += input_tokens
                    api_stats["total_output_tokens"] += output_tokens
                    api_stats["response_times"].append(response_time)
                    api_stats["question_count"] += 1
                
                except Exception as e:
                    response_time = time.time() - start_time
                    text = f"ERROR: {e}"
                    input_tokens = 0
                    output_tokens = 0
                    api_stats["response_times"].append(response_time)
                    api_stats["question_count"] += 1
                
                # Extract final answer
                final_answer = extract_final_answer(text)
                
                # Store result
                answer = {
                    "api": model,
                    "task_file": task_file,
                    "category": category,
                    "question": question,
                    "final_answer": final_answer,
                    "prompt": full_prompt.split("\n"),
                    "response": text.split("\n"),
                    "performance": {
                        "response_time_seconds": round(response_time, 3),
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens
                    }
                }
                results.append(answer)
                
                # Save incrementally
                today = datetime.datetime.now().strftime("%Y%m%d")
                model_name = model.replace("models/", "").replace("/", "_")
                filename = f"{self.results_dir}/{model_name}_{today}_task_groups.json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2)
        
        # Prepare results metadata
        today = datetime.datetime.now().strftime("%Y%m%d")
        model_name = model.replace("models/", "").replace("/", "_")
        filename = f"{self.results_dir}/{model_name}_{today}_task_groups.json"
        
        results_metadata = {
            "filename": filename,
            "provider": provider,
            "model": model,
            "tasks_processed": task_files,
            "total_questions": total_questions,
            "questions_completed": api_stats["question_count"],
            "statistics": {
                "total_time": api_stats["total_time"],
                "avg_time_per_question": api_stats["total_time"] / api_stats["question_count"] if api_stats["question_count"] > 0 else 0,
                "total_tokens": api_stats["total_input_tokens"] + api_stats["total_output_tokens"],
                "input_tokens": api_stats["total_input_tokens"],
                "output_tokens": api_stats["total_output_tokens"]
            }
        }
        
        if progress_callback:
            progress_callback(total_questions, total_questions, "Benchmark completed!")
        
        return filename, results_metadata
