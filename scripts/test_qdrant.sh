#!/bin/bash

# --- RAG End-to-End Test Runner ---
# This script executes the Python RAG diagnostic test (test_rag_e2e.py)
# by first navigating to the 'backend' directory. This fixes the 
# 'ModuleNotFoundError: No module named 'config'' by allowing relative imports 
# to resolve correctly within the backend package structure.

# Ensure the script stops on the first error
set -e

# Get the directory where this script is located (scripts/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
BACKEND_DIR="$PROJECT_ROOT/backend"
PYTHON_SCRIPT="$SCRIPT_DIR/test_e2e_rag.py"

echo "Navigating to: $BACKEND_DIR to resolve module imports..."

# Change the current working directory to the backend/ folder
cd "$BACKEND_DIR"

echo "Executing Python RAG E2E Test..."

# Execute the test script. Note: We still pass the full path to the Python script
# as running the script directly from the backend folder simplifies the imports 
# *within* the Python code.
python "$PYTHON_SCRIPT"

# The return code of the Python script determines the exit status of the bash script
EXIT_CODE=$?

# Navigate back to the original directory (optional, but good practice)
cd "$OLDPWD"

if [ $EXIT_CODE -eq 0 ]; then
    echo "======================================================="
    echo "✅ RAG E2E Test completed successfully!"
else
    echo "======================================================="
    echo "❌ RAG E2E Test failed during execution."
fi

exit $EXIT_CODE
