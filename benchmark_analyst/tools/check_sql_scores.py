import json

with open('ford_data_analyst_benchmark/evaluation/results.json') as f:
    data = json.load(f)
    print("\n=== SQL TASK SCORES (Updated) ===\n")
    for task in data['task_results']:
        if task['task_id'] in ['SQL_01', 'SQL_02', 'SQL_03', 'SQL_04']:
            score = task['score']
            max_pts = task['max_points']
            pct = (score/max_pts*100) if max_pts else 0
            print(f"{task['task_id']}: {score:.1f}/{max_pts} ({pct:.0f}%)")
    
    print("\n=== OVERALL SUMMARY ===\n")
    total = data['total_score']
    max_total = data['max_score']
    pct = (total/max_total*100) if max_total else 0
    print(f"Total Score: {total:.1f}/{max_total} ({pct:.1f}%)")
