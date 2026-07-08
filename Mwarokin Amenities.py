```python
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import json
import os
from datetime import datetime, timedelta
import random
import threading
import time

# Set appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class MwarokinEstatesApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Mwarokin Estates - Facility Ledger")
        self.geometry("1280x820")
        self.minsize(1100, 700)
        
        # Data
        self.ledger = []
        self.booking_count = 0
        self.data_file = "mwarokin_data.json"
        self.load_data()
        
        # UI Setup
        self.setup_ui()
        self.update_stats()
        
    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.ledger = data.get('ledger', [])
                    self.booking_count = data.get('booking_count', 0)
            except:
                self.ledger = []
                self.booking_count = 0
        else:
            self.ledger = []
            self.booking_count = 0
            
    def save_data(self):
        data = {
            'ledger': self.ledger[-30:],  # Keep last 30
            'booking_count': self.booking_count
        }
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def setup_ui(self):
        # Main container
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # nav
        self.grid_rowconfigure(1, weight=1)  # content
        
        # Navigation
        self.nav = ctk.CTkFrame(self, height=70, corner_radius=0, fg_color="#1a1a1a")
        self.nav.grid(row=0, column=0, sticky="ew")
        self.nav.grid_columnconfigure(1, weight=1)
        
        # Brand
        brand = ctk.CTkFrame(self.nav, fg_color="transparent")
        brand.pack(side="left", padx=20)
        
        brand_mark = ctk.CTkLabel(brand, text="M", font=ctk.CTkFont(size=28, weight="bold"),
                                 text_color="#c9a66b", width=40, height=40,
                                 fg_color="#2a2a2a", corner_radius=8)
        brand_mark.pack(side="left")
        
        brand_text = ctk.CTkFrame(brand, fg_color="transparent")
        brand_text.pack(side="left", padx=(12, 0))
        ctk.CTkLabel(brand_text, text="Mwarokin Estates", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(brand_text, text="Facility Ledger", font=ctk.CTkFont(size=12), text_color="gray").pack(anchor="w")
        
        # Nav Links
        nav_links = ctk.CTkFrame(self.nav, fg_color="transparent")
        nav_links.pack(side="left", padx=40)
        
        links = ["Overview", "Bills", "Payments", "Amenities", "Contact"]
        for i, link in enumerate(links):
            btn = ctk.CTkButton(nav_links, text=link, width=100, height=32,
                               fg_color="#2a2a2a" if link == "Amenities" else "transparent",
                               hover_color="#3a3a3a", border_width=0, corner_radius=6)
            btn.pack(side="left", padx=4)
        
        # Unit Info
        unit_frame = ctk.CTkFrame(self.nav, fg_color="#2a2a2a", corner_radius=20)
        unit_frame.pack(side="right", padx=20)
        ctk.CTkLabel(unit_frame, text="●", text_color="#4ade80", font=ctk.CTkFont(size=12)).pack(side="left", padx=(12,4))
        ctk.CTkLabel(unit_frame, text="Unit B-14", font=ctk.CTkFont(size=14)).pack(side="left", padx=(0,8))
        ctk.CTkLabel(unit_frame, text="Active Resident", text_color="gray", font=ctk.CTkFont(size=12)).pack(side="left")
        
        # Main Content
        self.main_content = ctk.CTkScrollableFrame(self, fg_color="#111111")
        self.main_content.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.main_content.grid_columnconfigure(0, weight=1)
        
        # Hero
        self.create_hero()
        
        # Facility Board
        self.create_facility_board()
        
        # Ledger
        self.create_ledger_section()
        
        # Footer (simplified)
        footer = ctk.CTkFrame(self, height=80, fg_color="#0a0a0a", corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew")
        ctk.CTkLabel(footer, text="Mwarokin Estates — The Amenities Ledger © 2026 | Powered by Syllogism Technology Africa",
                    text_color="gray", font=ctk.CTkFont(size=11)).pack(pady=20)
    
    def create_hero(self):
        hero = ctk.CTkFrame(self.main_content, fg_color="#1a1a1a", height=260, corner_radius=0)
        hero.pack(fill="x", padx=0, pady=0)
        hero.grid_columnconfigure(0, weight=1)
        
        # Eyebrow
        eyebrow = ctk.CTkFrame(hero, fg_color="transparent")
        eyebrow.pack(pady=(30,10), padx=60)
        ctk.CTkLabel(eyebrow, text="Facility Directory — Block B, Mwarokin Estates", 
                    text_color="#c9a66b", font=ctk.CTkFont(size=13, weight="bold")).pack()
        
        # Title
        title = ctk.CTkLabel(hero, text="Every amenity, booked, tracked\nand accounted for.",
                           font=ctk.CTkFont(size=42, weight="bold"), justify="center", text_color="white")
        title.pack(pady=(10, 16))
        
        # Lede
        lede = ctk.CTkLabel(hero, text="This is the live register of estate facilities available to your unit — reserve a slot,\ncheck real-time status, or report an issue directly to the estate office.",
                           font=ctk.CTkFont(size=15), text_color="gray", justify="center")
        lede.pack(pady=(0, 30))
        
        # Status Strip
        status_frame = ctk.CTkFrame(hero, fg_color="#222222", height=90, corner_radius=12)
        status_frame.pack(pady=10, padx=60, fill="x")
        status_frame.grid_columnconfigure((0,1,2,3), weight=1)
        
        statuses = [
            ("Facilities Open", "9", "/ 10"),
            ("Your Active Bookings", str(self.booking_count), ""),
            ("Estate Status", "Normal", "●"),
            ("Ledger Entries Today", str(len(self.ledger)), "")
        ]
        
        self.stat_labels = []
        for i, (label, val, suffix) in enumerate(statuses):
            cell = ctk.CTkFrame(status_frame, fg_color="transparent")
            cell.grid(row=0, column=i, padx=20, pady=12, sticky="nsew")
            
            ctk.CTkLabel(cell, text=label, text_color="gray", font=ctk.CTkFont(size=12)).pack()
            
            if i == 2:
                val_frame = ctk.CTkFrame(cell, fg_color="transparent")
                val_frame.pack()
                ctk.CTkLabel(val_frame, text="●", text_color="#4ade80", font=ctk.CTkFont(size=18)).pack(side="left")
                ctk.CTkLabel(val_frame, text="Normal", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=(4,0))
            else:
                val_lbl = ctk.CTkLabel(cell, text=val + suffix, font=ctk.CTkFont(size=22, weight="bold"))
                val_lbl.pack()
                self.stat_labels.append(val_lbl)
    
    def create_facility_board(self):
        board_section = ctk.CTkFrame(self.main_content, fg_color="transparent")
        board_section.pack(fill="x", padx=60, pady=40)
        
        ctk.CTkLabel(board_section, text="The Facility Board", font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(board_section, text="Bay numbers correspond to the estate office registry. Select, reserve, or flag.",
                    text_color="gray").pack(anchor="w", pady=(0,20))
        
        # Grid for bays
        self.bays_frame = ctk.CTkFrame(board_section, fg_color="transparent")
        self.bays_frame.pack(fill="x")
        self.bays_frame.grid_columnconfigure((0,1,2), weight=1, uniform="bay")
        
        self.create_bays()
    
    def create_bays(self):
        bays_data = [
            {"id": "01", "name": "Resident Parking", "icon": "🚗", "color": "#4ade80"},
            {"id": "02", "name": "Swimming Pool", "icon": "🏊", "color": "#60a5fa"},
            {"id": "03", "name": "Fitness Room", "icon": "🏋️", "color": "#f59e0b"},
            {"id": "04", "name": "Perimeter Security", "icon": "🛡️", "color": "#8b5cf6"},
            {"id": "05", "name": "Standby Generator", "icon": "⚡", "color": "#eab308"},
            {"id": "06", "name": "Water Backup", "icon": "💧", "color": "#22d3ee"},
            {"id": "07", "name": "Estate Wi-Fi", "icon": "📶", "color": "#a3e635"},
            {"id": "08", "name": "Community Hall", "icon": "🏛️", "color": "#c084fc"},
            {"id": "09", "name": "Children's Play Area", "icon": "🧒", "color": "#f472b6"},
            {"id": "10", "name": "Landscaped Gardens", "icon": "🌱", "color": "#4ade80"}
        ]
        
        self.bay_frames = []
        row = 0
        col = 0
        
        for bay in bays_data:
            frame = ctk.CTkFrame(self.bays_frame, fg_color="#1f1f1f", corner_radius=12)
            frame.grid(row=row, column=col, padx=8, pady=12, sticky="nsew")
            
            # Header
            header = ctk.CTkFrame(frame, fg_color="transparent")
            header.pack(fill="x", padx=16, pady=(16,8))
            
            ctk.CTkLabel(header, text=f"BAY / {bay['id']}", text_color="#c9a66b",
                        font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
            ctk.CTkLabel(header, text=bay['name'], font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
            
            # Icon
            icon_lbl = ctk.CTkLabel(header, text=bay['icon'], font=ctk.CTkFont(size=42))
            icon_lbl.pack(side="right", anchor="ne")
            
            # Status
            status = ctk.CTkLabel(frame, text="Open", text_color="#4ade80", font=ctk.CTkFont(size=14))
            status.pack(padx=16, anchor="w")
            
            # Form area (simplified per bay)
            form = ctk.CTkFrame(frame, fg_color="transparent")
            form.pack(fill="x", padx=16, pady=12)
            
            self.setup_bay_form(form, bay['id'], bay['name'])
            
            self.bay_frames.append(frame)
            
            col += 1
            if col > 2:
                col = 0
                row += 1
    
    def setup_bay_form(self, parent, bay_id, name):
        if bay_id == "01":  # Parking
            ctk.CTkLabel(parent, text="Bay Type", font=ctk.CTkFont(size=12)).pack(anchor="w")
            type_combo = ctk.CTkComboBox(parent, values=["Visitor Bay", "Resident Bay (2nd Car)", "Disability Bay"])
            type_combo.pack(fill="x", pady=(0,8))
            
            ctk.CTkLabel(parent, text="Date", font=ctk.CTkFont(size=12)).pack(anchor="w")
            date_entry = ctk.CTkEntry(parent, placeholder_text="Today")
            date_entry.pack(fill="x", pady=(0,8))
            
            ctk.CTkLabel(parent, text="Vehicle Reg. Plate", font=ctk.CTkFont(size=12)).pack(anchor="w")
            plate_entry = ctk.CTkEntry(parent, placeholder_text="KDA 001B")
            plate_entry.pack(fill="x", pady=(0,12))
            
            btn = ctk.CTkButton(parent, text="Reserve Bay", command=lambda: self.reserve_parking(type_combo, date_entry, plate_entry))
            btn.pack(fill="x", pady=4)
            
        elif bay_id == "02":  # Pool
            ctk.CTkLabel(parent, text="Available Slots", font=ctk.CTkFont(size=12)).pack(anchor="w")
            # Simple slot buttons simulation
            slots_frame = ctk.CTkFrame(parent, fg_color="transparent")
            slots_frame.pack(fill="x", pady=8)
            # Could be expanded with actual buttons
            btn = ctk.CTkButton(parent, text="Book Lap Lane", command=lambda: self.book_pool())
            btn.pack(fill="x")
            
        elif bay_id == "03":  # Gym
            ctk.CTkLabel(parent, text="Time Window", font=ctk.CTkFont(size=12)).pack(anchor="w")
            slot_combo = ctk.CTkComboBox(parent, values=["06:00 – 07:00", "07:00 – 08:00", "17:00 – 18:00"])
            slot_combo.pack(fill="x", pady=(0,8))
            
            btn = ctk.CTkButton(parent, text="Reserve Window", command=lambda: self.book_gym(slot_combo))
            btn.pack(fill="x", pady=4)
            
        elif bay_id == "04":
            btn = ctk.CTkButton(parent, text="Issue Visitor Pass", command=lambda: self.issue_pass())
            btn.pack(fill="x", pady=4)
            
        else:
            # Generic report button for others
            btn_text = "Report Issue" if bay_id in ["05","06","09","10"] else "Book / Check"
            btn = ctk.CTkButton(parent, text=btn_text, command=lambda b=bay_id: self.generic_action(b, name))
            btn.pack(fill="x", pady=8)
    
    def update_stats(self):
        if hasattr(self, 'stat_labels') and len(self.stat_labels) > 0:
            try:
                self.stat_labels[0].configure(text="9 / 10")
                self.stat_labels[1].configure(text=str(self.booking_count))
                self.stat_labels[3].configure(text=str(len(self.ledger)))
            except:
                pass
    
    def show_toast(self, message, is_error=False):
        toast = ctk.CTkToplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        
        color = "#ef4444" if is_error else "#c9a66b"
        frame = ctk.CTkFrame(toast, fg_color="#1f1f1f", border_color=color, border_width=1)
        frame.pack(padx=10, pady=10)
        
        ctk.CTkLabel(frame, text="●" if not is_error else "⚠", text_color=color, font=ctk.CTkFont(size=16)).pack(side="left", padx=8)
        ctk.CTkLabel(frame, text=message, text_color="white").pack(side="left", padx=(0,16), pady=8)
        
        x = self.winfo_x() + self.winfo_width() - 340
        y = self.winfo_y() + 80
        toast.geometry(f"+{x}+{y}")
        
        def fade():
            time.sleep(3.2)
            toast.destroy()
        
        threading.Thread(target=fade, daemon=True).start()
    
    def log_entry(self, bay, entry, status="Confirmed"):
        timestamp = datetime.now().strftime("%H:%M")
        self.ledger.insert(0, {
            "bay": bay,
            "entry": entry,
            "status": status,
            "time": timestamp
        })
        self.ledger = self.ledger[:30]
        self.booking_count += 1
        self.save_data()
        self.update_stats()
        self.refresh_ledger()
        self.show_toast(f"{bay} - {entry[:40]}")
    
    def refresh_ledger(self):
        if hasattr(self, 'ledger_tree'):
            for item in self.ledger_tree.get_children():
                self.ledger_tree.delete(item)
            
            for entry in self.ledger:
                tag = "confirmed" if entry["status"] == "Confirmed" else "pending"
                self.ledger_tree.insert("", 0, values=(
                    entry["bay"], 
                    entry["entry"][:45] + ("..." if len(entry["entry"]) > 45 else ""),
                    entry["status"],
                    entry["time"]
                ), tags=(tag,))
    
    def create_ledger_section(self):
        ledger_section = ctk.CTkFrame(self.main_content, fg_color="transparent")
        ledger_section.pack(fill="x", padx=60, pady=(10,40))
        
        ctk.CTkLabel(ledger_section, text="Your Household Ledger", font=ctk.CTkFont(size=26, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(ledger_section, text="Every booking and report is recorded here.", 
                    text_color="gray").pack(anchor="w", pady=(0,12))
        
        # Table
        columns = ("Bay", "Entry", "Status", "Time")
        self.ledger_tree = ttk.Treeview(ledger_section, columns=columns, show="headings", height=8)
        
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#1f1f1f", foreground="white", fieldbackground="#1f1f1f")
        style.configure("Treeview.Heading", background="#2a2a2a", foreground="#c9a66b")
        
        for col in columns:
            self.ledger_tree.heading(col, text=col)
            self.ledger_tree.column(col, width=180)
        
        self.ledger_tree.pack(fill="x", pady=8)
        
        # Emergency
        emer_frame = ctk.CTkFrame(ledger_section, fg_color="#450a0a", corner_radius=12)
        emer_frame.pack(fill="x", pady=20)
        
        inner = ctk.CTkFrame(emer_frame, fg_color="transparent")
        inner.pack(padx=20, pady=16, fill="x")
        
        ctk.CTkLabel(inner, text="⚠ Estate Emergency Line", text_color="#f87171", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(inner, text="For fire, medical, or security emergencies — call directly", 
                    text_color="#fda4af").pack(anchor="w")
        
        ctk.CTkButton(inner, text="+254 704 919 388", fg_color="#b91c1c", hover_color="#991b1b",
                     command=lambda: messagebox.showinfo("Calling", "Connecting to duty office...")).pack(pady=(12,0))
        
        self.refresh_ledger()
    
    # Action Handlers
    def reserve_parking(self, type_combo, date_entry, plate_entry):
        plate = plate_entry.get().strip()
        if not plate:
            self.show_toast("Enter vehicle registration plate", True)
            return
        bay_type = type_combo.get()
        self.log_entry("BAY-01", f"{bay_type} for {plate.upper()}")
        plate_entry.delete(0, tk.END)
        self.show_toast("Parking bay reserved successfully")
    
    def book_pool(self):
        self.log_entry("BAY-02", "Lap lane booked")
        self.show_toast("Pool slot booked")
    
    def book_gym(self, slot_combo):
        slot = slot_combo.get()
        self.log_entry("BAY-03", f"Fitness window {slot}")
        self.show_toast("Gym window reserved")
    
    def issue_pass(self):
        self.log_entry("BAY-04", "Visitor pass issued")
        self.show_toast("Visitor pass issued")
    
    def generic_action(self, bay_id, name):
        self.log_entry(f"BAY-{bay_id}", f"Action performed on {name}")
        self.show_toast(f"{name} request submitted")
    
    def run(self):
        self.mainloop()


if __name__ == "__main__":
    # pip install customtkinter
    app = MwarokinEstatesApp()
    app.run()
```