#!/bin/bash

# Setup script for Zoom RTMS LangChain Sample
# This script creates a clean virtual environment with compatible dependencies

echo "Setting up Zoom RTMS LangChain Sample environment..."

# Check if Python 3.11+ is available
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3.13 &> /dev/null; then
    PYTHON_CMD="python3.13"
else
    echo "Error: Python 3.11+ is required but not found"
    echo "Please install Python 3.11+ or use pyenv to manage Python versions"
    exit 1
fi

echo "Using Python: $($PYTHON_CMD --version)"

# Create virtual environment
echo "Creating virtual environment..."
$PYTHON_CMD -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Setup complete! To activate the environment, run:"
echo "source venv/bin/activate"
echo ""
echo "Then you can run the application with:"
echo "python print_transcripts.py" 