#!/bin/bash

set -e # Exit immediately if a command exits with a non-zero status.

echo "=== Starting application initialization ==="

# Test database connection first
echo "Testing database connection..."
python3 -c "
import os
import sys
from sqlalchemy import create_engine, text

try:
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print('ERROR: DATABASE_URL environment variable not set')
        sys.exit(1)
    
    print(f'Database URL: {database_url[:50]}...')
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('Database connection successful!')
        
except Exception as e:
    print(f'Database connection failed: {str(e)}')
    sys.exit(1)
"

# Create database tables
echo "Creating database tables..."
python3 -c "
import sys
try:
    from src.main import app, db
    with app.app_context():
        db.create_all()
        print('Database tables created successfully!')
except Exception as e:
    print(f'Failed to create database tables: {str(e)}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

# Create default categories
echo "Creating default categories..."
python3 -c "
import sys
try:
    from src.main import app, db
    from src.models.item import Category
    
    with app.app_context():
        default_categories = [
            {'name': 'Women', 'sort_order': 1},
            {'name': 'Men', 'sort_order': 2},
            {'name': 'Kids', 'sort_order': 3},
            {'name': 'Home', 'sort_order': 4},
            {'name': 'Electronics', 'sort_order': 5},
            {'name': 'Sports', 'sort_order': 6}
        ]
        
        for cat_data in default_categories:
            if not Category.query.filter_by(name=cat_data['name']).first():
                category = Category(name=cat_data['name'], sort_order=cat_data['sort_order'])
                db.session.add(category)
        
        db.session.commit()
        print('Default categories created successfully!')
        
except Exception as e:
    print(f'Failed to create default categories: {str(e)}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

echo "=== Application initialization complete ==="

# Start Gunicorn
echo "Starting Gunicorn server..."
exec gunicorn src.main:app --bind 0.0.0.0:$PORT --workers 4

