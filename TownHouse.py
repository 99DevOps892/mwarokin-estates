```python
# Real Estate Management System for Town Houses

class TownHouse:
    def __init__(self, house_id, address, price, square_feet, bedrooms, bathrooms, status="available", listing_type="for_sale"):
        self.house_id = house_id
        self.address = address
        self.price = price
        self.square_feet = square_feet
        self.bedrooms = bedrooms
        self.bathrooms = bathrooms
        self.status = status  # available, rented, sold, under_contract
        self.listing_type = listing_type  # for_sale, for_rent
        self.tenant = None
        self.owner = None
        
    def update_status(self, new_status):
        self.status = new_status
        
    def update_price(self, new_price):
        self.price = new_price
        
    def assign_tenant(self, tenant_name):
        if self.status == "available" and self.listing_type == "for_rent":
            self.tenant = tenant_name
            self.status = "rented"
            return True
        return False
        
    def assign_owner(self, owner_name):
        if self.status == "available" and self.listing_type == "for_sale":
            self.owner = owner_name
            self.status = "sold"
            return True
        return False
        
    def get_details(self):
        return {
            'id': self.house_id,
            'address': self.address,
            'price': self.price,
            'square_feet': self.square_feet,
            'bedrooms': self.bedrooms,
            'bathrooms': self.bathrooms,
            'status': self.status,
            'listing_type': self.listing_type,
            'tenant': self.tenant,
            'owner': self.owner
        }


class RealEstateManager:
    def __init__(self):
        self.town_houses = {}
        self.house_counter = 1
        
    def add_town_house(self, address, price, square_feet, bedrooms, bathrooms, listing_type="for_sale"):
        house_id = self.house_counter
        new_house = TownHouse(house_id, address, price, square_feet, bedrooms, bathrooms, listing_type=listing_type)
        self.town_houses[house_id] = new_house
        self.house_counter += 1
        return house_id
        
    def remove_town_house(self, house_id):
        if house_id in self.town_houses:
            del self.town_houses[house_id]
            return True
        return False
        
    def get_house(self, house_id):
        return self.town_houses.get(house_id)
        
    def update_house_status(self, house_id, new_status):
        house = self.get_house(house_id)
        if house:
            house.update_status(new_status)
            return True
        return False
        
    def update_house_price(self, house_id, new_price):
        house = self.get_house(house_id)
        if house:
            house.update_price(new_price)
            return True
        return False
        
    def rent_house(self, house_id, tenant_name):
        house = self.get_house(house_id)
        if house and house.listing_type == "for_rent":
            return house.assign_tenant(tenant_name)
        return False
        
    def sell_house(self, house_id, owner_name):
        house = self.get_house(house_id)
        if house and house.listing_type == "for_sale":
            return house.assign_owner(owner_name)
        return False
        
    def search_houses(self, filters=None):
        results = []
        for house in self.town_houses.values():
            if self._matches_filters(house, filters):
                results.append(house.get_details())
        return results
        
    def _matches_filters(self, house, filters):
        if not filters:
            return True
            
        if 'min_price' in filters and house.price < filters['min_price']:
            return False
        if 'max_price' in filters and house.price > filters['max_price']:
            return False
        if 'min_bedrooms' in filters and house.bedrooms < filters['min_bedrooms']:
            return False
        if 'min_bathrooms' in filters and house.bathrooms < filters['min_bathrooms']:
            return False
        if 'status' in filters and house.status != filters['status']:
            return False
        if 'listing_type' in filters and house.listing_type != filters['listing_type']:
            return False
            
        return True
        
    def get_available_houses(self):
        return self.search_houses({'status': 'available'})
        
    def get_houses_for_sale(self):
        return self.search_houses({'listing_type': 'for_sale', 'status': 'available'})
        
    def get_houses_for_rent(self):
        return self.search_houses({'listing_type': 'for_rent', 'status': 'available'})


class FinancialManager:
    def __init__(self, real_estate_manager):
        self.real_estate_manager = real_estate_manager
        self.transactions = []
        self.transaction_counter = 1
        
    def record_sale(self, house_id, buyer_name, sale_price, commission_rate=0.05):
        house = self.real_estate_manager.get_house(house_id)
        if house and house.listing_type == "for_sale":
            commission = sale_price * commission_rate
            transaction = {
                'id': self.transaction_counter,
                'type': 'sale',
                'house_id': house_id,
                'buyer': buyer_name,
                'amount': sale_price,
                'commission': commission,
                'date': '2024-01-01'  # In real implementation, use datetime
            }
            self.transactions.append(transaction)
            self.transaction_counter += 1
            return transaction
        return None
        
    def record_rental(self, house_id, tenant_name, monthly_rent, duration_months, security_deposit=0):
        house = self.real_estate_manager.get_house(house_id)
        if house and house.listing_type == "for_rent":
            total_rent = monthly_rent * duration_months
            transaction = {
                'id': self.transaction_counter,
                'type': 'rental',
                'house_id': house_id,
                'tenant': tenant_name,
                'monthly_rent': monthly_rent,
                'duration': duration_months,
                'total_amount': total_rent,
                'security_deposit': security_deposit,
                'date': '2024-01-01'
            }
            self.transactions.append(transaction)
            self.transaction_counter += 1
            return transaction
        return None
        
    def get_total_revenue(self):
        total = 0
        for transaction in self.transactions:
            if transaction['type'] == 'sale':
                total += transaction['amount']
            elif transaction['type'] == 'rental':
                total += transaction['total_amount']
        return total
        
    def get_total_commission(self):
        total = 0
        for transaction in self.transactions:
            if transaction['type'] == 'sale':
                total += transaction.get('commission', 0)
        return total


class MaintenanceManager:
    def __init__(self, real_estate_manager):
        self.real_estate_manager = real_estate_manager
        self.maintenance_requests = []
        self.request_counter = 1
        
    def create_maintenance_request(self, house_id, description, priority="medium"):
        house = self.real_estate_manager.get_house(house_id)
        if house:
            request = {
                'id': self.request_counter,
                'house_id': house_id,
                'description': description,
                'priority': priority,
                'status': 'open',
                'date_created': '2024-01-01',
                'date_resolved': None
            }
            self.maintenance_requests.append(request)
            self.request_counter += 1
            return request
        return None
        
    def resolve_maintenance_request(self, request_id, resolution_notes):
        for request in self.maintenance_requests:
            if request['id'] == request_id:
                request['status'] = 'resolved'
                request['resolution_notes'] = resolution_notes
                request['date_resolved'] = '2024-01-02'
                return True
        return False
        
    def get_open_requests(self):
        return [req for req in self.maintenance_requests if req['status'] == 'open']
        
    def get_requests_by_house(self, house_id):
        return [req for req in self.maintenance_requests if req['house_id'] == house_id]


# Example usage and demonstration
def main():
    # Create real estate manager
    manager = RealEstateManager()
    
    # Add some sample town houses
    house1 = manager.add_town_house(
        "123 Main Street, New York, USA", 
        250000, 
        1500, 
        3, 
        2, 
        "for_sale"
    )
    
    house2 = manager.add_town_house(
        "456 Oak Avenue, Los Angeles, USA", 
        1800, 
        1200, 
        2, 
        1, 
        "for_rent"
    )
    
    house3 = manager.add_town_house(
        "789 Pine Road, Chicago, USA", 
        320000, 
        1800, 
        4, 
        3, 
        "for_sale"
    )
    
    # Initialize financial and maintenance managers
    financial_manager = FinancialManager(manager)
    maintenance_manager = MaintenanceManager(manager)
    
    # Demonstrate searching
    print("Available houses for sale:")
    for_sale = manager.get_houses_for_sale()
    for house in for_sale:
        print(f"ID: {house['id']}, Address: {house['address']}, Price: ${house['price']}")
    
    print("\nAvailable houses for rent:")
    for_rent = manager.get_houses_for_rent()
    for house in for_rent:
        print(f"ID: {house['id']}, Address: {house['address']}, Rent: ${house['price']}/month")
    
    # Demonstrate renting a house
    if manager.rent_house(house2, "John Doe"):
        print(f"\nHouse {house2} rented to John Doe")
    
    # Demonstrate selling a house
    if manager.sell_house(house1, "Jane Smith"):
        print(f"House {house1} sold to Jane Smith")
    
    # Record financial transactions
    financial_manager.record_sale(house1, "Jane Smith", 250000)
    financial_manager.record_rental(house2, "John Doe", 1800, 12, 1800)
    
    # Create maintenance request
    maintenance_manager.create_maintenance_request(
        house2, 
        "Kitchen sink leaking", 
        "high"
    )
    
    # Display financial summary
    print(f"\nTotal Revenue: ${financial_manager.get_total_revenue()}")
    print(f"Total Commission: ${financial_manager.get_total_commission()}")
    
    # Display maintenance status
    open_requests = maintenance_manager.get_open_requests()
    print(f"\nOpen Maintenance Requests: {len(open_requests)}")


if __name__ == "__main__":
    main()
```

This Python real estate management system for town houses includes:

**Core Features:**
- `TownHouse` class to manage individual property details
- `RealEstateManager` for property listing and management
- `FinancialManager` for handling sales, rentals, and commissions
- `MaintenanceManager` for tracking maintenance requests

**Key Functionality:**
- Add/remove town houses
- Search and filter properties
- Handle property sales and rentals
- Track financial transactions
- Manage maintenance requests
- Update property status and prices

**Data Management:**
- Property details (address, price, bedrooms, bathrooms, square footage)
- Status tracking (available, rented, sold, under contract)
- Tenant and owner assignment
- Financial records and commission tracking
- Maintenance request management

The system provides a comprehensive foundation for managing town house properties with extensibility for additional features like advanced search, reporting, and integration with external systems.