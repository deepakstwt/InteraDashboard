#!/bin/bash

# Vehicle Registration Dashboard Setup Script
# This script sets up the entire project environment

echo "🏗️  Setting up Vehicle Registration Investor Dashboard..."
echo "========================================================"

# Change to project directory
cd "$(dirname "$0")"

# Check Python installation
echo "🐍 Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Found Python $python_version"

# Create virtual environment
echo "🔧 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install core dependencies
echo "📦 Installing core dependencies..."
pip install pandas numpy streamlit plotly

# Install additional dependencies
echo "📦 Installing additional dependencies..."
pip install beautifulsoup4 selenium webdriver-manager loguru watchdog

# Install remaining requirements
echo "📦 Installing remaining requirements..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating project directories..."
mkdir -p data/raw data/processed data/exports logs

# Test installation
echo "🧪 Testing installation..."
python -c "
import streamlit
import pandas
import numpy
import plotly
import selenium
import bs4
import loguru
print('✅ All packages imported successfully!')
"

echo "========================================================"
echo "🎉 Setup completed successfully!"
echo ""
echo "🚀 To start the dashboard, run:"
echo "   ./run_dashboard.sh"
echo ""
echo "🌐 Or manually:"
echo "   source venv/bin/activate"
echo "   streamlit run src/dashboard/main.py"
echo ""
echo "📖 The dashboard will be available at: http://localhost:8501"
echo "========================================================"
