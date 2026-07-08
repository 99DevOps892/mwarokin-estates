import json
import datetime
from typing import List, Dict, Any
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from dataclasses import dataclass
from enum import Enum

class FeedbackType(Enum):
    GENERAL = "general"
    MAINTENANCE = "maintenance"
    COMMUNITY = "community"
    SERVICES = "services"

@dataclass
class Event:
    id: str
    title: str
    date: str
    description: str
    attendees: List[str] = None
    
    def __post_init__(self):
        if self.attendees is None:
            self.attendees = []

@dataclass
class Feedback:
    date: str
    type: FeedbackType
    message: str
    tenant_id: str

@dataclass
class Payment:
    month: str
    amount: float
    tenant_id: str

@dataclass
class Resource:
    title: str
    link: str
    description: str

class TenantPortal:
    def __init__(self):
        self.events: List[Event] = []
        self.feedback: List[Feedback] = []
        self.payments: List[Payment] = []
        self.resources: List[Resource] = []
        self.current_tenant_id = "T001"  # Simulated current tenant
        
        # Initialize sample data
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """Initialize with sample data"""
        # Sample events
        self.events = [
            Event("E001", "Community BBQ", "2025-10-01", "Join us for a fun BBQ event!"),
            Event("E002", "Tenant Meet & Greet", "2025-11-15", "Meet your neighbors!")
        ]
        
        # Sample feedback
        self.feedback = [
            Feedback("2024-01-10", FeedbackType.GENERAL, 
                    "Great community, but parking needs improvement.", "T001"),
            Feedback("2024-02-20", FeedbackType.MAINTENANCE,
                    "Quick response to plumbing issue, thank you!", "T001")
        ]
        
        # Sample payments
        self.payments = [
            Payment("Jan", 1500.0, "T001"),
            Payment("Feb", 1500.0, "T001"),
            Payment("Mar", 1600.0, "T001"),
            Payment("Apr", 1500.0, "T001"),
            Payment("May", 1500.0, "T001"),
            Payment("Jun", 1550.0, "T001")
        ]
        
        # Sample resources
        self.resources = [
            Resource("Tenant Handbook", "#", "Guide to living in Mwarokin properties."),
            Resource("Maintenance Guide", "#", "How to report and track maintenance issues.")
        ]
    
    def display_community_events(self):
        """Display all community events"""
        print("\n" + "="*50)
        print("COMMUNITY EVENTS")
        print("="*50)
        print("Join upcoming community events organized by Mwarokin Real Estate.\n")
        
        for event in self.events:
            print(f"Event ID: {event.id}")
            print(f"Title: {event.title}")
            print(f"Date: {event.date}")
            print(f"Description: {event.description}")
            print(f"Attendees: {len(event.attendees)}")
            print("-" * 30)
    
    def rsvp_to_event(self, event_id: str):
        """RSVP to a community event"""
        event = next((e for e in self.events if e.id == event_id), None)
        if event:
            if self.current_tenant_id not in event.attendees:
                event.attendees.append(self.current_tenant_id)
                print(f"RSVP confirmed for {event.title} on {event.date}!")
            else:
                print(f"You are already RSVP'd for {event.title}")
        else:
            print("Event not found!")
    
    def submit_event_suggestion(self, suggestion: str):
        """Submit a new event suggestion"""
        if not suggestion:
            print("Please provide an event suggestion.")
            return
        
        print(f"Event suggestion submitted: {suggestion}")
        # In a real implementation, this would be saved to a database
    
    def display_feedback(self):
        """Display previous feedback"""
        print("\n" + "="*50)
        print("TENANT FEEDBACK")
        print("="*50)
        
        tenant_feedback = [fb for fb in self.feedback if fb.tenant_id == self.current_tenant_id]
        
        for fb in tenant_feedback:
            print(f"[{fb.date}] {fb.type.value.upper()}: {fb.message}")
    
    def submit_feedback(self, feedback_type: FeedbackType, message: str):
        """Submit new feedback"""
        if not message:
            print("Please provide a feedback message.")
            return
        
        new_feedback = Feedback(
            date=datetime.datetime.now().strftime("%Y-%m-%d"),
            type=feedback_type,
            message=message,
            tenant_id=self.current_tenant_id
        )
        
        self.feedback.append(new_feedback)
        print(f"Feedback submitted: {feedback_type.value} - {message}")
    
    def display_payment_analytics(self):
        """Display payment analytics using matplotlib"""
        tenant_payments = [p for p in self.payments if p.tenant_id == self.current_tenant_id]
        
        if not tenant_payments:
            print("No payment data available.")
            return
        
        months = [p.month for p in tenant_payments]
        amounts = [p.amount for p in tenant_payments]
        
        plt.figure(figsize=(10, 6))
        plt.plot(months, amounts, marker='o', color='#00b894', linewidth=2)
        plt.fill_between(months, amounts, alpha=0.2, color='#00b894')
        plt.title('Monthly Payment Trends')
        plt.xlabel('Month')
        plt.ylabel('Amount ($)')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()
        
        print(f"Payment analytics displayed for {self.current_tenant_id}")
    
    def update_payment_data(self):
        """Simulate updating payment data with new values"""
        for payment in self.payments:
            if payment.tenant_id == self.current_tenant_id:
                # Add some random variation to simulate new data
                payment.amount += (payment.amount * 0.02) - (payment.amount * 0.01)
        
        print("Payment analytics refreshed with new data.")
    
    def display_resources(self):
        """Display available resources"""
        print("\n" + "="*50)
        print("RESOURCE CENTER")
        print("="*50)
        print("Access helpful resources and guides for tenants.\n")
        
        for resource in self.resources:
            print(f"Title: {resource.title}")
            print(f"Description: {resource.description}")
            print(f"Link: {resource.link}")
            print("-" * 30)
    
    def request_new_resource(self, resource_title: str):
        """Request a new resource"""
        if resource_title:
            print(f"Resource request submitted: {resource_title}")
            # In a real implementation, this would be saved to a database
        else:
            print("Please provide a resource title.")
    
    def run_portal(self):
        """Main method to run the tenant portal"""
        print("="*60)
        print("MWAROKIN TENANT PORTAL - COMMUNITY & ANALYTICS")
        print("="*60)
        print("Engage with community events, provide feedback, view analytics, and access resources.\n")
        
        while True:
            print("\n" + "="*50)
            print("MAIN MENU")
            print("="*50)
            print("1. View Community Events")
            print("2. RSVP to Event")
            print("3. Submit Event Suggestion")
            print("4. View Feedback")
            print("5. Submit Feedback")
            print("6. View Payment Analytics")
            print("7. Refresh Payment Data")
            print("8. View Resources")
            print("9. Request New Resource")
            print("0. Exit")
            print("-" * 50)
            
            choice = input("Enter your choice (0-9): ").strip()
            
            if choice == "1":
                self.display_community_events()
            
            elif choice == "2":
                event_id = input("Enter Event ID to RSVP: ").strip()
                self.rsvp_to_event(event_id)
            
            elif choice == "3":
                suggestion = input("Enter your event suggestion: ").strip()
                self.submit_event_suggestion(suggestion)
            
            elif choice == "4":
                self.display_feedback()
            
            elif choice == "5":
                print("\nFeedback Types:")
                for i, fb_type in enumerate(FeedbackType, 1):
                    print(f"{i}. {fb_type.value.title()}")
                
                try:
                    type_choice = int(input("Select feedback type (1-4): "))
                    if 1 <= type_choice <= 4:
                        fb_type = list(FeedbackType)[type_choice - 1]
                        message = input("Enter your feedback message: ").strip()
                        self.submit_feedback(fb_type, message)
                    else:
                        print("Invalid choice!")
                except ValueError:
                    print("Please enter a valid number!")
            
            elif choice == "6":
                self.display_payment_analytics()
            
            elif choice == "7":
                self.update_payment_data()
                self.display_payment_analytics()
            
            elif choice == "8":
                self.display_resources()
            
            elif choice == "9":
                resource_title = input("Enter resource title you would like to request: ").strip()
                self.request_new_resource(resource_title)
            
            elif choice == "0":
                print("Thank you for using Mwarokin Tenant Portal!")
                print("© 2025 Mwarokin Real Estate. All rights reserved.")
                break
            
            else:
                print("Invalid choice! Please try again.")

def main():
    """Main function to start the tenant portal"""
    portal = TenantPortal()
    portal.run_portal()

if __name__ == "__main__":
    main()


This Python implementation provides a complete real estate management system for town houses with the following features:

## Key Features:

1. **Community Events Management**
   - View upcoming events
   - RSVP to events
   - Submit event suggestions

2. **Tenant Feedback System**
   - Submit feedback with different types (General, Maintenance, Community, Services)
   - View previous feedback history

3. **Payment Analytics**
   - Visualize payment trends using matplotlib
   - Refresh and update payment data
   - Display monthly payment charts

4. **Resource Center**
   - Access tenant resources and guides
   - Request new resources

## Technical Features:

- **Object-Oriented Design**: Uses dataclasses for clean data structures
- **Type Hints**: Full type annotations for better code clarity
- **Enum for Feedback Types**: Ensures type safety for feedback categories
- **Data Visualization**: Uses matplotlib for payment analytics charts
- **Interactive CLI**: User-friendly command-line interface
- **Sample Data**: Pre-populated with realistic sample data

## How to Use:

1. Run the script
2. Use the numbered menu to navigate through features
3. View events, submit feedback, check payment analytics, and access resources
4. Exit using option 0

The system is modular and can be easily extended with database integration, web interfaces, or additional features as needed.