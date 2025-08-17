#!/bin/bash

# Run database migrations and create tables
python3 -c "from src.main import app, db; with app.app_context(): db.create_all()"

# Create default categories if they don't exist
python3 -c "from src.main import app, db; from src.models.item import Category; with app.app_context(): default_categories = [{'name': 'Women', 'sort_order': 1}, {'name': 'Men', 'sort_order': 2}, {'name': 'Kids', 'sort_order': 3}, {'name': 'Home', 'sort_order': 4}, {'name': 'Electronics', 'sort_order': 5}, {'name': 'Sports', 'sort_order': 6}]; for cat_data in default_categories: if not Category.query.filter_by(name=cat_data['name']).first(): category = Category(name=cat_data['name'], sort_order=cat_data['sort_order']); db.session.add(category); db.session.commit()"

# Create default UAE shipping zones
python3 -c "from src.main import app, db; from src.models.user import UAEShippingZone; with app.app_context(): default_zones = [{'emirate': 'Dubai', 'city': 'Dubai', 'area': 'Downtown', 'delivery_zone': 'Zone 1', 'shipping_cost_zone1': 15.00}, {'emirate': 'Dubai', 'city': 'Dubai', 'area': 'Marina', 'delivery_zone': 'Zone 1', 'shipping_cost_zone1': 15.00}, {'emirate': 'Dubai', 'city': 'Dubai', 'area': 'JLT', 'delivery_zone': 'Zone 1', 'shipping_cost_zone1': 15.00}, {'emirate': 'Dubai', 'city': 'Dubai', 'area': 'Business Bay', 'delivery_zone': 'Zone 1', 'shipping_cost_zone1': 15.00}, {'emirate': 'Dubai', 'city': 'Dubai', 'area': 'DIFC', 'delivery_zone': 'Zone 1', 'shipping_cost_zone1': 15.00}, {'emirate': 'Abu Dhabi', 'city': 'Abu Dhabi', 'area': 'Corniche', 'delivery_zone': 'Zone 2', 'shipping_cost_zone2': 20.00}, {'emirate': 'Abu Dhabi', 'city': 'Abu Dhabi', 'area': 'Khalifa City', 'delivery_zone': 'Zone 2', 'shipping_cost_zone2': 20.00}, {'emirate': 'Sharjah', 'city': 'Sharjah', 'area': 'City Center', 'delivery_zone': 'Zone 2', 'shipping_cost_zone2': 20.00}, {'emirate': 'Ajman', 'city': 'Ajman', 'area': 'City Center', 'delivery_zone': 'Zone 3', 'shipping_cost_zone3': 25.00}, {'emirate': 'Ras Al Khaimah', 'city': 'Ras Al Khaimah', 'area': 'City Center', 'delivery_zone': 'Zone 3', 'shipping_cost_zone3': 25.00}, {'emirate': 'Fujairah', 'city': 'Fujairah', 'area': 'City Center', 'delivery_zone': 'Zone 3', 'shipping_cost_zone3': 25.00}, {'emirate': 'Umm Al Quwain', 'city': 'Umm Al Quwain', 'area': 'City Center', 'delivery_zone': 'Zone 3', 'shipping_cost_zone3': 25.00}]; for zone_data in default_zones: if not UAEShippingZone.query.filter_by(emirate=zone_data['emirate'], city=zone_data['city'], area=zone_data['area']).first(): zone = UAEShippingZone(**zone_data); db.session.add(zone); db.session.commit()"

# Start Gunicorn
gunicorn src.main:app --bind 0.0.0.0:$PORT --workers 4


