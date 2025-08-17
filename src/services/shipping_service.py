import requests
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

class ShippingService:
    """Service for handling shipping and logistics"""
    
    def __init__(self):
        self.providers = {
            'aramex': {
                'name': 'Aramex',
                'api_url': 'https://ws.aramex.net/ShippingAPI.V2/',
                'username': 'your_aramex_username',
                'password': 'your_aramex_password',
                'account_number': 'your_account_number',
                'supports_cod': True,
                'supports_tracking': True
            },
            'emirates_post': {
                'name': 'Emirates Post',
                'api_url': 'https://api.emiratespost.ae/',
                'api_key': 'your_emirates_post_api_key',
                'supports_cod': True,
                'supports_tracking': True
            },
            'fedex': {
                'name': 'FedEx',
                'api_url': 'https://apis.fedex.com/',
                'api_key': 'your_fedex_api_key',
                'supports_cod': False,
                'supports_tracking': True
            }
        }
        
        # UAE Emirates and their shipping zones
        self.uae_zones = {
            'Dubai': {'zone': 1, 'same_day': True},
            'Abu Dhabi': {'zone': 1, 'same_day': True},
            'Sharjah': {'zone': 1, 'same_day': True},
            'Ajman': {'zone': 2, 'same_day': False},
            'Ras Al Khaimah': {'zone': 2, 'same_day': False},
            'Fujairah': {'zone': 2, 'same_day': False},
            'Umm Al Quwain': {'zone': 2, 'same_day': False}
        }
    
    def calculate_shipping_cost(self, from_emirate: str, to_emirate: str, 
                              weight: float, dimensions: Dict = None, 
                              service_type: str = 'standard') -> Dict[str, Any]:
        """Calculate shipping cost between emirates"""
        try:
            from_zone = self.uae_zones.get(from_emirate, {'zone': 2})['zone']
            to_zone = self.uae_zones.get(to_emirate, {'zone': 2})['zone']
            
            # Base rates (in AED)
            base_rates = {
                'same_day': {'zone_1_to_1': 25, 'zone_1_to_2': 35, 'zone_2_to_2': 30},
                'express': {'zone_1_to_1': 15, 'zone_1_to_2': 20, 'zone_2_to_2': 18},
                'standard': {'zone_1_to_1': 10, 'zone_1_to_2': 15, 'zone_2_to_2': 12}
            }
            
            # Determine zone combination
            if from_zone == 1 and to_zone == 1:
                zone_key = 'zone_1_to_1'
            elif from_zone == 1 and to_zone == 2:
                zone_key = 'zone_1_to_2'
            else:
                zone_key = 'zone_2_to_2'
            
            base_cost = base_rates[service_type][zone_key]
            
            # Weight-based pricing (additional cost for weight > 1kg)
            weight_cost = 0
            if weight > 1.0:
                weight_cost = (weight - 1.0) * 3  # 3 AED per additional kg
            
            # Size-based pricing
            size_cost = 0
            if dimensions:
                volume = dimensions.get('length', 0) * dimensions.get('width', 0) * dimensions.get('height', 0)
                if volume > 1000:  # cm³
                    size_cost = 5  # Additional 5 AED for large items
            
            total_cost = base_cost + weight_cost + size_cost
            
            # Estimated delivery time
            delivery_estimates = {
                'same_day': {'min': 4, 'max': 8, 'unit': 'hours'},
                'express': {'min': 1, 'max': 2, 'unit': 'days'},
                'standard': {'min': 2, 'max': 4, 'unit': 'days'}
            }
            
            return {
                'success': True,
                'cost': round(total_cost, 2),
                'currency': 'AED',
                'service_type': service_type,
                'estimated_delivery': delivery_estimates[service_type],
                'breakdown': {
                    'base_cost': base_cost,
                    'weight_cost': weight_cost,
                    'size_cost': size_cost
                },
                'from_emirate': from_emirate,
                'to_emirate': to_emirate
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_shipping_options(self, from_emirate: str, to_emirate: str, 
                           weight: float, dimensions: Dict = None) -> List[Dict[str, Any]]:
        """Get all available shipping options"""
        options = []
        
        # Check if same-day delivery is available
        from_zone_info = self.uae_zones.get(from_emirate, {'same_day': False})
        to_zone_info = self.uae_zones.get(to_emirate, {'same_day': False})
        
        service_types = ['standard', 'express']
        if from_zone_info['same_day'] and to_zone_info['same_day']:
            service_types.append('same_day')
        
        for service_type in service_types:
            cost_info = self.calculate_shipping_cost(
                from_emirate, to_emirate, weight, dimensions, service_type
            )
            
            if cost_info['success']:
                options.append({
                    'service_type': service_type,
                    'provider': 'aramex',  # Default provider
                    'cost': cost_info['cost'],
                    'currency': cost_info['currency'],
                    'estimated_delivery': cost_info['estimated_delivery'],
                    'supports_cod': True,
                    'supports_tracking': True
                })
        
        return sorted(options, key=lambda x: x['cost'])
    
    def create_shipment(self, order_data: Dict[str, Any], shipping_option: Dict[str, Any]) -> Dict[str, Any]:
        """Create a shipment with the selected provider"""
        try:
            provider = shipping_option.get('provider', 'aramex')
            
            if provider == 'aramex':
                return self._create_aramex_shipment(order_data, shipping_option)
            elif provider == 'emirates_post':
                return self._create_emirates_post_shipment(order_data, shipping_option)
            else:
                return self._create_mock_shipment(order_data, shipping_option)
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_mock_shipment(self, order_data: Dict[str, Any], shipping_option: Dict[str, Any]) -> Dict[str, Any]:
        """Create a mock shipment for development/testing"""
        tracking_number = f"VUE{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return {
            'success': True,
            'tracking_number': tracking_number,
            'provider': shipping_option.get('provider', 'aramex'),
            'service_type': shipping_option['service_type'],
            'cost': shipping_option['cost'],
            'currency': shipping_option['currency'],
            'estimated_delivery': self._calculate_delivery_date(shipping_option['estimated_delivery']),
            'status': 'created',
            'label_url': f"https://api.example.com/labels/{tracking_number}.pdf"
        }
    
    def _create_aramex_shipment(self, order_data: Dict[str, Any], shipping_option: Dict[str, Any]) -> Dict[str, Any]:
        """Create shipment with Aramex (mock implementation)"""
        # In a real implementation, this would call Aramex API
        return self._create_mock_shipment(order_data, shipping_option)
    
    def _create_emirates_post_shipment(self, order_data: Dict[str, Any], shipping_option: Dict[str, Any]) -> Dict[str, Any]:
        """Create shipment with Emirates Post (mock implementation)"""
        # In a real implementation, this would call Emirates Post API
        return self._create_mock_shipment(order_data, shipping_option)
    
    def track_shipment(self, tracking_number: str, provider: str = 'aramex') -> Dict[str, Any]:
        """Track a shipment"""
        try:
            if provider == 'aramex':
                return self._track_aramex_shipment(tracking_number)
            elif provider == 'emirates_post':
                return self._track_emirates_post_shipment(tracking_number)
            else:
                return self._track_mock_shipment(tracking_number)
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _track_mock_shipment(self, tracking_number: str) -> Dict[str, Any]:
        """Mock shipment tracking for development"""
        # Simulate tracking events based on when shipment was created
        created_date = datetime.now() - timedelta(days=1)  # Assume created yesterday
        
        events = [
            {
                'status': 'created',
                'description': 'Shipment created',
                'timestamp': created_date.isoformat(),
                'location': 'Dubai, UAE'
            },
            {
                'status': 'picked_up',
                'description': 'Package picked up from seller',
                'timestamp': (created_date + timedelta(hours=2)).isoformat(),
                'location': 'Dubai, UAE'
            },
            {
                'status': 'in_transit',
                'description': 'Package in transit',
                'timestamp': (created_date + timedelta(hours=6)).isoformat(),
                'location': 'Dubai Sorting Facility'
            }
        ]
        
        return {
            'success': True,
            'tracking_number': tracking_number,
            'status': 'in_transit',
            'estimated_delivery': (datetime.now() + timedelta(days=1)).isoformat(),
            'events': events
        }
    
    def _track_aramex_shipment(self, tracking_number: str) -> Dict[str, Any]:
        """Track Aramex shipment (mock implementation)"""
        return self._track_mock_shipment(tracking_number)
    
    def _track_emirates_post_shipment(self, tracking_number: str) -> Dict[str, Any]:
        """Track Emirates Post shipment (mock implementation)"""
        return self._track_mock_shipment(tracking_number)
    
    def _calculate_delivery_date(self, delivery_estimate: Dict[str, Any]) -> str:
        """Calculate estimated delivery date"""
        now = datetime.now()
        
        if delivery_estimate['unit'] == 'hours':
            delivery_date = now + timedelta(hours=delivery_estimate['max'])
        else:  # days
            delivery_date = now + timedelta(days=delivery_estimate['max'])
        
        return delivery_date.isoformat()
    
    def get_delivery_zones(self) -> Dict[str, Any]:
        """Get available delivery zones"""
        return {
            'zones': self.uae_zones,
            'coverage': 'UAE nationwide',
            'same_day_emirates': [emirate for emirate, info in self.uae_zones.items() if info['same_day']]
        }
    
    def validate_address(self, address: Dict[str, Any]) -> Dict[str, Any]:
        """Validate shipping address"""
        required_fields = ['street', 'city', 'emirate', 'postal_code']
        missing_fields = []
        
        for field in required_fields:
            if not address.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            return {
                'valid': False,
                'errors': missing_fields,
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }
        
        # Validate emirate
        if address['emirate'] not in self.uae_zones:
            return {
                'valid': False,
                'errors': ['emirate'],
                'message': 'Invalid emirate. Must be one of: ' + ', '.join(self.uae_zones.keys())
            }
        
        return {
            'valid': True,
            'normalized_address': {
                'street': address['street'].strip(),
                'city': address['city'].strip(),
                'emirate': address['emirate'],
                'postal_code': address['postal_code'].strip(),
                'country': 'UAE'
            }
        }
    
    def get_cod_availability(self, emirate: str) -> bool:
        """Check if Cash on Delivery is available for the emirate"""
        # COD is available in all UAE emirates
        return emirate in self.uae_zones

# Singleton instance
shipping_service = ShippingService()

