import datetime
from collections import defaultdict
from typing import Dict, List, Any

def display_landlord_info(landlord: Dict[str, Any]) -> None:
    
    Displays comprehensive landlord information in a user-friendly format.
    Assumes the landlord dict structure includes:
    - 'name', 'email', 'phone'
    - 'properties': list of dicts, each with:
      - 'id', 'address'
      - 'tenants': list of dicts, each with:
        - 'name', 'email', 'phone', 'rent_amount'
        - 'payments': list of dicts with 'date' (datetime), 'amount', 'status' ('paid', 'overdue')
    Current month is determined dynamically.
    
    # Determine current month for rent calculations
    now = datetime.datetime.now()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    current_month_end = (now.replace(month=now.month % 12 + 1, day=1) - datetime.timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
    
    print("🏠 Landlord Information")
    print("=" * 50)
    
    # Basic Contact Details
    print("\n📞 Contact Details")
    print("-" * 20)
    print(f"Name: {landlord['name']}")
    print(f"Email: {landlord['email']}")
    print(f"Phone: {landlord['phone']}")
    
    # Overall Properties Summary
    properties = landlord.get('properties', [])
    total_properties = len(properties)
    total_tenants = sum(len(prop.get('tenants', [])) for prop in properties)
    avg_tenants_per_property = total_tenants / total_properties if total_properties > 0 else 0
    
    print(f"\n🏘️ Properties Owned: {total_properties}")
    print("\nProperty Addresses:")
    print("-" * 20)
    for prop in properties:
        print(f" - {prop['address']} (ID: {prop['id']})")
    
    # Overall Tenant and Rent Metrics
    print("\n💰 Overall Tenant and Rent Summary (This Month)")
    print("-" * 40)
    
    paid_tenants = []
    overdue_tenants = []
    total_rent_collected = 0
    total_overdue_amount = 0
    all_rent_amounts = []
    
    for prop in properties:
        for tenant in prop.get('tenants', []):
            all_rent_amounts.append(tenant.get('rent_amount', 0))
            # Check payments for this month
            monthly_payments = [p for p in tenant.get('payments', []) if current_month_start <= p.get('date') <= current_month_end]
            paid_this_month = any(p.get('status') == 'paid' for p in monthly_payments)
            expected_rent = tenant.get('rent_amount', 0)
            
            if paid_this_month:
                total_rent_collected += expected_rent
                paid_tenants.append(tenant)
            else:
                overdue_amount = expected_rent
                total_overdue_amount += overdue_amount
                overdue_tenants.append(tenant)
    
    total_tenants_overall = len(all_rent_amounts)
    paid_count = len(paid_tenants)
    overdue_count = len(overdue_tenants)
    
    if total_tenants_overall > 0:
        on_time_percentage = (paid_count / total_tenants_overall) * 100
        overdue_percentage = (overdue_count / total_tenants_overall) * 100
        avg_rent_per_tenant = sum(all_rent_amounts) / total_tenants_overall
        highest_rent = max(all_rent_amounts) if all_rent_amounts else 0
        lowest_rent = min(all_rent_amounts) if all_rent_amounts else 0
    else:
        on_time_percentage = overdue_percentage = avg_rent_per_tenant = highest_rent = lowest_rent = 0
    
    print(f"Total Number of Tenants: {total_tenants_overall}")
    print(f"Tenants Who Have Paid Rent This Month: {paid_count}")
    print(f"Overdue Tenants: {overdue_count}")
    print(f"Total Rent Collected This Month: ${total_rent_collected:,.2f}")
    print(f"Total Overdue Amount: ${total_overdue_amount:,.2f}")
    print(f"Percentage of Tenants Who Paid On Time: {on_time_percentage:.1f}%")
    print(f"Percentage of Overdue Tenants: {overdue_percentage:.1f}%")
    print(f"Average Rent Amount per Tenant: ${avg_rent_per_tenant:.2f}")
    print(f"Highest Rent Amount: ${highest_rent:,.2f}")
    print(f"Lowest Rent Amount: ${lowest_rent:,.2f}")
    print(f"Average Number of Tenants per Property: {avg_tenants_per_property:.1f}")
    print(f"Total Number of Properties Managed: {total_properties}")
    
    # List Paid and Overdue Tenants
    print("\n✅ Tenants Who Paid (Names & Contacts):")
    for tenant in paid_tenants:
        print(f" - {tenant['name']} ({tenant['email']}, {tenant['phone']})")
    
    print("\n⚠️ Overdue Tenants (Names & Contacts):")
    for tenant in overdue_tenants:
        print(f" - {tenant['name']} ({tenant['email']}, {tenant['phone']})")
    
    # Per-Property Breakdown
    print("\n📊 Per-Property Detailed Metrics")
    print("-" * 40)
    property_metrics = []
    
    for prop in properties:
        prop_tenants = prop.get('tenants', [])
        prop_total_tenants = len(prop_tenants)
        prop_paid_tenants = []
        prop_overdue_tenants = []
        prop_rent_collected = 0
        prop_overdue_amount = 0
        prop_rent_amounts = []
        
        for tenant in prop_tenants:
            prop_rent_amounts.append(tenant.get('rent_amount', 0))
            monthly_payments = [p for p in tenant.get('payments', []) if current_month_start <= p.get('date') <= current_month_end]
            paid_this_month = any(p.get('status') == 'paid' for p in monthly_payments)
            expected_rent = tenant.get('rent_amount', 0)
            
            if paid_this_month:
                prop_rent_collected += expected_rent
                prop_paid_tenants.append(tenant)
            else:
                prop_overdue_amount += expected_rent
                prop_overdue_tenants.append(tenant)
        
        prop_paid_count = len(prop_paid_tenants)
        prop_overdue_count = len(prop_overdue_tenants)
        
        if prop_total_tenants > 0:
            prop_on_time_pct = (prop_paid_count / prop_total_tenants) * 100
            prop_overdue_pct = (prop_overdue_count / prop_total_tenants) * 100
            prop_avg_rent_tenant = sum(prop_rent_amounts) / prop_total_tenants
            prop_highest_rent = max(prop_rent_amounts) if prop_rent_amounts else 0
            prop_lowest_rent = min(prop_rent_amounts) if prop_rent_amounts else 0
            prop_avg_tenants = prop_total_tenants  # Per property, it's just the count
            prop_total_properties_managed = 1  # Trivial per property
            prop_avg_tenants_per_prop = prop_total_tenants  # Same
            prop_avg_rent_per_prop = sum(prop_rent_amounts)
            prop_total_rent_per_prop = prop_rent_collected
            prop_total_overdue_per_prop = prop_overdue_amount
            prop_avg_rent_tenant_per_prop = prop_avg_rent_tenant
            prop_highest_lowest_per_prop = (prop_highest_rent, prop_lowest_rent)
        else:
            prop_on_time_pct = prop_overdue_pct = prop_avg_rent_tenant = prop_highest_rent = prop_lowest_rent = 0
            prop_avg_tenants = prop_total_properties_managed = prop_avg_tenants_per_prop = prop_avg_rent_per_prop = 0
            prop_total_rent_per_prop = prop_total_overdue_per_prop = 0
            prop_avg_rent_tenant_per_prop = 0
            prop_highest_lowest_per_prop = (0, 0)
        
        property_metrics.append({
            'property': prop,
            'paid_count': prop_paid_count,
            'overdue_count': prop_overdue_count,
            'rent_collected': prop_rent_collected,
            'overdue_amount': prop_overdue_amount,
            'on_time_pct': prop_on_time_pct,
            'overdue_pct': prop_overdue_pct,
            'avg_rent_tenant': prop_avg_rent_tenant,
            'highest_rent': prop_highest_rent,
            'lowest_rent': prop_lowest_rent,
            'total_tenants': prop_total_tenants,
            'total_properties': 1,
            'avg_tenants_per_prop': prop_avg_tenants,
            'avg_rent_per_prop': prop_avg_rent_per_prop,
            'total_rent_per_prop': prop_total_rent_per_prop,
            'total_overdue_per_prop': prop_total_overdue_per_prop,
            'paid_tenants': prop_paid_tenants,
            'overdue_tenants': prop_overdue_tenants
        })
        
        # Display per property
        print(f"\nProperty: {prop['address']} (ID: {prop['id']})")
        print("  Total Tenants: {prop_total_tenants}")
        print(f"  Paid This Month: {prop_paid_count}")
        print(f"  Overdue: {prop_overdue_count}")
        print(f"  Rent Collected: ${prop_rent_collected:,.2f}")
        print(f"  Overdue Amount: ${prop_overdue_amount:,.2f}")
        print(f"  On-Time %: {prop_on_time_pct:.1f}%")
        print(f"  Overdue %: {prop_overdue_pct:.1f}%")
        print(f"  Avg Rent per Tenant: ${prop_avg_rent_tenant:.2f}")
        print(f"  Highest Rent: ${prop_highest_rent:,.2f}")
        print(f"  Lowest Rent: ${prop_lowest_rent:,.2f}")
        print(f"  Avg Tenants per Property: {prop_avg_tenants}")
        print(f"  Avg Rent per Property: ${prop_avg_rent_per_prop:.2f}")
    
    # Services Section (Static list as per requirements)
    print("\n🛠️ Available Services")
    print("-" * 20)
    services = [
        "Maintenance Requests", "Lease Renewals", "Payment Processing", "Tenant Screening",
        "Property Inspections", "Legal Compliance", "Financial Reporting", "Communication Tools",
        "Document Management", "Marketing and Advertising", "Online Portals", "Mobile Access",
        "24/7 Support", "Analytics and Insights", "Customizable Workflows",
        "Integration with Other Systems", "Automated Reminders and Notifications",
        "Multi-Language Support", "User Roles and Permissions", "Data Security and Privacy",
        "Regular Updates and Improvements", "Training and Onboarding", "Customer Success Management",
        "Community Forums and Resources", "Feedback and Suggestions", "Scalability and Flexibility",
        "Competitive Pricing and Packages"
    ]
    for service in services:
        print(f" - {service}")
    
    print("\n" + "=" * 50)
    print("End of Landlord Report")
