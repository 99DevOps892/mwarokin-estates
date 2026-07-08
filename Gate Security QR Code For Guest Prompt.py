```python
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import qrcode
import json
import os
from datetime import datetime
import threading
import time

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class Guest:
    def __init__(self, id, name, email, phone, host, status, qr_data):
        self.id = id
        self.name = name
        self.email = email
        self.phone = phone
        self.host = host
        self.status = status
        self.qr_data = qr_data

class MwarokinGateApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Mwarokin Estates - Gate Security")
        self.geometry("1280x720")
        self.minsize(1024, 650)

        # Data
        self.guests = []
        self.next_id = 1
        self.current_filter = "all"
        self.load_sample_data()

        # UI Setup
        self.setup_ui()
        self.render_table()

    def load_sample_data(self):
        sample_data = [
            {"name": "Sarah Wanjiku", "email": "sarah.w@example.com", "phone": "+254 712 345 678", "host": "B4, Mr. Ochieng", "status": "checked-in", "qr": "MWK-1001"},
            {"name": "Michael Odhiambo", "email": "michael.o@example.com", "phone": "+254 723 456 789", "host": "A7, Ms. Akinyi", "status": "pending", "qr": "MWK-1002"},
            {"name": "Grace Auma", "email": "grace.a@example.com", "phone": "+254 734 567 890", "host": "C12, Dr. Mwangi", "status": "checked-out", "qr": "MWK-1003"},
            {"name": "David Kamau", "email": "david.k@example.com", "phone": "+254 745 678 901", "host": "D3, Mr. Kiprop", "status": "pending", "qr": "MWK-1004"},
            {"name": "Faith Nyambura", "email": "faith.n@example.com", "phone": "+254 756 789 012", "host": "E9, Mrs. Njoroge", "status": "checked-in", "qr": "MWK-1005"},
            {"name": "Peter Ochieng", "email": "peter.o@example.com", "phone": "+254 767 890 123", "host": "F2, Mr. Otieno", "status": "blocked", "qr": "MWK-1006"},
        ]
        for data in sample_data:
            g = Guest(self.next_id, data["name"], data["email"], data["phone"], data["host"], data["status"], data["qr"])
            self.guests.append(g)
            self.next_id += 1

    def setup_ui(self):
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=260, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Brand
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(pady=20, padx=20, fill="x")
        
        logo = ctk.CTkLabel(brand_frame, text="M", font=ctk.CTkFont(size=32, weight="bold"), 
                           text_color="#3b82f6", width=50, height=50, corner_radius=12, fg_color="#1e2937")
        logo.pack(side="left")
        
        brand_text = ctk.CTkLabel(brand_frame, text="Mwarokin\nEstates", font=ctk.CTkFont(size=18, weight="bold"),
                                 justify="left", anchor="w")
        brand_text.pack(side="left", padx=12)

        # Navigation
        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", padx=16, pady=10)

        ctk.CTkLabel(nav_frame, text="MAIN", text_color="#94a3b8", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=8, pady=(16,8))

        self.nav_buttons = {}
        nav_items = [
            ("Gate Security", "qrcode", True),
            ("All Guests", "users"),
            ("Check-ins", "clock"),
            ("Schedule", "calendar"),
        ]
        for text, icon, active in nav_items:
            btn = ctk.CTkButton(nav_frame, text=text, height=40, anchor="w", 
                               font=ctk.CTkFont(size=14), fg_color="#1e2937" if active else "transparent",
                               hover_color="#334155", corner_radius=8)
            btn.pack(fill="x", padx=8, pady=2)
            self.nav_buttons[text] = btn

        ctk.CTkLabel(nav_frame, text="SETTINGS", text_color="#94a3b8", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=8, pady=(24,8))

        for text, icon in [("Preferences", "cog"), ("Security Log", "shield")]:
            btn = ctk.CTkButton(nav_frame, text=text, height=40, anchor="w", 
                               font=ctk.CTkFont(size=14), fg_color="transparent", hover_color="#334155", corner_radius=8)
            btn.pack(fill="x", padx=8, pady=2)

        # User footer
        user_frame = ctk.CTkFrame(self.sidebar, fg_color="#1e2937", height=80, corner_radius=12)
        user_frame.pack(side="bottom", fill="x", padx=16, pady=20)
        
        avatar = ctk.CTkLabel(user_frame, text="JD", font=ctk.CTkFont(size=18, weight="bold"),
                             width=40, height=40, corner_radius=20, fg_color="#3b82f6")
        avatar.pack(side="left", padx=12)
        
        user_info = ctk.CTkFrame(user_frame, fg_color="transparent")
        user_info.pack(side="left", fill="x")
        ctk.CTkLabel(user_info, text="James Duncan", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(user_info, text="Security Admin", text_color="#94a3b8", font=ctk.CTkFont(size=12)).pack(anchor="w")

        # Main Content
        self.main_content = ctk.CTkFrame(self, fg_color="#0f172a")
        self.main_content.pack(side="right", fill="both", expand=True)

        # Header
        header = ctk.CTkFrame(self.main_content, height=80, fg_color="#1e2937", corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Toggle + Title
        left_header = ctk.CTkFrame(header, fg_color="transparent")
        left_header.pack(side="left", padx=20, fill="y")
        
        self.toggle_btn = ctk.CTkButton(left_header, text="☰", width=40, height=40, fg_color="transparent", 
                                       text_color="#e2e8f0", hover_color="#334155", font=ctk.CTkFont(size=20))
        self.toggle_btn.pack(side="left")
        
        title_frame = ctk.CTkFrame(left_header, fg_color="transparent")
        title_frame.pack(side="left", padx=16)
        ctk.CTkLabel(title_frame, text="Gate Security", font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Manage guest access & QR codes", 
                    text_color="#94a3b8", font=ctk.CTkFont(size=13)).pack(anchor="w")

        # Header right
        right_header = ctk.CTkFrame(header, fg_color="transparent")
        right_header.pack(side="right", padx=20)

        # Search
        self.search_var = tk.StringVar()
        search_frame = ctk.CTkFrame(right_header, fg_color="#334155", corner_radius=8, height=40)
        search_frame.pack(side="left", padx=(0,16))
        search_frame.pack_propagate(False)
        
        ctk.CTkLabel(search_frame, text="🔍", text_color="#94a3b8").pack(side="left", padx=12)
        search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search guests...", 
                                   textvariable=self.search_var, border_width=0, fg_color="transparent", 
                                   width=220, height=36)
        search_entry.pack(side="left", fill="y", padx=(0,12))
        self.search_var.trace("w", lambda *args: self.schedule_render())

        # Notifications
        notif_btn = ctk.CTkButton(right_header, text="🛎", width=40, height=40, fg_color="#334155", 
                                 hover_color="#475569", corner_radius=8)
        notif_btn.pack(side="left", padx=(0,12))

        # Add Guest
        add_btn = ctk.CTkButton(right_header, text="Add Guest", height=40, 
                               font=ctk.CTkFont(size=14, weight="bold"),
                               command=self.open_add_guest_modal)
        add_btn.pack(side="left")

        # Stats Row
        self.stats_frame = ctk.CTkFrame(self.main_content, fg_color="transparent", height=140)
        self.stats_frame.pack(fill="x", padx=24, pady=24)
        self.stats_frame.pack_propagate(False)

        self.create_stats_cards()

        # Table Area
        table_area = ctk.CTkFrame(self.main_content, fg_color="#1e2937", corner_radius=12)
        table_area.pack(fill="both", expand=True, padx=24, pady=(0,24))

        # Toolbar
        toolbar = ctk.CTkFrame(table_area, fg_color="transparent", height=60)
        toolbar.pack(fill="x", padx=20, pady=(16,8))
        
        # Filters
        filter_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        filter_frame.pack(side="left")
        
        self.filter_buttons = {}
        filters = ["All", "Checked In", "Pending", "Checked Out"]
        filter_values = ["all", "checked-in", "pending", "checked-out"]
        for i, (text, val) in enumerate(zip(filters, filter_values)):
            btn = ctk.CTkButton(filter_frame, text=text, height=32, corner_radius=20,
                               fg_color="#3b82f6" if val == "all" else "transparent",
                               text_color="white" if val == "all" else "#e2e8f0",
                               hover_color="#2563eb", command=lambda v=val: self.set_filter(v))
            btn.pack(side="left", padx=4)
            self.filter_buttons[val] = btn

        # Count and View
        right_toolbar = ctk.CTkFrame(toolbar, fg_color="transparent")
        right_toolbar.pack(side="right")
        
        self.count_label = ctk.CTkLabel(right_toolbar, text="6 guests", text_color="#94a3b8")
        self.count_label.pack(side="left", padx=20)

        # Table
        self.table_frame = ctk.CTkScrollableFrame(table_area, fg_color="#1e2937")
        self.table_frame.pack(fill="both", expand=True, padx=20, pady=(0,16))

        # Add Guest Modal
        self.add_modal = ctk.CTkToplevel(self)
        self.add_modal.title("Add New Guest")
        self.add_modal.geometry("420x520")
        self.add_modal.withdraw()
        self.add_modal.transient(self)
        self.add_modal.grab_set()

        self.setup_add_modal()

    def create_stats_cards(self):
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        stats = [
            ("Total Guests", "0", "#eab308", "users"),
            ("Checked In", "0", "#22c55e", "check-circle"),
            ("Pending", "0", "#3b82f6", "hourglass"),
            ("Checked Out", "0", "#ef4444", "sign-out-alt")
        ]

        for i, (label, value, color, icon) in enumerate(stats):
            card = ctk.CTkFrame(self.stats_frame, fg_color="#1e2937", corner_radius=12, width=260, height=110)
            card.grid(row=0, column=i, padx=8, pady=8, sticky="nsew")
            card.grid_propagate(False)

            icon_label = ctk.CTkLabel(card, text="👥" if icon=="users" else "✅" if icon=="check-circle" else "⏳" if icon=="hourglass" else "🚪",
                                     font=ctk.CTkFont(size=28), text_color=color)
            icon_label.pack(pady=(20,8))

            val_label = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=28, weight="bold"))
            val_label.pack()
            ctk.CTkLabel(card, text=label, text_color="#94a3b8", font=ctk.CTkFont(size=13)).pack()

        self.stats_frame.grid_columnconfigure((0,1,2,3), weight=1)

    def update_stats(self):
        total = len(self.guests)
        checked_in = len([g for g in self.guests if g.status == "checked-in"])
        pending = len([g for g in self.guests if g.status == "pending"])
        checked_out = len([g for g in self.guests if g.status == "checked-out"])

        # Update cards (simple refresh)
        self.create_stats_cards()  # Recreate for simplicity

    def setup_add_modal(self):
        modal = self.add_modal
        ctk.CTkLabel(modal, text="Add New Guest", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)

        self.name_entry = ctk.CTkEntry(modal, placeholder_text="Full Name", width=360, height=45)
        self.name_entry.pack(pady=8)
        
        self.email_entry = ctk.CTkEntry(modal, placeholder_text="Email Address", width=360, height=45)
        self.email_entry.pack(pady=8)
        
        phone_frame = ctk.CTkFrame(modal, fg_color="transparent", width=360)
        phone_frame.pack(pady=8)
        
        self.phone_entry = ctk.CTkEntry(phone_frame, placeholder_text="Phone Number", width=170, height=45)
        self.phone_entry.pack(side="left", padx=(0,16))
        
        self.host_entry = ctk.CTkEntry(phone_frame, placeholder_text="Host / Unit", width=170, height=45)
        self.host_entry.pack(side="left")
        
        status_frame = ctk.CTkFrame(modal, fg_color="transparent", width=360)
        status_frame.pack(pady=12)
        ctk.CTkLabel(status_frame, text="Status:").pack(anchor="w")
        
        self.status_var = tk.StringVar(value="pending")
        status_combo = ctk.CTkOptionMenu(status_frame, values=["pending", "checked-in", "checked-out", "blocked"],
                                        variable=self.status_var, width=360, height=45)
        status_combo.pack(pady=8)

        btn_frame = ctk.CTkFrame(modal, fg_color="transparent")
        btn_frame.pack(pady=20, fill="x", padx=30)
        
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="#475569", command=self.close_add_modal).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Generate QR & Add Guest", font=ctk.CTkFont(weight="bold"),
                     command=self.add_guest).pack(side="right", padx=8)

    def open_add_guest_modal(self):
        self.name_entry.delete(0, "end")
        self.email_entry.delete(0, "end")
        self.phone_entry.delete(0, "end")
        self.host_entry.delete(0, "end")
        self.add_modal.deiconify()

    def close_add_modal(self):
        self.add_modal.withdraw()

    def add_guest(self):
        name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        
        if not name or not email:
            messagebox.showerror("Error", "Name and Email are required")
            return
        
        phone = self.phone_entry.get().strip() or "—"
        host = self.host_entry.get().strip() or "—"
        status = self.status_var.get()
        
        qr_data = f"MWK-{str(self.next_id).zfill(4)}"
        
        new_guest = Guest(self.next_id, name, email, phone, host, status, qr_data)
        self.guests.append(new_guest)
        self.next_id += 1
        
        self.close_add_modal()
        self.render_table()
        self.show_toast(f"✅ {name} added successfully with QR: {qr_data}", "success")

    def set_filter(self, filter_val):
        self.current_filter = filter_val
        for val, btn in self.filter_buttons.items():
            btn.configure(fg_color="#3b82f6" if val == filter_val else "transparent",
                         text_color="white" if val == filter_val else "#e2e8f0")
        self.render_table()

    def generate_qr_image(self, data, size=120):
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0b1a2e", back_color="#ffffff")
        img = img.resize((size, size))
        return ImageTk.PhotoImage(img)

    def render_table(self):
        for widget in self.table_frame.winfo_children():
            widget.destroy()

        search_term = self.search_var.get().lower().strip()
        
        filtered = self.guests
        if self.current_filter != "all":
            filtered = [g for g in filtered if g.status == self.current_filter]
        
        if search_term:
            filtered = [g for g in filtered if 
                       search_term in g.name.lower() or 
                       search_term in g.email.lower() or 
                       search_term in g.phone.lower() or 
                       search_term in g.host.lower() or 
                       search_term in g.qr_data.lower()]

        self.count_label.configure(text=f"{len(filtered)} guest{'s' if len(filtered) != 1 else ''}")

        # Table Header
        headers = ["Guest", "Contact", "Status", "QR Code", "Actions"]
        header_frame = ctk.CTkFrame(self.table_frame, fg_color="#334155", height=40, corner_radius=8)
        header_frame.pack(fill="x", pady=(0, 4), padx=8)
        
        for i, h in enumerate(headers):
            if i == 4:
                label = ctk.CTkLabel(header_frame, text=h, width=180, anchor="e")
            else:
                label = ctk.CTkLabel(header_frame, text=h, width=220 if i==0 else 180)
            label.grid(row=0, column=i, padx=12, pady=8, sticky="w")
        header_frame.grid_columnconfigure((0,1,2,3,4), weight=1)

        # Rows
        for guest in filtered:
            row = ctk.CTkFrame(self.table_frame, fg_color="#1e2937", height=68, corner_radius=8)
            row.pack(fill="x", pady=4, padx=8)
            row.pack_propagate(False)

            # Guest Info
            guest_frame = ctk.CTkFrame(row, fg_color="transparent")
            guest_frame.grid(row=0, column=0, sticky="w", padx=12)
            
            initials = "".join([w[0].upper() for w in guest.name.split()[:2]])
            avatar = ctk.CTkLabel(guest_frame, text=initials, width=42, height=42, 
                                 corner_radius=21, fg_color="#3b82f6", font=ctk.CTkFont(weight="bold"))
            avatar.pack(side="left")
            
            info = ctk.CTkFrame(guest_frame, fg_color="transparent")
            info.pack(side="left", padx=12)
            ctk.CTkLabel(info, text=guest.name, font=ctk.CTkFont(weight="bold")).pack(anchor="w")
            ctk.CTkLabel(info, text=guest.host, text_color="#94a3b8", font=ctk.CTkFont(size=12)).pack(anchor="w")

            # Contact
            contact_frame = ctk.CTkFrame(row, fg_color="transparent")
            contact_frame.grid(row=0, column=1, sticky="w", padx=12)
            ctk.CTkLabel(contact_frame, text=guest.email, font=ctk.CTkFont(size=13)).pack(anchor="w")
            ctk.CTkLabel(contact_frame, text=guest.phone, text_color="#94a3b8", font=ctk.CTkFont(size=12)).pack(anchor="w")

            # Status
            status_colors = {
                "checked-in": "#22c55e",
                "pending": "#eab308",
                "checked-out": "#ef4444",
                "blocked": "#f87171"
            }
            status_color = status_colors.get(guest.status, "#94a3b8")
            status_frame = ctk.CTkFrame(row, fg_color="transparent")
            status_frame.grid(row=0, column=2, padx=12)
            
            status_label = ctk.CTkLabel(status_frame, text=guest.status.replace("-", " ").title(), 
                                       text_color=status_color, font=ctk.CTkFont(size=13, weight="medium"))
            status_label.pack()

            # QR Preview
            qr_frame = ctk.CTkFrame(row, fg_color="#ffffff", width=52, height=52, corner_radius=6)
            qr_frame.grid(row=0, column=3, padx=12)
            qr_img = self.generate_qr_image(guest.qr_data, size=48)
            qr_label = ctk.CTkLabel(qr_frame, image=qr_img, text="")
            qr_label.image = qr_img
            qr_label.pack()
            qr_label.bind("<Button-1>", lambda e, gid=guest.id: self.show_qr_detail(gid))

            # Actions
            action_frame = ctk.CTkFrame(row, fg_color="transparent")
            action_frame.grid(row=0, column=4, sticky="e", padx=12)

            if guest.status == "pending":
                ctk.CTkButton(action_frame, text="Check In", width=90, height=32, fg_color="#22c55e",
                             command=lambda gid=guest.id: self.check_in(gid)).pack(side="left", padx=4)
            
            if guest.status == "checked-in":
                ctk.CTkButton(action_frame, text="Check Out", width=90, height=32, fg_color="#ef4444",
                             command=lambda gid=guest.id: self.check_out(gid)).pack(side="left", padx=4)

            ctk.CTkButton(action_frame, text="🔍", width=32, height=32, fg_color="#475569",
                         command=lambda gid=guest.id: self.show_qr_detail(gid)).pack(side="left", padx=4)
            
            ctk.CTkButton(action_frame, text="🗑", width=32, height=32, fg_color="#f87171",
                         command=lambda gid=guest.id: self.delete_guest(gid)).pack(side="left", padx=4)

            row.grid_columnconfigure((0,1,2,3,4), weight=1)

        self.update_stats()

    def schedule_render(self):
        if hasattr(self, '_render_after'):
            self.after_cancel(self._render_after)
        self._render_after = self.after(300, self.render_table)

    def check_in(self, guest_id):
        guest = next((g for g in self.guests if g.id == guest_id), None)
        if guest:
            guest.status = "checked-in"
            self.show_toast(f"✅ {guest.name} checked in", "success")
            self.render_table()

    def check_out(self, guest_id):
        guest = next((g for g in self.guests if g.id == guest_id), None)
        if guest:
            guest.status = "checked-out"
            self.show_toast(f"🚪 {guest.name} checked out", "info")
            self.render_table()

    def delete_guest(self, guest_id):
        if messagebox.askyesno("Confirm", "Remove this guest?"):
            self.guests = [g for g in self.guests if g.id != guest_id]
            self.render_table()
            self.show_toast("Guest removed", "error")

    def show_qr_detail(self, guest_id):
        guest = next((g for g in self.guests if g.id == guest_id), None)
        if not guest:
            return

        detail_win = ctk.CTkToplevel(self)
        detail_win.title(f"QR - {guest.name}")
        detail_win.geometry("420x520")
        detail_win.transient(self)

        ctk.CTkLabel(detail_win, text=guest.name, font=ctk.CTkFont(size=18, weight="bold")).pack(pady=12)
        ctk.CTkLabel(detail_win, text=f"{guest.email} • {guest.host}", text_color="#94a3b8").pack(pady=(0,20))

        qr_big = ctk.CTkFrame(detail_win, fg_color="#ffffff", width=220, height=220, corner_radius=12)
        qr_big.pack(pady=20)
        
        qr_img = self.generate_qr_image(guest.qr_data, size=200)
        qr_label = ctk.CTkLabel(qr_big, image=qr_img, text="")
        qr_label.image = qr_img
        qr_label.pack(pady=10)

        ctk.CTkButton(detail_win, text="📥 Download QR Code", height=45, font=ctk.CTkFont(weight="bold"),
                     command=lambda: self.download_qr(guest)).pack(pady=20)

    def download_qr(self, guest):
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(guest.qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0b1a2e", back_color="#ffffff")
        
        filename = f"QR_{guest.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.png"
        save_path = filedialog.asksaveasfilename(defaultextension=".png", initialfile=filename,
                                                filetypes=[("PNG files", "*.png")])
        if save_path:
            img.save(save_path)
            self.show_toast("QR Code downloaded successfully!", "success")

    def show_toast(self, message, toast_type="success"):
        toast = ctk.CTkToplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        
        color = "#22c55e" if toast_type == "success" else "#3b82f6" if toast_type == "info" else "#ef4444"
        
        frame = ctk.CTkFrame(toast, fg_color="#1e2937", corner_radius=8, border_width=1, border_color=color)
        frame.pack(padx=10, pady=10)
        
        ctk.CTkLabel(frame, text=message, text_color="white").pack(padx=20, pady=12)
        
        x = self.winfo_x() + self.winfo_width() - 320
        y = self.winfo_y() + self.winfo_height() - 100
        toast.geometry(f"+{x}+{y}")
        
        def close_toast():
            toast.destroy()
        
        toast.after(2800, close_toast)

if __name__ == "__main__":
    app = MwarokinGateApp()
    app.mainloop()
```