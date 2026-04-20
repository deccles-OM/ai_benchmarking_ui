"""
Benchmark Analyst - AI model evaluation and benchmarking suite.
"""
from benchmark_analyst.core.ai_benchmark import AIBenchmark
from benchmark_analyst.core.ai_client import create_client, AIClient
from benchmark_analyst.STANDARD_SCHEMA import STANDARD_TASK_SCHEMA

__version__ = "1.0.0"

__all__ = [
    'AIBenchmark',
    'create_client',
    'AIClient',
    'STANDARD_TASK_SCHEMA',
]

__version__ = '1.0.0'
__all__ = ['AIBenchmark', 'create_client']
