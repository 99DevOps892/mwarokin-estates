```python
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from PIL import Image, ImageTk
import requests
from io import BytesIO
import json
from datetime import datetime, timedelta
import random
import threading

class LeaseManagementApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mwarokin Estate - Lease Management & Matchmaking")
        self.root.geometry("1600x900")
        self.root.configure(bg="#f4f7fc")
        
        # Modern styling
        style = ttk.Style()
        style.theme_use('clam')
        self.configure_styles(style)
        
        self.lease_drafts = []
        self.mock_matches = self.get_mock_matches()
        
        self.create_ui()
        self.load_initial_data()
    
    def configure_styles(self, style):
        style.configure("TFrame", background="#f4f7fc")
        style.configure("Card.TFrame", background="white", relief="flat")
        style.configure("Title.TLabel", font=("Inter", 18, "bold"), foreground="#1a2c3e")
        style.configure("Header.TLabel", font=("Inter", 24, "bold"), foreground="#1E3C2C")
        style.configure("Accent.TButton", background="#1E3C2C", foreground="white", font=("Inter", 10, "bold"))
        style.configure("Outline.TButton", background="white", foreground="#1E3C2C")
    
    def get_mock_matches(self):
        return [
            {
                "id": "match_001",
                "property_name": "Baobab Ridge Villa",
                "location": "Karen, Nairobi",
                "image_url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=600&h=400&q=80",
                "tenant_name": "Eleanor Mwangi",
                "match_score": 96,
                "explanation": "High income stability + green living preferences align with estate eco-policies.",
                "monthly_rent": 3250,
                "compliance_status": "compliant",
                "compliance_text": "Compliant · all safety & zoning certified",
                "features": "Smart home, solar backup, EV charger"
            },
            {
                "id": "match_002",
                "property_name": "Savannah Heights",
                "location": "Westlands, Nairobi",
                "image_url": "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=600&h=400&q=80",
                "tenant_name": "Michael Odinga",
                "match_score": 88,
                "explanation": "Good credit score but pending fire inspection for unit.",
                "monthly_rent": 2890,
                "compliance_status": "conditional",
                "compliance_text": "Conditional · awaiting final electrical clearance",
                "features": "Gym access, rooftop terrace"
            },
            {
                "id": "match_003",
                "property_name": "Zambezi Courtyard",
                "location": "Riverside Drive",
                "image_url": "https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?auto=format&fit=crop&w=600&h=400&q=80",
                "tenant_name": "Naomi Chebet",
                "match_score": 79,
                "explanation": "Rent-to-income ratio borderline, zoning variance required.",
                "monthly_rent": 4100,
                "compliance_status": "noncompliant",
                "compliance_text": "Non-Compliant · zoning mismatch for commercial use clause",
                "features": "Pool, parking, smart locks"
            },
            {
                "id": "match_004",
                "property_name": "Kifaru Gardens",
                "location": "Lavington",
                "image_url": "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=600&h=400&q=80",
                "tenant_name": "David Kiprono",
                "match_score": 94,
                "explanation": "Excellent references, full compliance with Mwarokin standards.",
                "monthly_rent": 3750,
                "compliance_status": "compliant",
                "compliance_text": "Fully Compliant · green bond certified",
                "features": "Garden, smart irrigation"
            }
        ]
    
    def create_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header = ttk.Frame(main_frame)
        header.pack(fill=tk.X, pady=(0, 30))
        
        # Brand
        brand_frame = ttk.Frame(header)
        brand_frame.pack(side=tk.LEFT)
        ttk.Label(brand_frame, text="🌿 Mwarokin Estate", style="Header.TLabel").pack(anchor="w")
        ttk.Label(brand_frame, text="Intelligent leasing · Premium property matchmaking · Compliance first", 
                  foreground="#5a6e7c").pack(anchor="w")
        
        # Badge
        badge = tk.Frame(header, bg="white", relief="flat", bd=0, padx=20, pady=8)
        badge.pack(side=tk.RIGHT)
        tk.Label(badge, text="🛡️", bg="white", font=("Arial", 16)).pack(side=tk.LEFT)
        tk.Label(badge, text="Legal & Compliance Ready", bg="white", font=("Inter", 11, "bold")).pack(side=tk.LEFT, padx=8)
        
        # Dashboard grid simulation using PanedWindow
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Left: Matchmaking Section
        left_frame = ttk.Frame(paned, padding=10)
        paned.add(left_frame, weight=3)
        
        ttk.Label(left_frame, text="🤝 AI Matchmaking Results", style="Title.TLabel").pack(anchor="w", pady=(0, 15))
        
        self.match_canvas = tk.Canvas(left_frame, bg="white", highlightthickness=0)
        match_scroll = ttk.Scrollbar(left_frame, orient="vertical", command=self.match_canvas.yview)
        self.match_canvas.configure(yscrollcommand=match_scroll.set)
        
        match_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.match_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.match_inner = ttk.Frame(self.match_canvas)
        self.match_canvas.create_window((0, 0), window=self.match_inner, anchor="nw")
        self.match_inner.bind("<Configure>", lambda e: self.match_canvas.configure(scrollregion=self.match_canvas.bbox("all")))
        
        # Right Panel
        right_frame = ttk.Frame(paned, padding=10, width=380)
        paned.add(right_frame, weight=1)
        
        # Lease Drafts
        drafts_card = ttk.LabelFrame(right_frame, text="📄 Lease Drafts · Generated", padding=15)
        drafts_card.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        self.drafts_list = tk.Frame(drafts_card)
        self.drafts_list.pack(fill=tk.BOTH, expand=True)
        
        # Compliance Summary
        comp_card = ttk.LabelFrame(right_frame, text="✅ Compliance Status Overview", padding=15)
        comp_card.pack(fill=tk.X)
        
        self.compliant_var = tk.StringVar(value="0")
        self.conditional_var = tk.StringVar(value="0")
        self.noncomp_var = tk.StringVar(value="0")
        
        ttk.Label(comp_card, text="Fully Compliant Leases").pack(anchor="w")
        ttk.Label(comp_card, textvariable=self.compliant_var, font=("Inter", 16, "bold"), foreground="#1e6f3f").pack(anchor="w")
        
        self.progress = ttk.Progressbar(comp_card, length=300, mode='determinate')
        self.progress.pack(pady=8)
        
        ttk.Label(comp_card, text="Conditional / Pending").pack(anchor="w")
        ttk.Label(comp_card, textvariable=self.conditional_var, font=("Inter", 12), foreground="#b45f1b").pack(anchor="w")
        
        ttk.Label(comp_card, text="Action Required").pack(anchor="w")
        ttk.Label(comp_card, textvariable=self.noncomp_var, font=("Inter", 12), foreground="#b83b2e").pack(anchor="w")
        
        # Footer stats
        ttk.Separator(comp_card, orient="horizontal").pack(fill=tk.X, pady=12)
        ttk.Label(comp_card, text="Occupancy Rate: 94% | Avg. Lease Maturity: 8.7/10", foreground="#5a6e7c").pack()
        
        # Modal window (Toplevel)
        self.modal = None
    
    def load_image(self, url, size=(320, 160)):
        try:
            response = requests.get(url, timeout=5)
            img = Image.open(BytesIO(response.content))
            img = img.resize(size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
        except:
            # Fallback placeholder
            img = Image.new('RGB', size, color="#e2e8f0")
            return ImageTk.PhotoImage(img)
    
    def create_property_card(self, parent, match):
        card = tk.Frame(parent, bg="white", relief="solid", bd=1, padx=12, pady=12)
        card.pack(fill=tk.X, pady=12, padx=8)
        card.configure(highlightbackground="#eef2f5", highlightthickness=2)
        
        # Image
        img = self.load_image(match["image_url"])
        img_label = tk.Label(card, image=img, bg="white")
        img_label.image = img
        img_label.pack(fill=tk.X, pady=(0, 12))
        
        # Badges and content
        status_color = {
            "compliant": "#1e6f3f",
            "conditional": "#b45f1b",
            "noncompliant": "#b83b2e"
        }.get(match["compliance_status"], "#666")
        
        status_frame = tk.Frame(card, bg="white")
        status_frame.pack(fill=tk.X, pady=4)
        
        badge = tk.Label(status_frame, text=match["compliance_text"].split("·")[0].strip(),
                         bg=status_color, fg="white", font=("Inter", 9, "bold"), padx=10, pady=3)
        badge.pack(side=tk.LEFT)
        
        tk.Label(card, text=match["property_name"], font=("Inter", 14, "bold"), bg="white").pack(anchor="w")
        tk.Label(card, text=f"📍 {match['location']}", fg="#6c7e8f", bg="white").pack(anchor="w")
        
        score_frame = tk.Frame(card, bg="#eef6ff", padx=12, pady=4)
        score_frame.pack(anchor="w", pady=8)
        tk.Label(score_frame, text=f"Match: {match['match_score']}%", fg="#1a5d8f", 
                 font=("Inter", 10, "bold"), bg="#eef6ff").pack()
        
        tk.Label(card, text=match["explanation"], wraplength=380, justify="left", 
                 fg="#4b5f6e", bg="white").pack(anchor="w", pady=8)
        
        tk.Label(card, text=f"${match['monthly_rent']:,}/month", font=("Inter", 18, "bold"), 
                 fg="#1E3C2C", bg="white").pack(anchor="w")
        
        # Buttons
        btn_frame = tk.Frame(card, bg="white")
        btn_frame.pack(fill=tk.X, pady=(12, 0))
        
        view_btn = tk.Button(btn_frame, text="👁️ Details", relief="flat", bg="#f0f4f8", fg="#1E3C2C",
                            command=lambda m=match: self.show_details(m))
        view_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)
        
        gen_btn = tk.Button(btn_frame, text="📝 Generate Lease", relief="flat", bg="#1E3C2C", fg="white",
                           command=lambda m=match: self.generate_lease_draft(m))
        gen_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)
    
    def render_matchmaking(self):
        for widget in self.match_inner.winfo_children():
            widget.destroy()
        
        for match in self.mock_matches:
            self.create_property_card(self.match_inner, match)
    
    def generate_lease_draft(self, match):
        draft = {
            "id": f"draft_{int(datetime.now().timestamp())}",
            "property_name": match["property_name"],
            "tenant_name": match["tenant_name"],
            "monthly_rent": match["monthly_rent"],
            "duration": 12,
            "start_date": (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d"),
            "compliance": match["compliance_status"],
            "compliance_text": match["compliance_text"],
            "generated_at": datetime.now().strftime("%b %d, %Y %H:%M")
        }
        self.lease_drafts.insert(0, draft)
        self.update_drafts_ui()
        self.update_compliance_stats()
        self.show_lease_modal(draft)
        self.show_toast(f"Lease draft created for {match['property_name']}")
    
    def update_drafts_ui(self):
        for widget in self.drafts_list.winfo_children():
            widget.destroy()
        
        if not self.lease_drafts:
            tk.Label(self.drafts_list, text="No lease drafts yet.\nGenerate from matchmaking cards.", 
                     fg="#8ba0ae", justify="center").pack(pady=40)
            return
        
        for draft in self.lease_drafts:
            item = tk.Frame(self.drafts_list, bg="#fbfdfe", relief="solid", bd=1, padx=12, pady=12)
            item.pack(fill=tk.X, pady=8, padx=4)
            
            header = tk.Frame(item, bg="#fbfdfe")
            header.pack(fill=tk.X)
            
            tk.Label(header, text=draft["property_name"], font=("Inter", 11, "bold"), bg="#fbfdfe").pack(side=tk.LEFT)
            
            status_color = "#1e6f3f" if draft["compliance"] == "compliant" else "#b45f1b" if draft["compliance"] == "conditional" else "#b83b2e"
            tk.Label(header, text=draft["compliance"].upper(), bg=status_color, fg="white", 
                     font=("Inter", 9, "bold"), padx=8, pady=2).pack(side=tk.RIGHT)
            
            tk.Label(item, text=f"{draft['tenant_name']} • ${draft['monthly_rent']:,}/mo", 
                     fg="#5b6e7e", bg="#fbfdfe").pack(anchor="w", pady=4)
            
            btn_frame = tk.Frame(item, bg="#fbfdfe")
            btn_frame.pack(fill=tk.X, pady=(8, 0))
            
            tk.Button(btn_frame, text="View Draft", bg="transparent", fg="#2a6b47", relief="flat",
                     command=lambda d=draft: self.show_lease_modal(d)).pack(side=tk.LEFT)
            tk.Button(btn_frame, text="Delete", bg="transparent", fg="#b83b2e", relief="flat",
                     command=lambda d=draft: self.delete_draft(d)).pack(side=tk.RIGHT)
    
    def update_compliance_stats(self):
        compliant = sum(1 for d in self.lease_drafts if d["compliance"] == "compliant")
        conditional = sum(1 for d in self.lease_drafts if d["compliance"] == "conditional")
        noncomp = sum(1 for d in self.lease_drafts if d["compliance"] == "noncompliant")
        
        total = len(self.lease_drafts) or 1
        percent = int((compliant / total) * 100)
        
        self.compliant_var.set(str(compliant))
        self.conditional_var.set(str(conditional))
        self.noncomp_var.set(str(noncomp))
        self.progress['value'] = percent
    
    def delete_draft(self, draft):
        if messagebox.askyesno("Delete Draft", "Delete this lease draft?"):
            self.lease_drafts = [d for d in self.lease_drafts if d["id"] != draft["id"]]
            self.update_drafts_ui()
            self.update_compliance_stats()
            self.show_toast("Draft deleted")
    
    def show_lease_modal(self, draft):
        if self.modal and self.modal.winfo_exists():
            self.modal.destroy()
        
        modal = tk.Toplevel(self.root)
        modal.title("Professional Lease Draft")
        modal.geometry("700x620")
        modal.configure(bg="white")
        modal.grab_set()
        
        # Header
        header = tk.Frame(modal, bg="#1E3C2C", padx=20, pady=15)
        header.pack(fill=tk.X)
        tk.Label(header, text="📜 Professional Lease Draft", fg="white", bg="#1E3C2C", 
                 font=("Inter", 16, "bold")).pack(side=tk.LEFT)
        tk.Button(header, text="✕", command=modal.destroy, fg="white", bg="#1E3C2C", 
                  relief="flat", font=("Arial", 18)).pack(side=tk.RIGHT)
        
        content = tk.Frame(modal, bg="white", padx=25, pady=20)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Content
        tk.Label(content, text=f"{draft['property_name']} • Lease Agreement", 
                 font=("Inter", 15, "bold")).pack(anchor="w")
        
        status_color = "#1e6f3f" if draft["compliance"] == "compliant" else "#b45f1b"
        tk.Label(content, text=draft["compliance_text"], bg=status_color, fg="white", 
                 font=("Inter", 10, "bold"), padx=15, pady=6).pack(anchor="w", pady=12)
        
        details = f"""
Lessee: {draft['tenant_name']}
Commencement Date: {draft['start_date']}
Monthly Rent: ${draft['monthly_rent']:,}
Duration: {draft['duration']} months
        """
        tk.Label(content, text=details, justify="left", bg="white", anchor="w").pack(anchor="w", pady=15)
        
        # Risk / Notes area
        note_frame = tk.LabelFrame(content, text="Risk Analysis & Compliance Notes", padx=15, pady=15)
        note_frame.pack(fill=tk.BOTH, expand=True, pady=15)
        
        notes = scrolledtext.ScrolledText(note_frame, height=12, wrap=tk.WORD)
        notes.pack(fill=tk.BOTH, expand=True)
        notes.insert(tk.END, "✅ Draft aligns with Mwarokin Estate premium standards.\n\n")
        notes.insert(tk.END, f"Generated: {draft['generated_at']}\nDraft ID: {draft['id']}\n\n")
        notes.insert(tk.END, "E-signature ready after final review.")
        notes.configure(state="disabled")
        
        # Footer
        footer = tk.Frame(modal, bg="#f9fafc", padx=20, pady=15)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Button(footer, text="Close Preview", command=modal.destroy, bg="#f0f4f8", padx=20).pack(side=tk.RIGHT)
    
    def show_details(self, match):
        self.show_toast(f"Viewing details for {match['property_name']} - Match Score: {match['match_score']}%")
    
    def show_toast(self, message):
        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.geometry("380x60+1200+780")
        toast.configure(bg="#1E3C2C")
        
        tk.Label(toast, text=message, fg="white", bg="#1E3C2C", font=("Inter", 10), padx=20, pady=12).pack()
        
        def close_toast():
            if toast.winfo_exists():
                toast.destroy()
        
        self.root.after(2800, close_toast)
    
    def load_initial_data(self):
        # Render matches
        self.render_matchmaking()
        
        # Add demo draft
        if not self.lease_drafts:
            demo_match = self.mock_matches[0]
            self.generate_lease_draft(demo_match)
        
        self.update_compliance_stats()


if __name__ == "__main__":
    root = tk.Tk()
    app = LeaseManagementApp(root)
    root.mainloop()
```