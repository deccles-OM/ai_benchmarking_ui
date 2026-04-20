# Quick Start Guide - AI Benchmarking Web UI

## Installation

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up environment variables

Create or update `.env` file in the project root:

```properties
SECRET_KEY=dev-secret-key-change-in-production
FLASK_ENV=development
GEMINI_API_KEY=your_gemini_api_key_here
```

## Running the Application

### Start the Flask server

```bash
python run.py
```

The application will be available at `http://localhost:5000`

### Default settings

- **Provider**: Gemini (configured)
- **API Key**: Auto-filled from `.env` file
- **Evaluation**: Enabled by default
- **Task Selection**: All tasks selected by default

## Workflow

1. **Test Connection**
   - Click "Test Connection & Detect Versions"
   - Displays available models on success
   - Shows error message if connection fails

2. **Select Model** (after successful connection)
   - Radio buttons appear for each available model
   - Select one model to use for benchmarking

3. **Select Tasks**
   - Choose which task groups to run
   - "Select All" is checked by default
   - "Select None" appears only when some (not all) tasks are selected

4. **Configure Evaluation**
   - "Run Evaluation" is checked by default
   - Uncheck to skip evaluation after benchmark

5. **Run Benchmark**
   - Click "Run Benchmark" button
   - Watch real-time progress: "X of Y questions"
   - Monitor elapsed time
   - Progress bar shows completion percentage

6. **Download Results**
   - Click "Download Results" after completion
   - ZIP file contains:
     - `[model]_[date]_task_groups.json` - Raw responses
     - `[model]_[date]_task_groups_evaluation.csv` - Evaluation scores (if run)
     - `[model]_[date]_task_groups_RESULTS.md` - Detailed results (if run)

## Key Features

### Provider Agnosticity

- Currently supports: **Gemini**
- Code architecture allows easy addition of new providers
- See `SETUP.md` "Adding a New Provider" section

### Real-time Progress

- Live updates every 500ms
- Shows current question and total questions
- Displays elapsed time in HH:MM:SS format

### Automatic Evaluation

- Optional integration with `evaluate_benchmark_results.py`
- Runs automatically after benchmark if enabled
- Results automatically added to download package

### Results Management

- All results saved as ZIP file
- Maintains original file format (JSON, CSV, MD)
- Download available immediately after completion

## Troubleshooting

### Connection fails with "API key is required"

- Check `.env` file exists in project root
- Verify `GEMINI_API_KEY` is set correctly
- Manually enter API key in UI if needed

### Tasks don't appear

- Verify `ford_data_analyst_benchmark/tasks/` directory exists
- Check task JSON files are valid JSON format
- Ensure file permissions allow reading

### Benchmark times out

- Check internet connection
- Verify API rate limits haven't been exceeded
- Try with fewer tasks to isolate issue

### Download fails

- Ensure benchmark completed successfully
- Check results file exists in `response_models/` directory
- Verify disk space available for ZIP creation

## File Structure

```text
ai_benchmarking/
├── app.py                      # Flask application
├── ai_client.py               # AI provider abstraction
├── ai_benchmark.py            # Benchmark execution engine
├── gemini_benchmark.py        # Backward compatible wrapper
├── gemini_client.py           # Backward compatible wrapper
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables
├── SETUP.md                   # Full documentation
├── QUICKSTART.md              # This file
├── templates/
│   └── index.html            # Main UI template
├── static/
│   ├── style.css             # UI styling
│   └── script.js             # UI interactivity
├── ford_data_analyst_benchmark/
│   ├── tasks/                # Task JSON files
│   ├── datasets/             # CSV data files
│   ├── documents/            # Reference documents
│   └── evaluation/           # Evaluation modules
└── response_models/          # Results directory (auto-created)
```

## API Endpoints (for reference)

| Endpoint | Method | Purpose |
| -------- | ------ | ------- |
| `/` | GET | Render main UI |
| `/api/config` | GET | Get initial config + auto-fill API key |
| `/api/test-connection` | POST | Test API and get available models |
| `/api/tasks` | GET | List available benchmark tasks |
| `/api/run-benchmark` | POST | Start benchmark execution |
| `/api/benchmark-status` | GET | Get current progress status |
| `/api/download-results` | GET | Download results as ZIP |

## Support

For detailed information, see:

- `SETUP.md` - Complete documentation and architecture
- `ai_benchmark.py` - Benchmark execution logic
- `ai_client.py` - Provider integration logic
- `app.py` - Flask application and API endpoints

---

**Version**: 2.0 (Web UI)  
**Last Updated**: April 2026
