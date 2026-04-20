#!/usr/bin/env python3
"""Ford Data Analyst Super Benchmark (FDASB) Runner - Professional v3.7
Main script to execute the benchmark against AI models.
Supports: 235 tasks, 27 categories, timing, SQL dialects, code review, security, testing
"""

import json
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation.scorer import BenchmarkScorer


def display_benchmark_info():
    """Display benchmark information."""
    print("\n" + "=" * 100)
    print("FORD DATA ANALYST SUPER BENCHMARK (FDASB) - ADVANCED v3.7")
    print("=" * 100)
    print("\n📊 BENCHMARK STRUCTURE (27 Categories, 235 Tasks, 7,115 Points):\n")
    
    categories = [
        ("Tier 1: Data Fundamentals", ["Basic", "Cleaning", "EDA", "Statistics", "SQL", "Business"]),
        ("Tier 2: Advanced Data", ["Instructions", "Dataform", "SQL Dialects", "Complex SQL", "Prompt Efficiency", "Documents"]),
        ("Tier 3: Engineering", ["Web Dev", "Pipelines", "Architecture", "Debugging", "Performance", "Code Review", "Libraries"]),
        ("Tier 4: Professional", ["Communication", "Security", "Testing"]),
        ("Tier 5: Stress Testing", ["Saturation & Complexity", "Long-Context", "Sustained Performance"]),
        ("Tier 6: Cognitive Skills", ["Context Switching"]),
        ("Tier 7: Content Generation", ["Writing & Generation"])
    ]
    
    for category, items in categories:
        print(f"  {category}:")
        for item in items:
            print(f"    • {item}")
    
    print("\n📈 KEY FEATURES:")
    print("  ✓ Timing metrics - measure response speed per task")
    print("  ✓ Saturation testing - find complexity breaking points")
    print("  ✓ Long-context handling - maintain accuracy with 100+ constraints")
    print("  ✓ Fatigue testing - detect degradation over 10-task marathon")
    print("  ✓ Context switching - test cognitive flexibility and clarity")
    print("  ✓ Content generation - exact word counts, tone adaptation, synthesis")
    print("  ✓ Code review - identify missing functions and validation issues")
    print("  ✓ Security analysis - SQL injection, auth, encryption detection")
    print("  ✓ Instruction following - test logical flow and ordering")
    print("  ✓ SQL dialects - BigQuery, MySQL, PostgreSQL validation")
    print("  ✓ Testing expertise - unit/integration tests, CI/CD design")
    print("  ✓ Library management - version conflicts and migrations")
    print("=" * 100 + "\n")


def load_all_tasks():
    """Load all tasks from the benchmark."""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    tasks_dir = script_dir / "tasks"
    all_tasks = {}
    
    for task_file in sorted(tasks_dir.glob("*.json")):
        with open(task_file, 'r') as f:
            level_name = task_file.stem
            all_tasks[level_name] = json.load(f)
    
    return all_tasks


def count_tasks():
    """Count total tasks in benchmark."""
    tasks = load_all_tasks()
    total = sum(len(level_tasks) for level_tasks in tasks.values())
    return total, len(tasks)


def run_custom_benchmark(responses):
    """Run benchmark with custom responses."""
    print("\n🚀 Scoring custom responses...\n")
    
    script_dir = Path(__file__).parent
    scorer = BenchmarkScorer(str(script_dir))
    
    results = scorer.score_benchmark(responses)
    report = scorer.generate_report(results)
    print(report)
    
    # Save results
    results_path = script_dir / "evaluation" / "results.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print("\n✅ Results saved to evaluation/results.json")


def run_example_benchmark():
    """Run with example responses."""
    print("\n🚀 Running benchmark with example responses...\n")
    
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    scorer = BenchmarkScorer(str(script_dir))
    
    # Example responses covering different task types
    example_responses = {
        # Basic tasks
        "BASIC_01": "F150",
        "BASIC_02": "328000",
        "BASIC_03": "US",
        "BASIC_04": "4",
        "BASIC_05": "10",
        
        # Data cleaning
        "CLEAN_01": "missing mileage, negative repair cost",
        "CLEAN_02": "Escape",
        "CLEAN_03": "No obvious inconsistencies",
        "CLEAN_04": "Remove or impute with mean/median",
        
        # EDA
        "EDA_01": "D14",
        "EDA_02": "Engine temp spike indicates overheating",
        "EDA_03": "Escape appears most frequently",
        "EDA_04": "US region has strongest sales",
        "EDA_05": "F150, Escape, Bronco, Mustang",
        
        # Statistics
        "STAT_01": "372.22",
        "STAT_02": "Median around 390, similar to mean",
        "STAT_03": "High variation, different demand",
        "STAT_04": "Yes, D14 is unusual at 110 vs 26 average",
        
        # SQL
        "SQL_01": "SELECT region, SUM(units_sold) FROM sales GROUP BY region",
        "SQL_02": "SELECT model, AVG(units_sold) FROM sales GROUP BY model",
        "SQL_03": "SELECT model, AVG(repair_cost) FROM warranty GROUP BY model",
        "SQL_04": "SELECT * FROM sales WHERE units_sold > 100000",
        
        # Business
        "BIZ_01": "Increase EU marketing, maintain F150 dominance, explore Asia",
        "BIZ_02": "Escape needs investigation due to claim frequency",
        "BIZ_03": "Investigate D14 for operational issues",
        "BIZ_04": "Engine failure increases warranty costs",
        
        # Instruction Following
        "INST_01": "F150 is the top model, with X warranty claims specific to F150",
        "INST_02": "US average mileage is Y with trend analysis",
        "INST_03": "D16 and others sorted by claims meeting criteria",
        "INST_04": "Anomalies: engine spike. Causes: overheating. Actions: investigate",
        "INST_05": "1) Data observation 2) Market implication 3) Risk 4) Recommendation",
        
        # Dataform
        "DF_01": "CREATE OR REPLACE TABLE... SELECT... CASE WHEN model='F150'...",
        "DF_02": "CREATE MATERIALIZED VIEW... GROUP BY region...",
        "DF_03": "WITH clean_data AS... ref()...",
        "DF_04": "INCREMENTAL TABLE... pre_operations...",
        "DF_05": "Multi-table project with dependencies and config",
        
        # SQL Dialects
        "SQLD_01": "SELECT AVG(repair_cost) FROM `project.dataset.warranty`",
        "SQLD_02": "SELECT model, SUM(...) FROM warranty GROUP BY model LIMIT 10",
        "SQLD_03": "SELECT model, ARRAY_AGG(...) FROM warranty GROUP BY model",
        "SQLD_04": "WITH RECURSIVE... PostgreSQL specific query",
        "SQLD_05": "SELECT model, COUNT(DISTINCT dealer_id) FROM sales",
        
        # Complex SQL
        "SQLC_01": "WITH filtered AS... SELECT... RANK() OVER...",
        "SQLC_02": "Subquery finding above-average regions...",
        "SQLC_03": "Multiple CTEs for cleaning, aggregation, percentiles...",
        "SQLC_04": "RECURSIVE CTE with moving average and outlier detection",
        "SQLC_05": "5+ CTEs with window functions and complex logic",
        
        # Prompt Efficiency
        "PEFF_01": "F150",
        "PEFF_02": "Escape",
        "PEFF_03": "EU has strongest demand, increase production there",
        "PEFF_04": "D14 has anomalous claims",
        "PEFF_05": "SELECT model, COUNT(*) FROM warranty GROUP BY model",
        
        # Document Reading
        "DOCREAD_01": "3-5 years coverage, 100% for defects",
        "DOCREAD_02": "Reduce claims 25% in 18 months",
        "DOCREAD_03": "BigQuery, Standard SQL, naming: stg_, dim_, fact_",
        "DOCREAD_04": "repair_cost >0, required field, USD currency",
        "DOCREAD_05": "5 key questions and required data fields",
        
        # Website Dev
        "WEB_01": "<table> with CSS styling",
        "WEB_02": "JavaScript filter function with event listeners",
        "WEB_03": "React component with useState and filters",
        "WEB_04": "Dashboard with multiple visualizations",
        "WEB_05": "Node.js API + React frontend",
        
        # Pipeline Dev
        "PIPE_01": "CSV -> cleaning -> aggregation -> output",
        "PIPE_02": "Python with pandas, error handling",
        "PIPE_03": "Validation pipeline with flagging",
        "PIPE_04": "Multi-source ETL with joining",
        "PIPE_05": "Airflow DAG with monitoring and retry logic",
        
        # Architecture
        "ARCH_01": "Source -> Storage -> Processing -> Analytics",
        "ARCH_02": "Scalable data warehouse with BigQuery",
        "ARCH_03": "Real-time streaming pipeline with alerts",
        "ARCH_04": "Enterprise ecosystem with multiple layers",
        
        # Debugging
        "DEBUG_01": "Missing model in GROUP BY clause",
        "DEBUG_02": "Filter logic error with NULL handling",
        "DEBUG_03": "Memory issues, need optimization",
        "DEBUG_04": "Investigate JOIN logic for discrepancies",
        "DEBUG_05": "Check for race conditions, caching",
        
        # Performance
        "PERF_01": "Replace LIKE with exact match or index",
        "PERF_02": "Use vectorized operations with pandas",
        "PERF_03": "Add indexes, partition by model",
        "PERF_04": "Batch processing, chunking, caching",
        "PERF_05": "Partitioning strategy, distributed processing",
        
        # Code Review & Issue Detection
        "CODREV_01": "Missing function definition or import for calculate_mean",
        "CODREV_02": "Missing quotes around date string, NULL handling issues",
        "CODREV_03": "No input validation, SQL injection risk, no error handling, no auth",
        "CODREV_04": "Data validation, error handling, logging, monitoring, retry logic",
        "CODREV_05": "No error handling, no logging, hardcoded paths, no type hints",
        
        # Library & Dependency Management
        "LIBFIX_01": "Try-except import with fallback or requirements.txt with version pinning",
        "LIBFIX_02": "pandas for unified interface with Excel and CSV support",
        "LIBFIX_03": "Check changelog, use deprecation warnings, version constraints, tests",
        "LIBFIX_04": "Performance benchmark, feature comparison, maintenance status analysis",
        "LIBFIX_05": "Virtual environments, Docker, requirements.txt, constraint files, testing",
        
        # Communication & Documentation
        "COMM_01": "Function with docstring explaining parameters, return, and purpose",
        "COMM_02": "Replace with meaningful comment explaining WHY, include context",
        "COMM_03": "Proper API spec with request/response schemas, status codes, authentication",
        "COMM_04": "Detailed comments for each CTE, explanation of joins and logic",
        "COMM_05": "Comprehensive README with setup, usage, architecture, troubleshooting",
        
        # Security & Best Practices
        "SECURE_01": "SQL injection vulnerability, password exposed, no hashing",
        "SECURE_02": "Hardcoded secrets risk, use environment variables or secrets manager",
        "SECURE_03": "Type checking, format validation, SQL prevention, XSS prevention",
        "SECURE_04": "Encryption in transit/at rest, access controls, audit logging",
        "SECURE_05": "Authentication/authorization, validation, encryption, monitoring, rate limits",
        
        # Testing & Quality Assurance
        "TEST_01": "Tests for positive, negative, zero, float, None, type errors",
        "TEST_02": "Test file existence, format validation, data integrity, error handling",
        "TEST_03": "Automated tests, mocking dependencies, fixtures, coverage goals",
        "TEST_04": "NULL handling, empty results, large datasets, boundary conditions",
        "TEST_05": "Test pyramid with unit/integration/E2E, fixtures, coverage 80%+",
        
        # Saturation & Complexity Limits
        "SAT_01": "JOIN 3 tables with CASE WHEN, GROUP BY, HAVING, error handling for nulls",
        "SAT_02": "Multi-source ETL handling schema variations, normalization, 8 derived metrics",
        "SAT_03": "Production solution: imputation, modeling, validation, explainability",
        "SAT_04": "Multi-dimensional time-series analysis, forecasting, anomaly detection",
        "SAT_05": "Complete pipeline: load→validate→clean→dedup→normalize→aggregate→analyze→model",
        
        # Long-Context Handling
        "LCTX_01": "Extract 15+ requirements, constraints, dependencies, edge cases",
        "LCTX_02": "100-line code analysis: patterns, architectural issues, security, optimization",
        "LCTX_03": "1000+ record dataset with pattern discovery maintaining accuracy",
        "LCTX_04": "20-step workflow: requirements→design→code→test→deploy→monitor with context",
        "LCTX_05": "Integrate 5 documents, resolve conflicts, create unified design",
        
        # Sustained Performance & Fatigue Testing (10-task marathon)
        "SUST_01": "Task 1/10: SELECT query",
        "SUST_02": "Task 2/10: Python function",
        "SUST_03": "Task 3/10: Dataset analysis",
        "SUST_04": "Task 4/10: Multi-step complex analysis showing no degradation",
        "SUST_05": "Task 5/10 MIDPOINT: Comprehensive code review with 5+ issues detected",
        "SUST_06": "Task 6/10: System architecture with scalable design",
        "SUST_07": "Task 7/10: Optimized query with performance justification",
        "SUST_08": "Task 8/10: Security audit finding critical issues despite fatigue",
        "SUST_09": "Task 9/10: ML pipeline implementation showing sustained quality",
        "SUST_10": "Task 10/10 FINAL: Test suite showing quality maintained vs Task 1",
        
        # Context Switching & Task Clarity
        "SWITCH_01": "SELECT region, revenue FROM customers ORDER BY revenue DESC LIMIT 10;",
        "SWITCH_02": "API endpoint: GET /warranty-claims with request params, response schema, error codes",
        "SWITCH_03": "PostgreSQL caching: materialized views, query result caching, TTL strategies",
        "SWITCH_04": "Python error handler (separate), HTML form (separate), SQL optimization (separate), API docs (separate)",
        "SWITCH_05": "Python script, SQL integration, proper context tracking, error handling architecture shown",
        "SWITCH_06": "Asks 'Do you mean optimize other pipeline? Add other feature? Create other report?' with caveats",
        "SWITCH_07": "API caching optimization: connection pools, response caching, cache invalidation strategies",
        "SWITCH_08": "def process_data(data): ... AND SELECT FROM data WHERE ... synchronized",
        "SWITCH_09": "Python variable 'data', SQL table 'data', clear distinction shown, integration correct",
        "SWITCH_10": "All 6 stages complete: Python→SQL→optimization→caching→API→tests with full context",
        
        # Writing & Content Generation
        "WRITE_01": "100-word summary (95-105 word count) covering: AI improving diagnostics 95%+ accuracy, personalized treatment, 23% readmission reduction; challenges including privacy, regulation, skepticism, training, cost barriers. AI as decision-support tool by 2030.",
        "WRITE_02": "PRD with executive summary, 3 ranked priorities: (1) Performance optimization addressing churn risk, (2) Integration layer enabling adoption, (3) UI refinement improving satisfaction. Professional business language, clear business justification.",
        "WRITE_03": "Three 150-word versions: CTO version with technical depth (multi-threaded events, async I/O, pooling, epoll); PM version emphasizing 20% productivity gain, cost savings, scale efficiency; End-user version: 'handles many tasks fast, uses memory well, rarely slows down'",
        "WRITE_04": "Feature Overview (2 sentences on OAuth), Acceptance Criteria (5 bullets: login, validation, creation, lockout, recovery), Technical Requirements (OAuth 2.0, token validation, account linking), Edge Cases (duplicate emails, provider revocation, simultaneous logins)",
        "WRITE_05": "300-350 word API documentation section with Getting Started, Authentication (token method), Making Requests (GET with pagination example), Rate Limiting (error response example). 3 valid code blocks included. Tone balances professionalism with accessibility.",
        "WRITE_06": "Three 150-word versions: Executive (strategic upgrade, 2-week timeline, minimal disruption, ROI); Manager (team impact, training requirement, limited workflows, transition support); Contributor (new features, 2-hr training, legacy data entry, help resources). Different emphasis, consistent facts.",
        "WRITE_07": "~300 word expansion covering: definition, B-tree mechanics/binary search, index types (B-tree for general, Hash for exact), composite indexes. Real example: 1000 rows from 1M instantly with index. Trade-offs: slower writes, storage cost. When-to-use guidance without padding.",
        "WRITE_08": "410-word email compressed to 200-word version retaining: April 15 date, 9AM-4PM time, main conference room, 3 agenda items, team preparation requirements, lunch/breaks, March 20 deadline. All essential information, no fluff.",
        "WRITE_09": "250-word business case: Problem (manual reconciliation 8 hrs/week, compliance risk, budget overruns), Solution (central dashboard with real-time tracking), Benefits (free 3 FTE=$300K annually, 90% time reduction), Timeline (8 weeks, Q2 live), ROI (3-4 months)",
        "WRITE_10": "800-word technical blog post: definition, advantages with code example (service communication), disadvantages (network latency, testing complexity), Netflix real-world use case, considerations, conclusion with next steps. 2-3 correct code snippets. Engaging professional tone.",
    }
    
    results = scorer.score_benchmark(example_responses)
    report = scorer.generate_report(results)
    print(report)
    
    # Save results
    script_dir = Path(__file__).parent
    results_path = script_dir / "evaluation" / "results.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print("\n✅ Results saved to evaluation/results.json")


def main():
    """Main entry point."""
    display_benchmark_info()
    
    # Count total tasks
    total_tasks, num_levels = count_tasks()
    print(f"📋 Total Tasks Available: {total_tasks} across {num_levels} categories\n")
    
    print("Options:")
    print("  1. Run with example responses (demo)")
    print("  2. View benchmark overview")
    print("  3. Load custom responses from JSON")
    print("  4. Fully automated scoring (scoring/gpt4_1_partial.json)")
    
    choice = input("\nSelect option (1-4): ").strip()

    if choice == "1":
        run_example_benchmark()
    elif choice == "2":
        tasks = load_all_tasks()
        print("\n📚 BENCHMARK OVERVIEW:\n")
        for level_name, level_tasks in tasks.items():
            print(f"{level_name}:")
            for task in level_tasks[:2]:  # Show first 2 tasks per level
                print(f"  • {task['task_id']}: {task['question'][:70]}...")
            if len(level_tasks) > 2:
                print(f"  ... and {len(level_tasks) - 2} more tasks\n")
    elif choice == "3":
        response_file = input("Enter JSON responses file path: ").strip()
        try:
            with open(response_file, 'r') as f:
                responses = json.load(f)
            run_custom_benchmark(responses)
        except Exception as e:
            print(f"❌ Error loading responses: {e}")
            sys.exit(1)
    elif choice == "4":
        response_file = "scoring/gpt4_1_partial.json"
        try:
            with open(response_file, 'r') as f:
                responses = json.load(f)
            run_custom_benchmark(responses)
        except FileNotFoundError:
            print(f"❌ Error: File '{response_file}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error loading responses: {e}")
            sys.exit(1)
    
    else:
        print("❌ Invalid option.")
        sys.exit(1)


if __name__ == "__main__":
    main()

