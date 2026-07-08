```python:disable-run
import sys
import json
import datetime
from pathlib import Path
from tkinter import messagebox, ttk
import customtkinter as ctk
from PIL import Image, ImageTk
import requests
from io import BytesIO

# Set appearance
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class MwarokinRentApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Mwarokin Estates - Rent Penalties & Payment")
        self.geometry("1280x780")
        self.minsize(1100, 700)

        # Data
        self.rent_amount = 1250.0
        self.last_payment_month = "2025-07"  # YYYY-MM
        self.data_file = Path.home() / ".mwarokin_rent.json"

        self.load_data()

        # Constants
        self.DUE_DAY = 5
        self.GRACE_DAYS = 3
        self.FLAT_PENALTY = 0.05
        self.DAILY_PENALTY = 0.005

        self.setup_ui()
        self.update_all_ui()

    def load_data(self):
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.rent_amount = data.get('rent_amount', 1250.0)
                    self.last_payment_month = data.get('last_payment_month', "2025-07")
            except:
                pass

    def save_data(self):
        try:
            data = {
                'rent_amount': self.rent_amount,
                'last_payment_month': self.last_payment_month
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except:
            pass

    def get_current_month_key(self):
        now = datetime.datetime.now()
        return f"{now.year}-{now.month:02d}"

    def get_current_month_display(self):
        now = datetime.datetime.now()
        return now.strftime("%B %Y")

    def get_overdue_days(self):
        today = datetime.date.today()
        year = today.year
        month = today.month

        due_date = datetime.date(year, month, self.DUE_DAY)
        grace_end = datetime.date(year, month, self.DUE_DAY + self.GRACE_DAYS)

        if today <= grace_end:
            return 0

        delta = today - grace_end
        return max(delta.days, 0)

    def is_current_month_paid(self):
        return self.last_payment_month == self.get_current_month_key()

    def compute_penalties(self):
        if self.is_current_month_paid():
            return {"flat": 0.0, "daily": 0.0, "total": 0.0, "days": 0}

        days = self.get_overdue_days()
        if days <= 0:
            return {"flat": 0.0, "daily": 0.0, "total": 0.0, "days": 0}

        flat = self.rent_amount * self.FLAT_PENALTY
        daily = self.rent_amount * self.DAILY_PENALTY * days
        total = flat + daily
        return {"flat": flat, "daily": daily, "total": total, "days": days}

    def setup_ui(self):
        # Top Nav
        top_frame = ctk.CTkFrame(self, height=70, fg_color="white", corner_radius=0)
        top_frame.pack(fill="x", side="top")
        top_frame.pack_propagate(False)

        title = ctk.CTkLabel(top_frame, text="🏡 Mwarokin Estates · My Profile",
                             font=ctk.CTkFont(size=20, weight="bold"),
                             text_color="#1E3A5F")
        title.pack(side="left", padx=30)

        right_nav = ctk.CTkFrame(top_frame, fg_color="transparent")
        right_nav.pack(side="right", padx=30)

        ctk.CTkButton(right_nav, text="🔔", width=45, height=45, corner_radius=50,
                      fg_color="transparent", hover_color="#EEF2FF", text_color="#2C3E66",
                      font=ctk.CTkFont(size=22)).pack(side="left", padx=5)
        ctk.CTkButton(right_nav, text="👁", width=45, height=45, corner_radius=50,
                      fg_color="transparent", hover_color="#EEF2FF", text_color="#2C3E66",
                      font=ctk.CTkFont(size=22)).pack(side="left", padx=5)

        self.save_btn = ctk.CTkButton(right_nav, text="Save changes", width=140,
                                      height=42, corner_radius=30, fg_color="#1E3A5F",
                                      hover_color="#0F2B46", font=ctk.CTkFont(weight="600"))
        self.save_btn.pack(side="left", padx=10)
        self.save_btn.configure(command=self.save_profile)

        # Main Content
        main_container = ctk.CTkFrame(self, fg_color="#F4F7FC")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Profile Header
        profile_frame = ctk.CTkFrame(main_container, fg_color="white", corner_radius=28,
                                     height=220, border_width=1, border_color="#EDF2F7")
        profile_frame.pack(fill="x", padx=10, pady=(0, 25))
        profile_frame.pack_propagate(False)

        # Cover
        cover_frame = ctk.CTkFrame(profile_frame, height=140, fg_color="transparent", corner_radius=28)
        cover_frame.pack(fill="x")
        cover_frame.pack_propagate(False)

        try:
            response = requests.get("https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=1200&q=60", timeout=5)
            img = Image.open(BytesIO(response.content)).resize((1200, 140))
            self.cover_photo = ctk.CTkImage(light_image=img, size=(1200, 140))
            cover_label = ctk.CTkLabel(cover_frame, image=self.cover_photo, text="")
            cover_label.pack(fill="both", expand=True)
        except:
            cover_label = ctk.CTkLabel(cover_frame, text="Mwarokin Estates", fg_color="#1E3A5F",
                                       text_color="white", font=ctk.CTkFont(size=24, weight="bold"))
            cover_label.pack(fill="both", expand=True)

        # Profile Identity
        identity_frame = ctk.CTkFrame(profile_frame, fg_color="transparent")
        identity_frame.pack(fill="x", padx=30, pady=(0, 20))

        # Avatar
        avatar_frame = ctk.CTkFrame(identity_frame, fg_color="transparent", width=110, height=110)
        avatar_frame.pack(side="left", padx=(0, 25))

        avatar = ctk.CTkLabel(avatar_frame, text="RM", font=ctk.CTkFont(size=48, weight="bold"),
                              text_color="white", fg_color="#1E3A5F", width=100, height=100,
                              corner_radius=50)
        avatar.pack()
        ctk.CTkLabel(avatar_frame, text="", width=22, height=22, fg_color="#2ECC71",
                     corner_radius=50).place(x=78, y=78)

        # Info
        info_frame = ctk.CTkFrame(identity_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True)

        name_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        name_frame.pack(anchor="w")
        ctk.CTkLabel(name_frame, text="Robin Mwarema", font=ctk.CTkFont(size=26, weight="bold"),
                     text_color="#1E293B").pack(side="left")
        ctk.CTkLabel(name_frame, text="Verified", fg_color="#EEF2FF", text_color="#2563EB",
                     corner_radius=20, padx=12, pady=4, font=ctk.CTkFont(size=13, weight="600")).pack(side="left", padx=12)

        ctk.CTkLabel(info_frame, text="@robin.mwarema · Tenant since Jan 2024",
                     text_color="#4B5563", font=ctk.CTkFont(size=15)).pack(anchor="w", pady=4)

        meta = ctk.CTkFrame(info_frame, fg_color="transparent")
        meta.pack(anchor="w", pady=8)
        for meta_text in ["📍 Nairobi, Kenya", "📅 Joined 18 months ago", "⭐ 4.8 tenant rating", "⏱ Responds in ~2 hrs"]:
            ctk.CTkLabel(meta, text=meta_text, fg_color="#F1F5F9", text_color="#1E293B",
                         corner_radius=30, padx=14, pady=6, font=ctk.CTkFont(size=13)).pack(side="left", padx=4)

        # Actions
        actions_frame = ctk.CTkFrame(identity_frame, fg_color="transparent")
        actions_frame.pack(side="right")
        ctk.CTkButton(actions_frame, text="Share", width=110, height=42, corner_radius=30,
                      border_width=1, fg_color="white", text_color="#1E3A5F", border_color="#CBD5E1",
                      command=self.copy_link).pack(side="left", padx=6)
        ctk.CTkButton(actions_frame, text="Edit profile", width=130, height=42, corner_radius=30,
                      border_width=1, fg_color="#F8FAFC", text_color="#1E3A5F", border_color="#CBD5E1",
                      command=lambda: messagebox.showinfo("Demo", "Edit profile opened")).pack(side="left", padx=6)

        # Main Grid
        content = ctk.CTkFrame(main_container, fg_color="transparent")
        content.pack(fill="both", expand=True)

        content.grid_columnconfigure(0, weight=2)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        # Left Column
        left_col = ctk.CTkFrame(content, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 15))

        # Rent Center Card
        rent_card = ctk.CTkFrame(left_col, fg_color="white", corner_radius=28, border_width=1, border_color="#EDF2F7")
        rent_card.pack(fill="x", pady=(0, 25))

        # Header
        header = ctk.CTkFrame(rent_card, fg_color="transparent")
        header.pack(fill="x", padx=32, pady=(28, 16))
        ctk.CTkLabel(header, text="Rent & Penalty Center", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color="#1F2937").pack(anchor="w")
        ctk.CTkLabel(header, text="5% flat + 0.5% daily after 3-day grace", text_color="#6B7280",
                     font=ctk.CTkFont(size=14)).pack(anchor="w")

        month_label = ctk.CTkLabel(header, text=self.get_current_month_display(),
                                   font=ctk.CTkFont(size=14, weight="600"), text_color="#1E40AF",
                                   fg_color="#DBEAFE", corner_radius=999, padx=16, pady=6)
        month_label.pack(anchor="e")

        # Rent Input
        rent_row = ctk.CTkFrame(rent_card, fg_color="transparent")
        rent_row.pack(fill="x", padx=32, pady=10)

        ctk.CTkLabel(rent_row, text="Monthly rent (USD)", font=ctk.CTkFont(size=13, weight="600"),
                     text_color="#6B7280").pack(anchor="w")

        rent_input_frame = ctk.CTkFrame(rent_row, fg_color="transparent")
        rent_input_frame.pack(anchor="w", pady=8)

        ctk.CTkLabel(rent_input_frame, text="$", font=ctk.CTkFont(size=42, weight="bold"),
                     text_color="#1E3A5F").pack(side="left")
        self.rent_entry = ctk.CTkEntry(rent_input_frame, font=ctk.CTkFont(size=42, weight="bold"),
                                       width=180, border_width=0, fg_color="transparent",
                                       text_color="#1E3A5F")
        self.rent_entry.pack(side="left", padx=8)
        self.rent_entry.bind("<Return>", lambda e: self.update_rent())

        # Due info
        ctk.CTkLabel(rent_row, text="Due date: 5th of each month\nGrace period: until 8th",
                     text_color="#9CA3AF", font=ctk.CTkFont(size=13), justify="right").pack(side="right", anchor="e")

        # Penalty Breakdown
        penalty_frame = ctk.CTkFrame(rent_card, fg_color="#F8FAFC", corner_radius=20)
        penalty_frame.pack(fill="x", padx=32, pady=20)

        top_penalty = ctk.CTkFrame(penalty_frame, fg_color="transparent")
        top_penalty.pack(fill="x", padx=24, pady=20)

        left_p = ctk.CTkFrame(top_penalty, fg_color="transparent")
        left_p.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(left_p, text="Payment status", text_color="#6B7280").pack(anchor="w")
        self.status_label = ctk.CTkLabel(left_p, text="", font=ctk.CTkFont(size=16, weight="600"),
                                         corner_radius=999, padx=16, pady=6)
        self.status_label.pack(anchor="w", pady=8)

        right_p = ctk.CTkFrame(top_penalty, fg_color="transparent")
        right_p.pack(side="right", anchor="e")
        ctk.CTkLabel(right_p, text="Total due today", text_color="#6B7280").pack(anchor="e")
        self.total_due_label = ctk.CTkLabel(right_p, text="$0.00", font=ctk.CTkFont(size=38, weight="bold"),
                                            text_color="#1F2937")
        self.total_due_label.pack(anchor="e")
        ctk.CTkLabel(right_p, text="includes rent + penalties", text_color="#9CA3AF",
                     font=ctk.CTkFont(size=13)).pack(anchor="e")

        # Breakdown
        breakdown = ctk.CTkFrame(penalty_frame, fg_color="white", corner_radius=16)
        breakdown.pack(fill="x", padx=24, pady=(0, 24))

        self.base_label = ctk.CTkLabel(breakdown, text="", anchor="w", font=ctk.CTkFont(size=15))
        self.base_label.grid(row=0, column=0, padx=24, pady=8, sticky="w
```