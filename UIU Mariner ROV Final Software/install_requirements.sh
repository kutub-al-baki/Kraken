#!/bin/bash
# =================================================================
# UIU MARINER ROV - Local Environment Setup
# =================================================================
# This script installs all necessary packages for the Ground Station.
# Works on Linux, macOS, and Windows (via Git Bash/WSL).

echo "🚀 Starting UIU Mariner ROV Software Installation..."
echo "---------------------------------------------------"

# 1. Python Backend Dependencies
echo "🐍 Installing Python dependencies..."
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
else
    echo "❌ Error: Python not found. Please install Python 3.8+."
    exit 1
fi

$PYTHON_BIN -m pip install --upgrade pip
$PYTHON_BIN -m pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Python dependencies installed successfully."
else
    echo "❌ Error: Failed to install Python dependencies."
    exit 1
fi

echo "---------------------------------------------------"

# 2. Frontend Dependencies
echo "⚛️  Installing Frontend dependencies (Node.js)..."
if [ -d "frontend" ]; then
    cd frontend
    if command -v npm &>/dev/null; then
        npm install
        if [ $? -eq 0 ]; then
            echo "✅ Frontend dependencies installed successfully."
        else
            echo "❌ Error: npm install failed."
            exit 1
        fi
    else
        echo "⚠️  Warning: npm not found. Skipping frontend installation."
        echo "   Please install Node.js and run 'npm install' inside the 'frontend' folder."
    fi
    cd ..
else
    echo "⚠️  Warning: 'frontend' directory not found. Skipping."
fi

echo "---------------------------------------------------"
echo "🎉 Installation Complete!"
echo "💡 To start the software, run: python launch_mariner.py"
echo "==================================================="
