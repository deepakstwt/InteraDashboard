#!/bin/bash

# Vehicle Registration Dashboard Launcher Script
# This script activates the virtual environment and starts the dashboard

echo "🚀 Starting Vehicle Registration Investor Dashboard..."
echo "======================================================="

# Change to project directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if required packages are installed
echo "🔍 Checking dependencies..."
python -c "import streamlit, pandas, numpy, plotly" 2>/dev/null || {
    echo "❌ Missing dependencies. Installing..."
    pip install -r requirements.txt
}

# Start the dashboard
echo "📊 Launching dashboard at http://localhost:8501"
echo "📝 Press Ctrl+C to stop the dashboard"
echo "======================================================="

streamlit run src/dashboard/main.py --server.port 8501 --server.address localhost

echo "👋 Dashboard stopped. Thank you for using our service!"
