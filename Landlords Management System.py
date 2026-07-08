import datetime
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
from collections import defaultdict
from typing import Dict, List, Any

class LandlordManagementSystem:
    def __init__(self, landlord: Dict[str, Any]):
        self.landlord = landlord
        self.root = tk.Tk()
        self.root.title("Landlord Management System")
        self.root.geometry("1200x800")
        
        # Style for beautiful UI
        self.style = ttk.Style()
        self.style.theme_use('clam')  # Use a modern theme
        self.style.configure('TLabel', font=('Helvetica', 12))
        self.style.configure('TButton', font=('Helvetica', 12), padding=10)
        self.style.configure('Header.TLabel', font=('Helvetica', 16, 'bold'))
        self.style.configure('Subheader.TLabel', font=('Helvetica', 14, 'underline'))
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tabs
        self.create_contact_tab()
        self.create_properties_tab()
        self.create_rent_summary_tab()
        self.create_per_property_tab()
        self.create_services_tab()
        
        # Advanced features: Buttons for actions
        action_frame = ttk.Frame(self.root)
        action_frame.pack(pady=10)
        
        refresh_btn = ttk.Button(action_frame, text="Refresh Data", command=self.refresh_data)
        refresh_btn.grid(row=0, column=0, padx=10)
        
        export_btn = ttk.Button(action_frame, text="Export Report", command=self.export_report)
        export_btn.grid(row=0, column=1, padx=10)
        
        remind_btn = ttk.Button(action_frame, text="Send Reminders to Overdue", command=self.send_reminders)
        remind_btn.grid(row=0, column=2, padx=10)
        
        self.calculate_metrics()
        self.update_displays()
        
        self.root.mainloop()
    
    def calculate_metrics(self):
        # Determine current month for rent calculations
        now = datetime.datetime.now()  # Or set to specific date: datetime.datetime(2025, 9, 11)
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month + 1, day=1)
        current_month_end = (next_month - datetime.timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
        
        properties = self.landlord.get('properties', [])
        self.total_properties = len(properties)
        self.total_tenants = sum(len(prop.get('tenants', [])) for prop in properties)
        self.avg_tenants_per_property = self.total_tenants / self.total_properties if self.total_properties > 0 else 0
        
        self.paid_tenants = []
        self.overdue_tenants = []
        self.total_rent_collected = 0
        self.total_overdue_amount = 0
        self.all_rent_amounts = []
        
        self.property_metrics = []
        
        for prop in properties:
            prop_tenants = prop.get('tenants', [])
            prop_total_tenants = len(prop_tenants)
            prop_paid_tenants = []
            prop_overdue_tenants = []
            prop_rent_collected = 0
            prop_overdue_amount = 0
            prop_rent_amounts = []
            
            for tenant in prop_tenants:
                self.all_rent_amounts.append(tenant.get('rent_amount', 0))
                prop_rent_amounts.append(tenant.get('rent_amount', 0))
                monthly_payments = [p for p in tenant.get('payments', []) if current_month_start <= p.get('date', datetime.datetime.min) <= current_month_end]
                paid_this_month = any(p.get('status') == 'paid' for p in monthly_payments)
                expected_rent = tenant.get('rent_amount', 0)
                
                if paid_this_month:
                    self.total_rent_collected += expected_rent
                    prop_rent_collected += expected_rent
                    self.paid_tenants.append(tenant)
                    prop_paid_tenants.append(tenant)
                else:
                    overdue = expected_rent
                    self.total_overdue_amount += overdue
                    prop_overdue_amount += overdue
                    self.overdue_tenants.append(tenant)
                    prop_overdue_tenants.append(tenant)
            
            prop_paid_count = len(prop_paid_tenants)
            prop_overdue_count = len(prop_overdue_tenants)
            
            if prop_total_tenants > 0:
                prop_on_time_pct = (prop_paid_count / prop_total_tenants) * 100
                prop_overdue_pct = (prop_overdue_count / prop_total_tenants) * 100
                prop_avg_rent_tenant = sum(prop_rent_amounts) / prop_total_tenants
                prop_highest_rent = max(prop_rent_amounts) if prop_rent_amounts else 0
                prop_lowest_rent = min(prop_rent_amounts) if prop_rent_amounts else 0
                prop_avg_rent_per_prop = sum(prop_rent_amounts)
            else:
                prop_on_time_pct = prop_overdue_pct = prop_avg_rent_tenant = prop_highest_rent = prop_lowest_rent = 0
                prop_avg_rent_per_prop = 0
            
            self.property_metrics.append({
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
                'avg_rent_per_prop': prop_avg_rent_per_prop,
                'paid_tenants': prop_paid_tenants,
                'overdue_tenants': prop_overdue_tenants
            })
        
        self.total_tenants_overall = len(self.all_rent_amounts)
        self.paid_count = len(self.paid_tenants)
        self.overdue_count = len(self.overdue_tenants)
        
        if self.total_tenants_overall > 0:
            self.on_time_percentage = (self.paid_count / self.total_tenants_overall) * 100
            self.overdue_percentage = (self.overdue_count / self.total_tenants_overall) * 100
            self.avg_rent_per_tenant = sum(self.all_rent_amounts) / self.total_tenants_overall
            self.highest_rent = max(self.all_rent_amounts) if self.all_rent_amounts else 0
            self.lowest_rent = min(self.all_rent_amounts) if self.all_rent_amounts else 0
        else:
            self.on_time_percentage = self.overdue_percentage = self.avg_rent_per_tenant = self.highest_rent = self.lowest_rent = 0
    
    def create_contact_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Contact Details")
        
        header = ttk.Label(tab, text="🏠 Landlord Information", style='Header.TLabel')
        header.pack(pady=10)
        
        contact_frame = ttk.Frame(tab)
        contact_frame.pack(pady=10)
        
        ttk.Label(contact_frame, text=f"Name: {self.landlord['name']}", style='TLabel').grid(row=0, column=0, sticky='w', pady=5)
        ttk.Label(contact_frame, text=f"Email: {self.landlord['email']}", style='TLabel').grid(row=1, column=0, sticky='w', pady=5)
        ttk.Label(contact_frame, text=f"Phone: {self.landlord['phone']}", style='TLabel').grid(row=2, column=0, sticky='w', pady=5)
    
    def create_properties_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Properties")
        
        header = ttk.Label(tab, text="🏘️ Properties Owned", style='Header.TLabel')
        header.pack(pady=10)
        
        self.properties_list = scrolledtext.ScrolledText(tab, wrap=tk.WORD, width=100, height=20, font=('Helvetica', 12))
        self.properties_list.pack(pady=10)
    
    def create_rent_summary_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Rent Summary")
        
        header = ttk.Label(tab, text="💰 Overall Tenant and Rent Summary (This Month)", style='Header.TLabel')
        header.pack(pady=10)
        
        summary_frame = ttk.Frame(tab)
        summary_frame.pack(pady=10)
        
        self.summary_labels = []
        rows = [
            f"Total Number of Tenants: {self.total_tenants_overall}",
            f"Tenants Who Have Paid Rent This Month: {self.paid_count}",
            f"Overdue Tenants: {self.overdue_count}",
            f"Total Rent Collected This Month: ${self.total_rent_collected:,.2f}",
            f"Total Overdue Amount: ${self.total_overdue_amount:,.2f}",
            f"Percentage of Tenants Who Paid On Time: {self.on_time_percentage:.1f}%",
            f"Percentage of Overdue Tenants: {self.overdue_percentage:.1f}%",
            f"Average Rent Amount per Tenant: ${self.avg_rent_per_tenant:.2f}",
            f"Highest Rent Amount: ${self.highest_rent:,.2f}",
            f"Lowest Rent Amount: ${self.lowest_rent:,.2f}",
            f"Average Number of Tenants per Property: {self.avg_tenants_per_property:.1f}",
            f"Total Number of Properties Managed: {self.total_properties}"
        ]
        for i, text in enumerate(rows):
            label = ttk.Label(summary_frame, text=text, style='TLabel')
            label.grid(row=i, column=0, sticky='w', pady=5)
            self.summary_labels.append(label)
        
        ttk.Label(tab, text="✅ Tenants Who Paid (Names & Contacts):", style='Subheader.TLabel').pack(pady=10)
        self.paid_tenants_text = scrolledtext.ScrolledText(tab, wrap=tk.WORD, width=100, height=10, font=('Helvetica', 12))
        self.paid_tenants_text.pack(pady=5)
        
        ttk.Label(tab, text="⚠️ Overdue Tenants (Names & Contacts):", style='Subheader.TLabel').pack(pady=10)
        self.overdue_tenants_text = scrolledtext.ScrolledText(tab, wrap=tk.WORD, width=100, height=10, font=('Helvetica', 12))
        self.overdue_tenants_text.pack(pady=5)
    
    def create_per_property_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Per-Property Metrics")
        
        header = ttk.Label(tab, text="📊 Per-Property Detailed Metrics", style='Header.TLabel')
        header.pack(pady=10)
        
        self.per_prop_notebook = ttk.Notebook(tab)
        self.per_prop_notebook.pack(fill=tk.BOTH, expand=True)
        
        self.prop_tabs = []
    
    def create_services_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Available Services")
        
        header = ttk.Label(tab, text="🛠️ Available Services", style='Header.TLabel')
        header.pack(pady=10)
        
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
        
        services_text = scrolledtext.ScrolledText(tab, wrap=tk.WORD, width=100, height=20, font=('Helvetica', 12))
        services_text.pack(pady=10)
        for service in services:
            services_text.insert(tk.END, f" - {service}\n")
        services_text.config(state=tk.DISABLED)
    
    def update_displays(self):
        # Update Properties Tab
        self.properties_list.delete(1.0, tk.END)
        self.properties_list.insert(tk.END, f"Properties Owned: {self.total_properties}\n\nProperty Addresses:\n")
        for prop in self.landlord.get('properties', []):
            self.properties_list.insert(tk.END, f" - {prop['address']} (ID: {prop['id']})\n")
        self.properties_list.config(state=tk.DISABLED)
        
        # Update Rent Summary Tab
        summaries = [
            f"Total Number of Tenants: {self.total_tenants_overall}",
            f"Tenants Who Have Paid Rent This Month: {self.paid_count}",
            f"Overdue Tenants: {self.overdue_count}",
            f"Total Rent Collected This Month: ${self.total_rent_collected:,.2f}",
            f"Total Overdue Amount: ${self.total_overdue_amount:,.2f}",
            f"Percentage of Tenants Who Paid On Time: {self.on_time_percentage:.1f}%",
            f"Percentage of Overdue Tenants: {self.overdue_percentage:.1f}%",
            f"Average Rent Amount per Tenant: ${self.avg_rent_per_tenant:.2f}",
            f"Highest Rent Amount: ${self.highest_rent:,.2f}",
            f"Lowest Rent Amount: ${self.lowest_rent:,.2f}",
            f"Average Number of Tenants per Property: {self.avg_tenants_per_property:.1f}",
            f"Total Number of Properties Managed: {self.total_properties}"
        ]
        for label, text in zip(self.summary_labels, summaries):
            label.config(text=text)
        
        self.paid_tenants_text.delete(1.0, tk.END)
        for tenant in self.paid_tenants:
            self.paid_tenants_text.insert(tk.END, f" - {tenant['name']} ({tenant['email']}, {tenant['phone']})\n")
        self.paid_tenants_text.config(state=tk.DISABLED)
        
        self.overdue_tenants_text.delete(1.0, tk.END)
        for tenant in self.overdue_tenants:
            self.overdue_tenants_text.insert(tk.END, f" - {tenant['name']} ({tenant['email']}, {tenant['phone']})\n")
        self.overdue_tenants_text.config(state=tk.DISABLED)
        
        # Update Per-Property Tabs
        for subtab in self.prop_tabs:
            subtab.destroy()
        self.prop_tabs = []
        
        for metric in self.property_metrics:
            prop = metric['property']
            subtab = ttk.Frame(self.per_prop_notebook)
            self.per_prop_notebook.add(subtab, text=prop['address'][:20] + '...' if len(prop['address']) > 20 else prop['address'])
            self.prop_tabs.append(subtab)
            
            prop_frame = ttk.Frame(subtab)
            prop_frame.pack(pady=10)
            
            rows = [
                f"Total Tenants: {metric['total_tenants']}",
                f"Paid This Month: {metric['paid_count']}",
                f"Overdue: {metric['overdue_count']}",
                f"Rent Collected: ${metric['rent_collected']:,.2f}",
                f"Overdue Amount: ${metric['overdue_amount']:,.2f}",
                f"On-Time %: {metric['on_time_pct']:.1f}%",
                f"Overdue %: {metric['overdue_pct']:.1f}%",
                f"Avg Rent per Tenant: ${metric['avg_rent_tenant']:.2f}",
                f"Highest Rent: ${metric['highest_rent']:,.2f}",
                f"Lowest Rent: ${metric['lowest_rent']:,.2f}",
                f"Avg Rent per Property: ${metric['avg_rent_per_prop']:.2f}"
            ]
            for i, text in enumerate(rows):
                ttk.Label(prop_frame, text=text, style='TLabel').grid(row=i, column=0, sticky='w', pady=5)
            
            ttk.Label(subtab, text="✅ Paid Tenants:", style='Subheader.TLabel').pack(pady=10)
            paid_text = scrolledtext.ScrolledText(subtab, wrap=tk.WORD, width=80, height=5, font=('Helvetica', 12))
            paid_text.pack(pady=5)
            for tenant in metric['paid_tenants']:
                paid_text.insert(tk.END, f" - {tenant['name']} ({tenant['email']}, {tenant['phone']})\n")
            paid_text.config(state=tk.DISABLED)
            
            ttk.Label(subtab, text="⚠️ Overdue Tenants:", style='Subheader.TLabel').pack(pady=10)
            overdue_text = scrolledtext.ScrolledText(subtab, wrap=tk.WORD, width=80, height=5, font=('Helvetica', 12))
            overdue_text.pack(pady=5)
            for tenant in metric['overdue_tenants']:
                overdue_text.insert(tk.END, f" - {tenant['name']} ({tenant['email']}, {tenant['phone']})\n")
            overdue_text.config(state=tk.DISABLED)
    
    def refresh_data(self):
        # Simulate refreshing data - in real system, reload from DB or file
        self.calculate_metrics()
        self.update_displays()
        tk.messagebox.showinfo("Refresh", "Data refreshed successfully!")
    
    def export_report(self):
        # Simulate export - in real, write to file
        tk.messagebox.showinfo("Export", "Report exported to file (simulated).")
    
    def send_reminders(self):
        # Simulate sending emails/SMS
        if self.overdue_tenants:
            tk.messagebox.showinfo("Reminders", f"Reminders sent to {len(self.overdue_tenants)} overdue tenants (simulated).")
        else:
            tk.messagebox.showinfo("Reminders", "No overdue tenants.")

# Example usage:
# landlord_data = {...}  # Your data dict
# app = LandlordManagementSystem(landlord_data)