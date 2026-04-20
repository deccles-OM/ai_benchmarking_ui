# AI Benchmarking System (v2) - Web UI

A web-based benchmarking system for testing and evaluating AI model responses across various tasks. Built with Flask, supporting multiple AI providers (currently Gemini, extensible for future providers).

## Features

- **Web UI Interface**: Modern Flask-based web application for easy benchmark management
- **Multi-Provider Support**: Extensible architecture supporting multiple AI providers (currently Gemini)
- **Provider-Agnostic Code**: `ai_client.py` and `ai_benchmark.py` provide abstraction layer for adding new providers
- **Real-time Progress Tracking**: Live progress updates during benchmark execution
- **Automatic API Key Management**: Loads API key from `.env` file on startup
- **Task Selection**: Flexible checkbox selection of which benchmark tasks to run
- **Evaluation Integration**: Optional automatic evaluation after benchmark completion
- **Results Download**: Download all results as a ZIP file with standard formats (JSON, CSV, MD)

## Architecture

### Core Components

1. **ai_client.py**: Provider-agnostic AI client abstraction
   - `AIClient` class supporting multiple providers
   - Factory function `create_client(provider, api_key)`
   - Currently implements Gemini support

2. **ai_benchmark.py**: Benchmark execution engine
   - `AIBenchmark` class for managing benchmark workflow
   - Task scanning and question processing
   - Progress callback support for real-time updates
   - Response extraction and storage

3. **app.py**: Flask web application
   - REST API endpoints for UI communication
   - Background benchmark execution with threading
   - Results management and download

4. **Frontend** (HTML/CSS/JS)
   - `templates/index.html`: Main UI template
   - `static/style.css`: Responsive styling
   - `static/script.js`: Interactive UI logic

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create or update `.env` file with your API key:

```properties
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Run the Application

```bash
python run.py
```

The web UI will be available at: `http://localhost:5000`

## Usage

### Provider & Credentials Section

1. **Select Provider**: Currently only "Gemini" is available (dropdown is extensible)
2. **Enter API Key**:
   - Manually enter your API key, or
   - It will auto-fill from `.env` file if present
3. **Test Connection & Detect Versions**:
   - Validates the API key
   - Tests connection to the provider
   - Retrieves available model versions

### Model Selection

- After successful connection, radio buttons appear for each available model
- Only one model can be selected at a time
- First model is selected by default

### Task Selection

- All available benchmark tasks appear as checkboxes
- **Select All** (default checked): Enables/disables all tasks
- **Select None**: Appears only when some (but not all) tasks are selected
- Tasks can be individually toggled

### Run Benchmark

1. **Evaluation Checkbox**: Checked by default to run evaluation after benchmark
2. **Run Benchmark Button**: Starts the benchmark execution
   - Disabled until a model and at least one task are selected
3. **Progress Display**:
   - Shows current question number and total questions
   - Displays elapsed time
   - Real-time progress bar
4. **Results Display**:
   - Success message upon completion
   - **Download Results**: ZIP file containing:
     - JSON file with raw benchmark results
     - CSV file with evaluation data (if evaluation ran)
     - Markdown file with detailed results (if evaluation ran)

## File Structure

```text
ai_benchmarking/
├── app.py                           # Flask application
├── ai_client.py                     # Provider abstraction layer
├── ai_benchmark.py                  # Benchmark execution engine
├── requirements.txt                 # Python dependencies
├── .env                            # Environment variables
├── templates/
│   └── index.html                  # Main UI template
├── static/
│   ├── style.css                   # UI styling
│   └── script.js                   # UI interactivity
├── ford_data_analyst_benchmark/     # Benchmark data
│   ├── tasks/                      # Task JSON files
│   ├── datasets/                   # CSV datasets
│   ├── documents/                  # Reference documents
│   ├── evaluation/                 # Evaluation modules
│   └── scoring/                    # Scoring modules
└── response_models/                # Output directory for results
```

## API Endpoints

### GET /api/config

Returns initial configuration including auto-filled API key.

### POST /api/test-connection

Tests connection and detects available models.

```json
{
  "provider": "gemini",
  "api_key": "your_key"
}
```

### GET /api/tasks

Returns list of available benchmark tasks.

### POST /api/run-benchmark

Starts benchmark execution.

```json
{
  "provider": "gemini",
  "api_key": "your_key",
  "model": "gemini-3-pro-preview",
  "task_files": ["task_group1_basic.json"],
  "run_evaluation": true
}
```

### GET /api/benchmark-status

Returns current benchmark execution status with progress.

### GET /api/download-results

Downloads results as a ZIP file.

## Adding a New Provider

To add support for a new AI provider (e.g., OpenAI, Claude):

1. **Update ai_client.py**:

```python
class AIClient:
    def __init__(self, provider: str, api_key: str):
        # ... existing code ...
        elif self.provider == 'openai':
            self.client = openai.OpenAI(api_key=api_key)

    def test_connection(self):
        # ... existing code ...
        elif self.provider == 'openai':
            # Implement OpenAI connection test

    def generate_content(self, model: str, contents: str):
        # ... existing code ...
        elif self.provider == 'openai':
            # Implement OpenAI content generation
```

1. **Update app.py**:

```python
@app.route('/api/config')
def get_config():
    # ... existing code ...
    return jsonify({
        'api_key': api_key,
        'providers': ['gemini', 'openai']  # Add new provider
    })
```

1. **Update .env**:

```properties
OPENAI_API_KEY=your_openai_key_here
```

1. **Update requirements.txt**:

```text
openai>=1.0.0  # Add new provider dependency
```

## Troubleshooting

### API Key Issues

- Ensure `.env` file exists in the project root
- Verify `GEMINI_API_KEY` (or other provider key) is set correctly
- API key will not auto-fill if file doesn't exist or key is missing

### Connection Test Fails

- Verify API key is correct and active
- Check internet connection
- Ensure provider API is accessible

### Tasks Not Loading

- Verify `ford_data_analyst_benchmark/tasks/` directory exists
- Ensure task JSON files are properly formatted
- Check file permissions

### Benchmark Hangs

- Check benchmark logs in browser console
- Verify API rate limits aren't exceeded
- Try with fewer tasks to isolate issue

## Development Notes

### Progress Callback

The benchmark system uses a progress callback for real-time updates:

```python
def progress_callback(current: int, total: int, message: str):
    # Update UI with progress
```

### Thread Safety

Benchmark execution runs in a separate thread to keep the UI responsive. State is managed through the `benchmark_state` dictionary.

### Result Format

Results are saved in JSON format with the following structure:

```json
{
  "api": "model_name",
  "task_file": "filename",
  "question": "question_text",
  "final_answer": "extracted_answer",
  "prompt": ["prompt", "lines"],
  "response": ["response", "lines"],
  "performance": {
    "response_time_seconds": 1.23,
    "input_tokens": 100,
    "output_tokens": 50,
    "total_tokens": 150
  }
}
```

## Future Enhancements

- [ ] Additional provider support (OpenAI, Claude, etc.)
- [ ] Custom task creation UI
- [ ] Detailed evaluation visualizations
- [ ] Batch comparison across multiple models
- [ ] Historical result tracking
- [ ] Advanced filtering and search
- [ ] User authentication and project management

## License

Internal Use - Ford

## Support

For issues or questions, please refer to the project documentation or contact the development team.
