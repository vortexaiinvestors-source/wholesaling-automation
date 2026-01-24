#!/bin/bash
# Real Estate Wholesaling System Setup

echo "================================"
echo "Real Estate Wholesaling System"
echo "Setup Script"
echo "================================"

# Create directories
mkdir -p logs database config scrapers

# Create .env from template
if [ ! -f .env ]; then
    cp .env.template .env
    echo "✓ Created .env file (edit with your API keys)"
else
    echo "✓ .env file already exists"
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "================================"
echo "Setup Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Edit .env with your API keys"
echo "2. Run: python scrapers/master_scraper_orchestrator.py"
echo ""