#!/usr/bin/env python3
"""
Evaluate benchmark results using the existing BenchmarkScorer.
Tests responses from the new task_group JSON files against correct answers.
Generates comprehensive analysis with markdown reports and performance commentary.
"""

import json
import sys
import re
from pathlib import Path
from collections import defaultdict
import statistics
from benchmark_analyst.evaluation.scorer import BenchmarkScorer

# Ensure stdout/stderr use UTF-8 encoding (helps on Windows where default may be cp1252)
try:
    # Python 3.7+: reconfigure is available
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    # Fallback: set PYTHONIOENCODING at runtime if possible (best-effort)
    try:
        import os
        os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    except Exception:
        pass


def extract_final_answer(response_text):
    """
    Extract the final answer from response text using smart heuristics.
    
    Strategies (in priority order):
    1. Look for the LAST occurrence of **Answer:** marker (handles multi-answer responses)
    2. For explanation questions, capture more content (up to next major section)
    3. Check if extracted text is pandas metadata and try to parse pandas output
    4. Look for Answer: pattern without markdown
    5. If response contains code blocks, extract ONLY if substantial and no Answer marker found
    6. Try to extract ranking from pandas output
    7. Fall back to last non-empty line
    
    Args:
        response_text: The full response text (string or array)
        
    Returns:
        The extracted final answer as a string
    """
    # Convert array to string if needed
    if isinstance(response_text, list):
        text = '\n'.join(response_text)
    else:
        text = str(response_text)
    
    text = text.strip()
    if not text:
        return ''
    
    # Strategy 1: Find ALL **Answer:** occurrences and use the LAST one
    # This handles cases where code blocks are between answer markers
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
                # Extract code from this block - be flexible with newlines/spaces
                code_pattern = r'```(?:\w+)?\s*\n(.*?)\n```'
                code_match = re.search(code_pattern, extracted, re.DOTALL)
                if code_match:
                    code = code_match.group(1).strip()
                    if code and len(code) > 3:  # Substantial code
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
    
    # Strategy 3: Fallback - look for answer-like content after Answer marker
    answer_pattern2 = r'(?:^|\n)\*\*(?:Final\s+)?Answer:\*\*\s*(.+?)(?=\n\*\*|$)'
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



def generate_markdown_report(results_summary, response_path, total_score, max_score, avg_score):
    """
    Generate a comprehensive markdown report with tables, metrics, and commentary.
    Uses standardized template with Key Results summary followed by detailed analysis.
    
    Args:
        results_summary: Dictionary with aggregated results by category
        response_path: Path to the response JSON file
        total_score: Total score achieved
        max_score: Maximum possible score
        avg_score: Average score percentage
    """
    
    percentage = (total_score / max_score * 100) if max_score > 0 else 0
    
    # Identify strengths and weaknesses
    category_scores = {}
    for category, data in results_summary.items():
        if data['count'] > 0:
            category_percentage = (data['score'] / data['max_points'] * 100) if data['max_points'] > 0 else 0
            category_scores[category] = {
                'score': data['score'],
                'max': data['max_points'],
                'percentage': category_percentage
            }
    
    sorted_categories = sorted(category_scores.items(), key=lambda x: x[1]['percentage'], reverse=True)
    
    # Determine status indicators
    def get_status_emoji(percentage):
        if percentage >= 80:
            return "🟢"
        elif percentage >= 60:
            return "🟡"
        elif percentage >= 50:
            return "🟡"
        else:
            return "🔴"
    
    def get_status_text(percentage):
        if percentage >= 80:
            return "Excellent"
        elif percentage >= 60:
            return "Good"
        elif percentage >= 50:
            return "Fair"
        else:
            return "Weak"
    
    # Build markdown report with standardized template
    report = []
    report.append("# Benchmark Evaluation Results")
    report.append("")
    report.append(f"**Model:** {response_path.stem}")
    report.append(f"**Date:** March 16, 2026")
    report.append("")
    report.append("---")
    report.append("")
    report.append("## Key Results")
    report.append("")
    report.append(f"**Overall Score:** {total_score:.1f} / {max_score} points **({percentage:.1f}%)**")
    report.append("")
    
    # Quick category performance with emojis
    report.append("### Performance by Category")
    report.append("")
    report.append("| Category | Score | Status |")
    report.append("|----------|-------|--------|")
    
    for category, scores in sorted_categories:
        emoji = get_status_emoji(scores['percentage'])
        status = get_status_text(scores['percentage'])
        if category == sorted_categories[0][0]:
            report.append(f"| {emoji} **{category}** | **{scores['percentage']:.2f}%** | Best |")
        elif category == sorted_categories[-1][0]:
            report.append(f"| {emoji} {category} | **{scores['percentage']:.2f}%** | Weakest |")
        else:
            report.append(f"| {emoji} {category} | {scores['percentage']:.2f}% | {status} |")
    
    report.append("")
    
    # Quick Findings
    report.append("### Quick Findings")
    report.append("")
    report.append("**Strengths:**")
    strengths_found = False
    strengths_list = []
    for i, (category, scores) in enumerate(sorted_categories[:3]):
        if scores['percentage'] >= 60:
            report.append(f"✅ {category}: {scores['percentage']:.2f}%")
            strengths_list.append(category)
            strengths_found = True
    if not strengths_found:
        top_cat = sorted_categories[0]
        report.append(f"✅ {top_cat[0]}: {top_cat[1]['percentage']:.2f}% (Relatively strongest)")
        strengths_list.append(top_cat[0])
    
    report.append("")
    report.append("**Weaknesses:**")
    weaknesses_identified = []
    
    # Find weaknesses - categories that are NOT in the strengths list
    # and are among the worst performers
    worst_categories = sorted_categories[-2:]  # Bottom 2 categories
    for category, scores in worst_categories:
        if category not in strengths_list:  # Don't repeat strengths as weaknesses
            weaknesses_identified.append(f"❌ {category}: {scores['percentage']:.2f}%")
    
    if weaknesses_identified:
        for weakness in weaknesses_identified:
            report.append(weakness)
    else:
        report.append("- No significant weaknesses identified")

    
    report.append("")
    report.append("---")
    report.append("")
    report.append("## Detailed Analysis")
    report.append("")
    
    # In-Depth Insights
    report.append("### In-Depth Insights")
    report.append("")
    
    # Top category insight
    top_cat, top_scores = sorted_categories[0]
    report.append(f"**{top_cat} ({top_scores['percentage']:.2f}%)**")
    if top_scores['percentage'] >= 80:
        report.append("- Demonstrates excellent capability and understanding")
    elif top_scores['percentage'] >= 60:
        report.append("- Shows good performance and solid capability")
    else:
        report.append("- Relatively strongest category but still shows performance gaps")
    report.append(f"- {top_cat} is the strongest performing area")
    report.append("")
    
    # Bottom category insight
    bottom_cat, bottom_scores = sorted_categories[-1]
    report.append(f"**{bottom_cat} ({bottom_scores['percentage']:.2f}%)**")
    if bottom_scores['percentage'] < 50:
        report.append(f"- Shows significant weaknesses and requires substantial improvement")
    else:
        report.append(f"- Shows performance gaps and opportunities for development")
    report.append(f"- {bottom_cat} is the weakest performing area")
    report.append("")
    
    # Variability analysis
    variance = sorted_categories[0][1]['percentage'] - sorted_categories[-1][1]['percentage']
    if variance > 40:
        report.append(f"**Performance Consistency:** {variance:.1f}% spread between strongest and weakest")
        report.append("- High variability indicates inconsistent capabilities across task domains")
    elif variance > 20:
        report.append(f"**Performance Consistency:** {variance:.1f}% spread between strongest and weakest")
        report.append("- Moderate variability suggests some inconsistency in capabilities")
    else:
        report.append(f"**Performance Consistency:** {variance:.1f}% spread between strongest and weakest")
        report.append("- Good consistency across task domains")
    report.append("")
    
    # Overall assessment
    report.append("### Overall Assessment")
    report.append("")
    if percentage >= 80:
        report.append(f"The model demonstrates **excellent overall performance** at {percentage:.1f}%, with strong and consistent capability across most task categories.")
    elif percentage >= 65:
        report.append(f"The model shows **good overall performance** at {percentage:.1f}%, with clear strengths in some areas and opportunities for improvement in others.")
    elif percentage >= 50:
        report.append(f"The model demonstrates **moderate overall performance** at {percentage:.1f}%, with significant variation across task categories and room for improvement.")
    else:
        report.append(f"The model shows **limited overall performance** at {percentage:.1f}%. Substantial improvements are needed across multiple task areas.")
    report.append("")
    
    # Performance tier chart
    high_performers = sum(1 for _, s in sorted_categories if s['percentage'] >= 80)
    good_performers = sum(1 for _, s in sorted_categories if 60 <= s['percentage'] < 80)
    fair_performers = sum(1 for _, s in sorted_categories if 50 <= s['percentage'] < 60)
    poor_performers = sum(1 for _, s in sorted_categories if s['percentage'] < 50)
    
    report.append("### Performance Tier Summary")
    report.append("")
    report.append("| Tier | Count | Percentage |")
    report.append("|------|-------|-----------|")
    report.append(f"| Excellent (≥80%) | {high_performers} | {high_performers/len(sorted_categories)*100:.0f}% |")
    report.append(f"| Good (60-79%) | {good_performers} | {good_performers/len(sorted_categories)*100:.0f}% |")
    report.append(f"| Fair (50-59%) | {fair_performers} | {fair_performers/len(sorted_categories)*100:.0f}% |")
    report.append(f"| Poor (<50%) | {poor_performers} | {poor_performers/len(sorted_categories)*100:.0f}% |")
    report.append("")
    
    # Recommendations
    report.append("## Recommendations")
    report.append("")
    report.append("### Priority Improvement Areas")
    report.append("")
    
    recommendations = []
    for i, (category, scores) in enumerate(sorted_categories[-3:], 1):
        if scores['percentage'] < 70:
            recommendations.append((i, category, scores['percentage']))
    
    if recommendations:
        for idx, (priority, category, score) in enumerate(recommendations, 1):
            report.append(f"**Priority {idx}: {category} ({score:.2f}%)**")
            report.append(f"- Focus on improving {category.lower()}")
            report.append(f"- Current performance: {score:.2f}% - needs development")
            report.append("")
    else:
        report.append("- Most categories performing above 70%")
        report.append("- Continue focus on maintaining strong performance")
        report.append("")
    
    report.append("### General Improvement Strategy")
    report.append("")
    
    point_num = 1
    
    if variance > 40:
        report.append(f"{point_num}. **Address Inconsistency**: The large performance gap suggests variable capabilities. Focus on consistent improvement across all domains.")
        point_num += 1
    
    if percentage < 50:
        report.append(f"{point_num}. **Foundational Skills**: Review core competencies and fundamental task understanding.")
    elif percentage < 65:
        report.append(f"{point_num}. **Bridge Performance Gaps**: Implement targeted training for weaker categories.")
    else:
        report.append(f"{point_num}. **Maintain Momentum**: Continue improving weak areas while sustaining strengths.")
    
    point_num += 1
    report.append(f"{point_num}. **Iterative Testing**: Re-evaluate regularly to track improvement progress.")
    report.append("")
    
    # Footer
    report.append("---")
    report.append("")
    report.append(f"*Report generated from {response_path.name}*")
    report.append(f"*Evaluation Date: March 16, 2026*")
    
    return "\n".join(report)



def evaluate_responses(response_file_path: str, benchmark_dir: str = "benchmark_analyst/data"):
    """
    Evaluate AI responses from a benchmark result JSON file.
    
    Args:
        response_file_path: Path to the JSON file with responses (e.g., benchmarks/response_models/gemini-2.5-flash_20260316_task_group1_basic.json)
        benchmark_dir: Path to the benchmark directory containing tasks and datasets (default: benchmark_analyst/data)
    """
    
    # Initialize scorer
    scorer = BenchmarkScorer(benchmark_dir)
    
    # Load task definitions
    tasks = scorer.load_tasks()
    print(f"[OK] Loaded {len(tasks)} task files from {scorer.tasks_dir}")
    
    # Load responses from the JSON file
    response_path = Path(response_file_path)
    if not response_path.exists():
        print(f"[ERROR] Response file not found: {response_path}")
        return
    
    with open(response_path, 'r', encoding='utf-8') as f:
        responses = json.load(f)
    
    print(f"[OK] Loaded {len(responses)} responses from {response_path.name}")
    print("\n" + "=" * 100)
    print("EVALUATING RESPONSES")
    print("=" * 100 + "\n")
    
    # Score each response
    total_score = 0
    max_score = 0
    results = []
    # Track scores and performance aggregates per category
    results_by_category = defaultdict(lambda: {
        'score': 0,
        'max_points': 0,
        'count': 0,
        'response_time': 0.0,
        'input_tokens': 0,
        'output_tokens': 0,
        'total_tokens': 0
    })

    # Overall performance stats
    perf_stats = {
        'response_times': [],
        'input_tokens': 0,
        'output_tokens': 0,
        'total_tokens': 0
    }
    
    # Track position within each task group for proper matching
    task_group_positions = defaultdict(int)
    
    def pretty_print(text):
        if not isinstance(text, str):
            return text
        return text.replace('\\n', '\n').replace('\\t', '\t').strip()

    # Safe print wrapper to avoid UnicodeEncodeError on Windows consoles
    def safe_print(*args, **kwargs):
        try:
            print(*args, **kwargs)
        except UnicodeEncodeError:
            safe_args = []
            for a in args:
                if isinstance(a, str):
                    safe_args.append(a.encode('utf-8', errors='replace').decode('utf-8'))
                else:
                    safe_args.append(a)
            print(*safe_args, **kwargs)

    for i, response_item in enumerate(responses, 1):
        api = response_item.get('api', 'unknown')
        task_file = response_item.get('task_file', 'unknown')
        question = response_item.get('question', '')
        
        # Extract final answer using smart heuristics
        if 'final_answer' in response_item and response_item['final_answer']:
            # Use pre-extracted final_answer if available
            response = response_item['final_answer']
        else:
            # Extract from full response for backward compatibility with old JSON files
            resp_raw = response_item.get('response', '')
            response = extract_final_answer(resp_raw)
        
        response_task_id = response_item.get('task_id', None)

        # Extract the task name from task_file (e.g., "task_group1_basic.json" -> "task_group1_basic")
        task_key = task_file.replace('.json', '')

        # Get the correct answer from the matching task in the group
        task_data = tasks.get(task_key, {})
        task_item = None
        
        # Try to match by task_id first (if present)
        if isinstance(task_data, list) and response_task_id:
            for t in task_data:
                if t.get('task_id') == response_task_id:
                    task_item = t
                    break
        
        # If no match by task_id, try matching by question text
        if not task_item and isinstance(task_data, list):
            for t in task_data:
                if t.get('question', '') == question:
                    task_item = t
                    break
        
        # If still no match, use position within the task group
        if not task_item and isinstance(task_data, list):
            pos = task_group_positions[task_key]
            if pos < len(task_data):
                task_item = task_data[pos]
                task_group_positions[task_key] += 1
        
        # Fallback if task_data is a single dict or other format
        if not task_item:
            if isinstance(task_data, list) and len(task_data) > 0:
                task_item = task_data[0]
            else:
                task_item = task_data

        # Get answer_type from task (defaulting to 'text' for backward compatibility)
        answer_type = task_item.get('answer_type', task_item.get('task_type', 'text'))
        category = task_item.get('category', 'Uncategorized')
        points = task_item.get('points', 10)
        task_id = task_item.get('task_id', 'UNKNOWN')

        # Pretty-print response and question for readability
        pretty_response = pretty_print(response)
        pretty_question = pretty_print(question)

        # Use unified scorer.score_task() for consistent evaluation across all tasks
        # This applies task-specific weighting (factual vs code/explanation)
        score_result = scorer.score_task(task_item, response)
        
        weighted_points = score_result.get('score', 0)
        accuracy = score_result.get('accuracy', 0)
        reasoning = score_result.get('reasoning', 0)
        
        # Compute combined_score for display (score_result already has weighted points)
        combined_score = weighted_points / points if points > 0 else 0
        
        total_score += weighted_points
        max_score += points
        results_by_category[category]['score'] += weighted_points
        results_by_category[category]['max_points'] += points
        results_by_category[category]['count'] += 1

        # Performance metrics from response (if available)
        perf = response_item.get('performance', {}) or {}
        resp_time = perf.get('response_time_seconds', perf.get('response_time', 0)) or 0
        input_tokens = perf.get('input_tokens', perf.get('prompt_token_count', 0)) or 0
        output_tokens = perf.get('output_tokens', perf.get('candidates_token_count', 0)) or 0
        total_tokens = perf.get('total_tokens', input_tokens + output_tokens)

        # Accumulate per-category
        results_by_category[category]['response_time'] += float(resp_time)
        results_by_category[category]['input_tokens'] += int(input_tokens)
        results_by_category[category]['output_tokens'] += int(output_tokens)
        results_by_category[category]['total_tokens'] += int(total_tokens)

        # Accumulate overall
        try:
            perf_stats['response_times'].append(float(resp_time))
        except Exception:
            pass
        perf_stats['input_tokens'] += int(input_tokens)
        perf_stats['output_tokens'] += int(output_tokens)
        perf_stats['total_tokens'] += int(total_tokens)

        status = "[OK]" if combined_score >= 0.7 else "[FAIL]" if combined_score < 0.3 else "[WARN]"
        try:
            question_preview = str(pretty_question)[:80]
            response_preview = str(pretty_response)[:100]
            safe_print(f"{status} Task {i}/{len(responses)}: {task_key} [{category}] {task_id}")
            safe_print(f"   Score: {combined_score:.2%} (Accuracy: {accuracy:.2%}, Reasoning: {reasoning:.2%})")
            safe_print(f"   Question: {question_preview}...")
            safe_print(f"   Response: {response_preview}")
        except Exception:
            # On any printing error, fallback to a minimal status line
            try:
                print("{} Task {}/{}: {} [{}] {}".format(status, i, len(responses), task_key, category, task_id))
            except Exception:
                # Last-resort: ignore printing errors so evaluation continues
                pass
        print()

        results.append({
            'task_file': task_file,
            'task_id': task_id,
            'category': category,
            'combined_score': combined_score,
            'accuracy': accuracy,
            'reasoning': reasoning,
            'weighted_points': weighted_points,
            'max_points': points,
            'pretty_response': pretty_response,
            'performance': {
                'response_time_seconds': float(resp_time),
                'input_tokens': int(input_tokens),
                'output_tokens': int(output_tokens),
                'total_tokens': int(total_tokens)
            }
        })
    
    # Summary
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    avg_score = total_score / max_score if total_score > 0 and max_score > 0 else 0
    print(f"Total Score: {total_score:.1f}/{max_score} ({(total_score/max_score*100 if max_score > 0 else 0):.1f}%)")
    print(f"API: {responses[0].get('api', 'unknown') if responses else 'unknown'}")
    print(f"Task Categories: {len(results_by_category)}")
    # Performance summary
    total_questions = sum(d['count'] for d in results_by_category.values())
    total_resp_count = len(perf_stats['response_times'])
    avg_response_time = (statistics.mean(perf_stats['response_times']) if perf_stats['response_times'] else 0)
    median_response_time = (statistics.median(perf_stats['response_times']) if perf_stats['response_times'] else 0)
    total_input_tokens = perf_stats['input_tokens']
    total_output_tokens = perf_stats['output_tokens']
    total_tokens = perf_stats['total_tokens']
    avg_input_tokens = (total_input_tokens / total_resp_count) if total_resp_count > 0 else 0
    avg_output_tokens = (total_output_tokens / total_resp_count) if total_resp_count > 0 else 0
    avg_total_tokens = (total_tokens / total_resp_count) if total_resp_count > 0 else 0

    print('\n** Performance Metrics **')
    print(f'  Questions counted: {total_questions} (with perf data: {total_resp_count})')
    print(f'  Avg response time (s): {avg_response_time:.3f} | Median: {median_response_time:.3f}')
    print(f'  Avg tokens (in/out/total): {avg_input_tokens:.1f}/{avg_output_tokens:.1f}/{avg_total_tokens:.1f}')
    
    print("\n** Category Breakdown **")
    for category, data in sorted(results_by_category.items(), key=lambda x: (x[1]['score']/x[1]['max_points'] if x[1]['max_points'] > 0 else 0), reverse=True):
        pct = (data['score']/data['max_points']*100) if data['max_points'] > 0 else 0
        print(f"  {category}: {data['score']:.1f}/{data['max_points']} ({pct:.1f}%)")
    
    # Save results to JSON
    results_file = response_path.parent / f"{response_path.stem}_evaluation.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            'source_file': str(response_path),
            'total_score': total_score,
            'max_score': max_score,
            'average_score': avg_score,
            'percentage': (total_score/max_score*100) if max_score > 0 else 0,
            'category_breakdown': {
                cat: {
                    'score': data['score'],
                    'max_points': data['max_points'],
                    'percentage': (data['score']/data['max_points']*100) if data['max_points'] > 0 else 0
                }
                for cat, data in results_by_category.items()
            },
            'performance_summary': {
                'questions_with_perf': total_resp_count,
                'avg_response_time_seconds': avg_response_time,
                'median_response_time_seconds': median_response_time,
                'total_input_tokens': total_input_tokens,
                'total_output_tokens': total_output_tokens,
                'total_tokens': total_tokens,
                'avg_input_tokens': avg_input_tokens,
                'avg_output_tokens': avg_output_tokens,
                'avg_total_tokens': avg_total_tokens
            },
            'results': results
        }, f, indent=2)
    
    print(f"\n[OK] Detailed JSON results saved to: {results_file.name}")
    
    # Generate and save markdown report
    markdown_report = generate_markdown_report(
        results_by_category,
        response_path,
        total_score,
        max_score,
        avg_score
    )
    # Append performance summary to markdown report
    perf_lines = []
    perf_lines.append('\n## Performance Metrics')
    perf_lines.append('\n')
    perf_lines.append(f"- Questions counted: {total_questions} (with perf data: {total_resp_count})")
    perf_lines.append(f"- Average response time (s): {avg_response_time:.3f}")
    perf_lines.append(f"- Median response time (s): {median_response_time:.3f}")
    perf_lines.append(f"- Total tokens (in/out/total): {total_input_tokens}/{total_output_tokens}/{total_tokens}")
    perf_lines.append(f"- Average tokens per question (in/out/total): {avg_input_tokens:.1f}/{avg_output_tokens:.1f}/{avg_total_tokens:.1f}")
    # Per-category performance averages
    perf_lines.append('\n### Per-category performance averages')
    for cat, data in sorted(results_by_category.items(), key=lambda x: (x[1]['score']/x[1]['max_points'] if x[1]['max_points']>0 else 0), reverse=True):
        cnt = data.get('count', 0)
        if cnt > 0:
            avg_rt = data.get('response_time', 0.0) / cnt
            avg_in = data.get('input_tokens', 0) / cnt
            avg_out = data.get('output_tokens', 0) / cnt
            avg_tot = data.get('total_tokens', 0) / cnt
            perf_lines.append(f"- {cat}: avg_time_s={avg_rt:.3f}, avg_tokens(in/out/total)={avg_in:.1f}/{avg_out:.1f}/{avg_tot:.1f} (n={cnt})")
        else:
            perf_lines.append(f"- {cat}: no performance data")
    markdown_report = markdown_report + '\n'.join(perf_lines)
    
    report_file = response_path.parent / f"{response_path.stem}_RESULTS.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(markdown_report)
    
    print(f"[OK] Markdown report saved to: {report_file.name}")
    
    # Generate answer comparison table
    print("\n[Progress] Generating answer comparison table...")
    try:
        # Import the comparison function from the packaged module to avoid import errors
        from benchmark_analyst.core.comparison import generate_answer_comparison_table
        # Pass the benchmark_dir so the comparator can find task definitions
        generate_answer_comparison_table(str(response_path), benchmark_dir=benchmark_dir)
    except Exception as e:
        print(f"[WARN] Could not generate comparison table: {e}")



if __name__ == "__main__":
    # Default file to evaluate
    response_file = "response_models/gemini-3.1-pro-preview_20260317_task_groups.json"
    
    if len(sys.argv) > 1:
        response_file = sys.argv[1]
    # Optional second argument: benchmark directory containing tasks/datasets/docs
    benchmark_dir = "benchmark_analyst/data"
    if len(sys.argv) > 2:
        benchmark_dir = sys.argv[2]

    evaluate_responses(response_file, benchmark_dir=benchmark_dir)
