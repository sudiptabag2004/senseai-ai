#!/bin/bash
set -e

# Activate virtual environment if needed
# source venv/bin/activate

# Run API tests with coverage
python -m pytest tests/api/ -v --cov=src --cov-report=term --cov-report=html:coverage_html

echo "API tests completed successfully. Coverage report is available in the coverage_html directory." 