# AI Benchmarking System

A comprehensive web-based benchmarking platform for evaluating AI model performance using the Gemini API.

## Quick Start

### Prerequisites

- Python 3.11+
- Virtual environment (included)
- Gemini API key from [Google AI Studio](https://aistudio.google.com)

### Installation

1. Activate virtual environment

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

1. Install dependencies

```bash
pip install -r requirements.txt
```

1. Configure environment

Create .env file:

```properties
SECRET_KEY=dev-secret-key
FLASK_ENV=development
GEMINI_API_KEY=your_api_key_here
```

### Running the App

```bash
python run.py
```

Opens at `http://127.0.0.1:5000`

## Features

- Benchmark execution with models and tasks
- Real-time progress tracking
- Task selection with checkboxes
- Model selection with radio buttons
- Results download as ZIP
- Provider-agnostic architecture

## Project Structure

```text
ai_benchmarking_ui/
├── README.md                  # This file
├── run.py                     # Entry point
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables
|
├── app/                       # Flask web application
│   ├── __init__.py            # Factory + app setup
│   ├── routes.py              # API routes (blueprint)
│   ├── utils.py               # Helper functions
│   └── templates/             # HTML templates
|
├── benchmark_analyst/         # Benchmarking engine
│   ├── core/
│   │   ├── ai_client.py       # Provider abstraction
│   │   ├── ai_benchmark.py    # Benchmark runner
│   │   ├── evaluation.py      # Scoring engine
│   │   └── comparison.py      # Response comparison utilities
│   ├── data/
│   │   ├── datasets/          # CSV datasets
│   │   ├── documents/         # Reference documents
│   │   └── tasks/             # Task group JSONs (27+)
│   ├── evaluation/            # Evaluation modules
│   ├── scoring/               # Results storage
│   └── tools/                 # Utility scripts
|
├── docs/                      # Reference documentation
│   ├── QUICKSTART.md
│   ├── SETUP.md
│   └── IMPLEMENTATION.md
|
├── static/                    # Frontend assets (CSS/JS)
│   ├── style.css
│   └── script.js
|
├── templates/                 # HTML templates served by Flask
│   └── index.html
|
└── response_models/           # Results directory (auto-created)
```

## API Endpoints

| Endpoint | Method | Purpose |
| -------- | ------ | ------- |
| / | GET | Main UI |
| /api/config | GET | Configuration |
| /api/test-connection | POST | Test API |
| /api/tasks | GET | List tasks |
| /api/run-benchmark | POST | Start benchmark |
| /api/benchmark-status | GET | Get progress |
| /api/download-results | GET | Download ZIP |

## Configuration

Create .env file in root directory:

```properties
SECRET_KEY=dev-secret-key
FLASK_ENV=development
GEMINI_API_KEY=your_api_key_here
```

## Documentation

- QUICKSTART.md - Quick reference
- SETUP.md - Complete documentation
- IMPLEMENTATION.md - Technical details

## Troubleshooting

API Connection Fails: Verify GEMINI_API_KEY in .env

Tasks Not Loading: Check benchmark_analyst/data/tasks/ directory exists

Benchmark Timeout: Try fewer tasks or check internet

## Requirements

- Python 3.11+
- Flask 3.1.3
- google-genai 1.70.0
- python-dotenv 1.0.0

## License

Internal Use - Ford

---

Version: 2.0 (Web UI)
Status: Production Ready
Updated: April 2026
