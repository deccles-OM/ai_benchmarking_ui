"""
Flask API routes for the AI Benchmarking application.
Handles benchmark execution, progress tracking, and result downloads.
"""
import os
import json
import sys
import threading
import time
import subprocess
from pathlib import Path
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, send_file
from dotenv import load_dotenv
from io import BytesIO
import zipfile

# Import from benchmark_analyst
from benchmark_analyst.core.ai_client import create_client
from benchmark_analyst.core.ai_benchmark import AIBenchmark
from benchmark_analyst.core.comparison import generate_answer_comparison_table
from app.utils import markdown_to_html, kill_stuck_processes

# Load environment variables
load_dotenv()

# Create Blueprint
bp = Blueprint('main', __name__, url_prefix='/api')

# Global state for progress tracking
benchmark_state = {
    'running': False,
    'progress': 0,
    'total': 0,
    'task_group_progress': 0,
    'task_group_total': 0,
    'current_message': '',
    'elapsed_time': 0,
    'start_time': None,
    'results_file': None,
    'error': None,
    'thread': None,  # Reference to the benchmark thread
    'should_stop': False  # Flag to signal the thread to stop
}


def progress_callback(current: int, total: int, message: str, task_group_progress: int = 0, task_group_total: int = 0):
    """Callback for benchmark progress updates."""
    benchmark_state['progress'] = current
    benchmark_state['total'] = total
    benchmark_state['task_group_progress'] = task_group_progress
    benchmark_state['task_group_total'] = task_group_total
    benchmark_state['current_message'] = message
    if benchmark_state['start_time']:
        benchmark_state['elapsed_time'] = time.time() - benchmark_state['start_time']


def run_benchmark_thread(provider: str, api_key: str, custom_endpoint: str, model: str, task_files: list, run_evaluation: bool):
    """Run benchmark in a separate thread to avoid blocking the UI."""
    try:
        print(f"[DEBUG] run_benchmark_thread started with run_evaluation={run_evaluation}")
        benchmark_state['running'] = True
        benchmark_state['start_time'] = time.time()
        benchmark_state['error'] = None
        
        # Clean up old results before starting new benchmark
        progress_callback(0, 1, "Cleaning up previous results...")
        
        # Check if stop was requested
        if benchmark_state['should_stop']:
            print("[DEBUG] Stop requested before cleanup - exiting")
            benchmark_state['running'] = False
            return
        
        try:
            results_dir = Path('response_models')
            if results_dir.exists():
                import shutil
                for file in results_dir.glob('*'):
                    if file.is_file():
                        file.unlink()
                        print(f"[DEBUG] Deleted: {file}")
        except Exception as e:
            print(f"[DEBUG] Warning: Could not clean up response_models: {e}")
        
        # Run benchmark
        benchmark = AIBenchmark()
        
        # Check if stop was requested before starting benchmark
        if benchmark_state['should_stop']:
            print("[DEBUG] Stop requested before benchmark - exiting")
            benchmark_state['running'] = False
            return
        
        results_file, metadata = benchmark.run_benchmark(
            provider=provider,
            api_key=api_key,
            custom_endpoint=custom_endpoint,
            model=model,
            task_files=task_files,
            progress_callback=progress_callback,
            should_stop_flag=benchmark_state  # Pass the state dict so benchmark can check should_stop
        )
        
        # Check if stop was requested after benchmark completed
        if benchmark_state['should_stop']:
            print("[DEBUG] Stop requested after benchmark - exiting early")
            benchmark_state['running'] = False
            return
        
        benchmark_state['results_file'] = results_file
        print(f"[DEBUG] Benchmark complete. results_file = {results_file}")
        
        # Generate answer comparison CSV
        progress_callback(benchmark_state['total'], benchmark_state['total'], "Generating answer comparison...")
        print(f"[DEBUG] Starting answer comparison generation for: {results_file}")
        try:
            generate_answer_comparison_table(results_file, evaluation_file=None, benchmark_dir="benchmark_analyst")
            progress_callback(benchmark_state['total'], benchmark_state['total'], "Answer comparison generated!")
            print(f"[DEBUG] Answer comparison generation completed for: {results_file}")
        except Exception as e:
            print(f"Warning: Could not generate answer comparison: {e}")
        
        # Run evaluation if requested
        if run_evaluation:
            progress_callback(benchmark_state['total'], benchmark_state['total'], "Running evaluation...")
            print(f"[DEBUG] Preparing to run evaluation subprocess for: {results_file}")
            try:
                # Add the project root to Python path when running evaluation subprocess
                env = os.environ.copy()
                env['PYTHONPATH'] = os.path.abspath(os.path.dirname(__file__) + '/..')
                # Ensure subprocess uses UTF-8 for stdout/stderr to avoid encoding errors on Windows
                env['PYTHONIOENCODING'] = 'utf-8'

                cmd = [
                    sys.executable,
                    "-m",
                    "benchmark_analyst.core.evaluation",
                    results_file,
                    "benchmark_analyst/data"
                ]
                print(f"[DEBUG] Evaluation command: {cmd}")
                print(f"[DEBUG] Evaluation env PYTHONPATH={env.get('PYTHONPATH')}")
                print(f"[DEBUG] Evaluation cwd={os.path.abspath(os.path.dirname(__file__) + '/..')}")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600,
                    env=env,
                    cwd=os.path.abspath(os.path.dirname(__file__) + '/..')
                )
                print(f"[DEBUG] Evaluation subprocess returncode: {result.returncode}")
                if result.stdout:
                    print(f"[DEBUG] Evaluation stdout:\n{result.stdout}")
                if result.stderr:
                    print(f"[DEBUG] Evaluation stderr:\n{result.stderr}")

                # Check for expected evaluation artifacts and log their presence
                try:
                    results_dir = Path('response_models')
                    base_filename = Path(results_file).stem
                    eval_file = results_dir / f"{base_filename}_evaluation.json"
                    md_file = results_dir / f"{base_filename}_RESULTS.md"
                    html_file = results_dir / f"{base_filename}_RESULTS.html"
                    print(f"[DEBUG] Expected eval JSON: {eval_file} exists={eval_file.exists()}")
                    print(f"[DEBUG] Expected MD file: {md_file} exists={md_file.exists()}")
                    print(f"[DEBUG] Expected HTML file: {html_file} exists={html_file.exists()}")
                except Exception as e:
                    print(f"[DEBUG] Error while checking for created files: {e}")

                # Regenerate answer comparison with evaluation scores
                progress_callback(benchmark_state['total'], benchmark_state['total'], "Updating answer comparison with scores...")
                try:
                    print(f"[DEBUG] Regenerating answer comparison with evaluation file: {eval_file}")
                    generate_answer_comparison_table(results_file, evaluation_file=str(eval_file), benchmark_dir="benchmark_analyst/data")
                    progress_callback(benchmark_state['total'], benchmark_state['total'], "Scores added to answer comparison!")
                    print(f"[DEBUG] Regenerated answer comparison with scores for: {results_file}")
                except Exception as e:
                    print(f"Warning: Could not regenerate answer comparison with scores: {e}")

                # Convert markdown report to HTML
                progress_callback(benchmark_state['total'], benchmark_state['total'], "Converting report to HTML...")
                try:
                    results_dir = Path('response_models')
                    base_filename = Path(results_file).stem
                    md_file = results_dir / f"{base_filename}_RESULTS.md"
                    print(f"[DEBUG] Looking for markdown file to convert: {md_file}")
                    if md_file.exists():
                        with open(md_file, 'r', encoding='utf-8') as f:
                            md_content = f.read()
                        html_content = markdown_to_html(md_content)
                        html_file = results_dir / f"{base_filename}_RESULTS.html"
                        with open(html_file, 'w', encoding='utf-8') as f:
                            f.write(html_content)
                        print(f"[DEBUG] HTML report generated: {html_file}")
                    else:
                        print(f"[DEBUG] Markdown file not found, skipping HTML conversion: {md_file}")
                except Exception as e:
                    print(f"Warning: Could not convert markdown to HTML: {e}")

                progress_callback(benchmark_state['total'], benchmark_state['total'], "Evaluation completed!")
            except Exception as e:
                benchmark_state['error'] = f"Evaluation error: {str(e)}"
                print(f"[DEBUG] Evaluation exception: {str(e)}")
                progress_callback(benchmark_state['total'], benchmark_state['total'], f"Evaluation error: {str(e)}")
    
    except Exception as e:
        benchmark_state['error'] = str(e)
        progress_callback(benchmark_state['progress'], benchmark_state['total'], f"Error: {str(e)}")
    
    finally:
        benchmark_state['running'] = False


@bp.route('/config')
def get_config():
    """Get initial configuration including API key from .env."""
    api_key = os.getenv('GEMINI_API_KEY', '')
    
    return jsonify({
        'api_key': api_key,
        'providers': ['gemini']  # Can be extended for more providers
    })


@bp.route('/test-connection', methods=['POST'])
def test_connection():
    """Test connection to AI provider and get available models."""
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'No JSON data provided',
                'models': []
            }), 400
        
        provider = data.get('provider', 'gemini')
        api_key = data.get('api_key', '')
        custom_endpoint = data.get('custom_endpoint', None)
        
        if not api_key:
            return jsonify({
                'success': False,
                'message': 'API key is required',
                'models': []
            }), 400
        
        print(f"[DEBUG] Testing connection for provider: {provider}")
        client = create_client(provider, api_key, custom_endpoint=custom_endpoint)
        print(f"[DEBUG] Client created successfully")
        result = client.test_connection()
        print(f"[DEBUG] Test connection result: {result}")
        return jsonify(result)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[ERROR] Test connection failed: {error_trace}")
        return jsonify({
            'success': False,
            'message': f'Connection test failed: {str(e)}',
            'models': []
        }), 500


@bp.route('/tasks')
def get_tasks():
    """Get list of available benchmark tasks."""
    try:
        benchmark = AIBenchmark()
        tasks = benchmark.scan_tasks()
        return jsonify({
            'success': True,
            'tasks': [{'filename': t[0], 'name': t[1]} for t in tasks]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


@bp.route('/run-benchmark', methods=['POST'])
def run_benchmark():
    """Start benchmark execution."""
    if benchmark_state['running']:
        return jsonify({
            'success': False,
            'message': 'Benchmark is already running'
        }), 400
    
    data = request.json
    provider = data.get('provider', 'gemini')
    api_key = data.get('api_key', '')
    custom_endpoint = data.get('custom_endpoint', None)
    model = data.get('model', '')
    task_files = data.get('task_files', [])
    run_evaluation = data.get('run_evaluation', True)
    
    print(f"[DEBUG] run_benchmark received: provider={provider}, model={model}, task_files={task_files}, run_evaluation={run_evaluation}")
    
    if not api_key or not model or not task_files:
        return jsonify({
            'success': False,
            'message': 'API key, model, and at least one task are required'
        }), 400
    
    # Reset state
    benchmark_state['progress'] = 0
    benchmark_state['total'] = 0
    benchmark_state['current_message'] = 'Starting benchmark...'
    benchmark_state['error'] = None
    benchmark_state['results_file'] = None
    benchmark_state['should_stop'] = False  # Reset stop flag
    
    # Start benchmark in background thread
    thread = threading.Thread(
        target=run_benchmark_thread,
        args=(provider, api_key, custom_endpoint, model, task_files, run_evaluation),
        daemon=True
    )
    thread.start()
    benchmark_state['thread'] = thread  # Store thread reference
    
    return jsonify({
        'success': True,
        'message': 'Benchmark started'
    })


@bp.route('/stop-benchmark', methods=['POST'])
def stop_benchmark():
    """Stop the currently running benchmark."""
    if benchmark_state['running']:
        benchmark_state['should_stop'] = True
        print("[DEBUG] Stop benchmark requested - setting should_stop flag")
        return jsonify({
            'success': True,
            'message': 'Benchmark stop requested'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'No benchmark currently running'
        })


@bp.route('/shutdown', methods=['POST'])
def shutdown_server():
    """Shutdown the Flask server."""
    print("[INFO] Shutdown requested - gracefully closing server...")
    
    def do_shutdown():
        time.sleep(1)  # Give the response time to be sent
        import os
        os._exit(0)
    
    # Start shutdown in a separate thread so the response can be sent first
    threading.Thread(target=do_shutdown, daemon=True).start()
    
    return jsonify({
        'success': True,
        'message': 'Server shutting down...'
    })


@bp.route('/benchmark-status')
def benchmark_status():
    """Get current benchmark status."""
    return jsonify({
        'running': benchmark_state['running'],
        'progress': benchmark_state['progress'],
        'total': benchmark_state['total'],
        'task_group_progress': benchmark_state['task_group_progress'],
        'task_group_total': benchmark_state['task_group_total'],
        'message': benchmark_state['current_message'],
        'elapsed_time': int(benchmark_state['elapsed_time']),
        'error': benchmark_state['error'],
        'results_file': benchmark_state['results_file']
    })


@bp.route('/download-results')
def download_results():
    """Download benchmark results as ZIP."""
    results_file = benchmark_state['results_file']
    
    print(f"\n[DEBUG] ========== DOWNLOAD RESULTS ==========")
    print(f"[DEBUG] results_file = {results_file}")
    print(f"[DEBUG] results_file type = {type(results_file)}")
    print(f"[DEBUG] results_file exists? {Path(results_file).exists() if results_file else 'N/A'}")
    print(f"[DEBUG] benchmark_state keys = {benchmark_state.keys()}")
    
    if not results_file:
        print(f"[DEBUG] No results_file in benchmark_state")
        return jsonify({
            'success': False,
            'message': 'No results available'
        }), 404
    
    if not Path(results_file).exists():
        print(f"[DEBUG] Results file does not exist at path: {results_file}")
        return jsonify({
            'success': False,
            'message': f'Results file not found: {results_file}'
        }), 404
    
    try:
        results_dir = Path('response_models')
        
        # Create ZIP file in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Get the base filename from results_file
            if results_file:
                base_filename = Path(results_file).stem  # e.g., "gemini-2.5-flash_20260408_task_groups"
                print(f"[DEBUG] base_filename = {base_filename}")
                
                # Find and add ALL files matching this base filename
                if results_dir.exists():
                    for file in results_dir.glob(f"{base_filename}*"):
                        if file.is_file():
                            print(f"[DEBUG] Adding file to ZIP: {file}")
                            zip_file.write(file, arcname=file.name)
                        else:
                            print(f"[DEBUG] Skipping (not a file): {file}")
                else:
                    print(f"[DEBUG] results_dir does not exist: {results_dir}")
            else:
                print(f"[DEBUG] results_file is empty or None")
        
        zip_buffer.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_results_{timestamp}.zip"
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error creating ZIP: {str(e)}'
        }), 400
