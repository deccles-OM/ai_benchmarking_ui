#!/usr/bin/env python3
"""
Generate a detailed comparison table of expected vs actual answers for benchmark evaluation.
Outputs a CSV file with all questions showing expected answers, AI answers, and evaluation scores.
"""

import json
import csv
from pathlib import Path
import re
import sys


def format_evaluation_criteria(eval_criteria: dict) -> str:
    """Format evaluation_criteria dict into a readable string."""
    if not eval_criteria:
        return ""
    
    parts = []
    if eval_criteria.get("required_elements"):
        parts.append("Required: " + ", ".join(eval_criteria["required_elements"]))
    if eval_criteria.get("forbidden_elements"):
        parts.append("Forbidden: " + ", ".join(eval_criteria["forbidden_elements"]))
    
    return " | ".join(parts)


def generate_answer_comparison_table(response_file: str, evaluation_file: str = None, benchmark_dir: str = "ford_data_analyst_benchmark"):
    """
    Generate a comparison table of expected vs actual answers with evaluation scores.
    
    Args:
        response_file: Path to the response JSON file
        evaluation_file: Path to the evaluation results JSON (optional - will use response_file stem to find it)
        benchmark_dir: Path to the benchmark directory
    """
    
    # Load responses
    response_path = Path(response_file)
    with open(response_path, 'r', encoding='utf-8') as f:
        responses = json.load(f)
    
    # Load evaluation results if available
    eval_results = {}
    if evaluation_file is None:
        # Try to find evaluation file with same stem name but ending with _evaluation.json
        eval_file = response_path.parent / f"{response_path.stem}_evaluation.json"
    else:
        eval_file = Path(evaluation_file)
    
    if eval_file.exists():
        try:
            with open(eval_file, 'r', encoding='utf-8') as f:
                eval_data = json.load(f)
                # Build lookup by task_id (use 'results' key from new evaluation format)
                results_list = eval_data.get("results", eval_data.get("task_results", []))
                for task_result in results_list:
                    task_id = task_result.get("task_id")
                    if task_id:
                        eval_results[task_id] = task_result
        except Exception as e:
            print(f"[Warning] Could not load evaluation file: {e}")
    
    # Load task definitions
    tasks_dir = Path(benchmark_dir) / "tasks"
    tasks_by_id = {}  # Map task_id to full task dict
    tasks_by_group = {}
    
    for task_file in sorted(tasks_dir.glob("task_group*.json")):
        with open(task_file, 'r', encoding='utf-8') as f:
            tasks = json.load(f)
            task_key = task_file.stem
            tasks_by_group[task_key] = tasks
            # Build id lookup
            for task in tasks:
                task_id = task.get("task_id")
                if task_id:
                    tasks_by_id[task_id] = task
    
    # Track position in each task group
    task_group_positions = {}
    # Generate comparison rows
    rows = []
    for i, response in enumerate(responses, 1):
        task_file = response.get('task_file', '')
        question = response.get('question', '')
        ai_answer = response.get('final_answer', '')
        
        # Get task from response metadata and lookup
        task_key = task_file.replace('.json', '')
        task_list = tasks_by_group.get(task_key, [])
        
        # Get position for this response in the task group
        if task_key not in task_group_positions:
            task_group_positions[task_key] = 0
        
        pos = task_group_positions[task_key]
        if pos < len(task_list):
            task = task_list[pos]
            task_group_positions[task_key] += 1
        else:
            task = task_list[0] if task_list else {}
        
        task_id = task.get('task_id', f'Q{i}')
        category = task.get('category', 'Unknown')
        correct_answer = task.get('correct_answer', '')
        evaluation_criteria = task.get('evaluation_criteria', {})
        
        # Build expected answer display
        if correct_answer and str(correct_answer).strip():
            expected_display = str(correct_answer)
        else:
            # Show evaluation criteria instead
            expected_display = format_evaluation_criteria(evaluation_criteria)
        
        # Truncate for display
        expected_str = expected_display if len(expected_display) < 300 else expected_display[:300] + '...'
        actual_str = str(ai_answer).strip() if len(str(ai_answer).strip()) < 300 else str(ai_answer).strip()[:300] + '...'
        
        # Get score from evaluation results if available
        score_display = ""
        if task_id in eval_results:
            eval_result = eval_results[task_id]
            score = eval_result.get("weighted_points", 0)
            max_points = eval_result.get("max_points", 10)
            pct = (score / max_points * 100) if max_points > 0 else 0
            score_display = f"{score:.1f}/{max_points} ({pct:.0f}%)"
        else:
            score_display = "N/A"
        
        rows.append({
            'Question #': i,
            'Task ID': task_id,
            'Category': category,
            'Question': question[:80] + '...' if len(question) > 80 else question,
            'Expected/Criteria': expected_str,
            'AI Answer': actual_str,
            'Score': score_display
        })
    
    # Write to CSV
    output_file = response_path.parent / f"{response_path.stem}_answer_comparison.csv"
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'Question #', 'Task ID', 'Category', 'Question', 'Expected/Criteria', 'AI Answer', 'Score'
        ])
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n[OK] Answer comparison table saved to: {output_file.name}")
    
    # Print summary to console
    if eval_results:
        valid_scores = [eval_results.get(row['Task ID'], {}).get('score', 0) for row in rows if row['Task ID'] in eval_results]
        if valid_scores:
            avg_score = sum(valid_scores) / len(valid_scores)
            print(f"\nEvaluation Summary:")
            print(f"  Tasks Evaluated: {len(valid_scores)}/{len(rows)}")
            print(f"  Average Score: {avg_score:.1f}%")
    else:
        print(f"\nNote: No evaluation results found. CSV shows expected answers/criteria for manual review.")
    
    print(f"\nDetailed comparison available in: {output_file.name}")


if __name__ == "__main__":
    response_file = "response_models/gemini-3.1-pro-preview_20260318_task_groups.json"
    evaluation_file = None
    
    if len(sys.argv) > 1:
        response_file = sys.argv[1]
    
    if len(sys.argv) > 2:
        evaluation_file = sys.argv[2]
    
    generate_answer_comparison_table(response_file, evaluation_file)
