```python
import flet as ft
import random
from typing import List, Dict, Optional
import time

class Tier:
    def __init__(self, key: str, name: str, req: str, color: str, glyph: str, bg: str):
        self.key = key
        self.name = name
        self.req = req
        self.color = color
        self.glyph = glyph
        self.bg = bg

class Agent:
    def __init__(self, name: str, territory: str, tier: str, status: str, 
                 deals: int, commission: int, kyc: str, conv: str, color: str):
        self.name = name
        self.territory = territory
        self.tier = tier
        self.status = status
        self.deals = deals
        self.commission = commission
        self.kyc = kyc
        self.conv = conv
        self.color = color

class Territory:
    def __init__(self, name: str, agents: int, listings: int, pct: int):
        self.name = name
        self.agents = agents
        self.listings = listings
        self.pct = pct

class PipelineStage:
    def __init__(self, stage: str, count: int, color: str):
        self.stage = stage
        self.count = count
        self.color = color

# Data
TIERS = [
    Tier('taifa', 'Taifa', '150+ deals · Nation-wide mandate', '#C9A24B', '#1C1508', 'linear-gradient(155deg,#E9C876,#B9903B)'),
    Tier('milki', 'Milki', '80+ deals · Ownership tier', '#9C8CE0', '#1C1508', 'linear-gradient(155deg,#B9ADEE,#7A6BC9)'),
    Tier('jengo', 'Jengo', '35+ deals · Building tier', '#6FB6A8', '#0B221C', 'linear-gradient(155deg,#8FD2C4,#4C9484)'),
    Tier('msingi', 'Msingi', '0+ deals · Foundation tier', '#8C93A6', '#12141C', 'linear-gradient(155deg,#AAB1C4,#6B7286)'),
]

AGENTS = [
    Agent('Kevin Otieno', 'Kilimani', 'taifa', 'active', 162, 284500, 'verified', '34%', '#4F46E5'),
    Agent('Amina Yusuf', 'Westlands', 'taifa', 'active', 158, 271200, 'verified', '31%', '#C9A24B'),
    Agent('Brian Kiplagat', 'Karen', 'milki', 'active', 96, 168300, 'verified', '27%', '#177A54'),
    Agent('Faith Njoroge', 'Ruaka', 'milki', 'active', 88, 151900, 'verified', '25%', '#BC3B3B'),
    Agent('Dennis Mwangi', 'South B', 'milki', 'on leave', 81, 139800, 'verified', '22%', '#B4791A'),
    Agent('Cynthia Wafula', 'Kasarani', 'jengo', 'active', 52, 88400, 'pending', '19%', '#4F46E5'),
    Agent('Peter Kamau', 'South C', 'jengo', 'active', 47, 79600, 'verified', '21%', '#177A54'),
    Agent('Grace Achieng', 'Westlands', 'jengo', 'active', 41, 71200, 'verified', '18%', '#C9A24B'),
    Agent('Samuel Kiprono', 'Kilimani', 'jengo', 'suspended', 38, 64100, 'rejected', '14%', '#BC3B3B'),
    Agent('Lucy Chebet', 'Ruaka', 'msingi', 'active', 19, 32800, 'pending', '16%', '#177A54'),
    Agent('Hassan Ali', 'Karen', 'msingi', 'active', 14, 24100, 'verified', '12%', '#4F46E5'),
    Agent('Mercy Wanjiru', 'South B', 'msingi', 'active', 9, 15600, 'pending', '10%', '#B4791A'),
]

TERRITORIES = [
    Territory('Kilimani', 6, 84, 88),
    Territory('Westlands', 5, 71, 76),
    Territory('Ruaka', 4, 52, 63),
    Territory('Karen', 4, 38, 54),
    Territory('South B / C', 5, 46, 49),
    Territory('Kasarani', 3, 29, 38),
]

PIPELINE = [
    PipelineStage('New Lead', 58, '#8C93A6'),
    PipelineStage('Contacted', 41, '#4F46E5'),
    PipelineStage('Viewing', 26, '#B4791A'),
    PipelineStage('Offer', 14, '#6FB6A8'),
    PipelineStage('Closed', 9, '#177A54'),
]

PAYOUTS = [
    {"name": "Kevin Otieno", "amount": 48200, "date": "Requested 2h ago", "status": "pending"},
    {"name": "Amina Yusuf", "amount": 39600, "date": "Requested 5h ago", "status": "pending"},
    {"name": "Brian Kiplagat", "amount": 22100, "date": "Requested yesterday", "status": "pending"},
    {"name": "Grace Achieng", "amount": 14300, "date": "Approved · paid out", "status": "done"},
    {"name": "Faith Njoroge", "amount": 27900, "date": "Approved · paid out", "status": "done"},
]

VIEWINGS = [
    {"title": "2BR Apartment — Kilimani Ridge", "agent": "Kevin Otieno", "time": "Today, 2:30 PM"},
    {"title": "Office Suite — Westlands Square", "agent": "Amina Yusuf", "time": "Today, 4:00 PM"},
    {"title": "Townhouse — Ruaka Greens", "agent": "Faith Njoroge", "time": "Tomorrow, 10:00 AM"},
    {"title": "Studio — South B Court", "agent": "Cynthia Wafula", "time": "Tomorrow, 1:15 PM"},
]

ACTIVITIES = [
    {"icon": "handshake", "color": "#10b981", "bg": "#ecfdf5", "text": "<b>Brian Kiplagat</b> closed a deal on Karen Villa 12", "time": "12 minutes ago"},
    {"icon": "person_add", "color": "#6366f1", "bg": "#eef2ff", "text": "<b>Lucy Chebet</b> submitted KYC documents", "time": "48 minutes ago"},
]

def initials(name: str) -> str:
    parts = name.split()
    return ''.join(p[0] for p in parts[:2]).upper()

def fmt_kes(n: int) -> str:
    return f"KES {n:,}"

class MwarokinApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Mwarokin Estates - Agent Console"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.bgcolor = "#f8f9fc"
        self.page.padding = 0
        self.page.spacing = 0
        self.page.window_width = 1480
        self.page.window_height = 920
        self.page.window_resizable = True
        self.page.fonts = {"inter": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"}
        
        self.current_filter = "all"
        self.sort_key = "commission"
        self.sort_dir = -1
        self.selected_agent = None
        
        self.setup_ui()

    def setup_ui(self):
        # Sidebar
        self.sidebar = self.build_sidebar()
        
        # Main Content
        self.main_content = self.build_main_content()
        
        # Root layout
        root = ft.Row(
            controls=[
                self.sidebar,
                ft.VerticalDivider(width=1, color="#e5e7eb"),
                self.main_content
            ],
            expand=True,
            spacing=0
        )
        
        self.page.add(root)
        self.page.update()
        
        # Initial renders
        self.render_ladder()
        self.render_agents()
        self.render_territories()
        self.render_pipeline()
        self.render_activity()
        self.render_payouts()
        self.render_viewings()
        
        # Simulate live activity
        self.page.on_interval = self.live_activity_pulse
        self.page.interval = 25000  # 25 seconds

    def build_sidebar(self) -> ft.Container:
        return ft.Container(
            width=280,
            bgcolor="#0f172a",
            padding=20,
            content=ft.Column(
                controls=[
                    # Brand
                    ft.Row(
                        controls=[
                            ft.Container(
                                width=48, height=48, border_radius=12, bgcolor="#c9a24b",
                                content=ft.Text("ME", size=22, weight="bold", color="#1c1508", text_align="center"),
                                alignment=ft.alignment.center
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text("Mwarokin Estates", size=18, weight="bold", color="white"),
                                    ft.Text("Agent Console", size=12, color="#94a3b8")
                                ],
                                spacing=2
                            )
                        ],
                        spacing=12
                    ),
                    ft.Divider(height=30, color="#334155"),
                    
                    # Navigation
                    ft.Text("Overview", size=13, color="#64748b", weight="w500"),
                    self.nav_item("Agent Dashboard", "pie_chart", active=True),
                    self.nav_item("Properties", "home"),
                    self.nav_item("Tenants", "people"),
                    
                    ft.Text("Agent Operations", size=13, color="#64748b", weight="w500", margin=ft.margin.only(top=20)),
                    self.nav_item("Agent Directory", "badge", badge="32"),
                    self.nav_item("Lead Pipeline", "filter_alt", badge="58"),
                    self.nav_item("Territories", "map"),
                    self.nav_item("Commissions", "monetization_on"),
                    self.nav_item("Rank & Incentives", "military_tech"),
                    self.nav_item("Viewings & Tasks", "calendar_month"),
                    
                    ft.Text("System", size=13, color="#64748b", weight="w500", margin=ft.margin.only(top=20)),
                    self.nav_item("Payout Requests", "request_quote", badge="6"),
                    self.nav_item("AI Agents", "smart_toy"),
                    self.nav_item("Settings", "settings"),
                    
                    # Footer
                    ft.Container(
                        margin=ft.margin.only(top=40),
                        content=ft.Row(
                            controls=[
                                ft.CircleAvatar(
                                    content=ft.Text("RM", size=16, weight="bold"),
                                    bgcolor="#c9a24b", color="#1c1508", radius=22
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Text("Robin Mwarema", size=14, color="white", weight="w600"),
                                        ft.Text("Estate Director", size=12, color="#94a3b8")
                                    ],
                                    spacing=1
                                )
                            ],
                            spacing=12
                        )
                    )
                ],
                expand=True,
                spacing=8
            )
        )

    def nav_item(self, text: str, icon: str, active: bool = False, badge: str = None):
        return ft.Container(
            padding=12,
            border_radius=8,
            bgcolor="#1e2937" if active else None,
            content=ft.Row(
                controls=[
                    ft.Icon(icon, color="#e2e8f0" if not active else "#fcd34d", size=20),
                    ft.Text(text, color="#e2e8f0" if not active else "#fcd34d", size=14, expand=True),
                    ft.Text(badge, size=11, color="#fcd34d", weight="bold") if badge else None
                ],
                alignment="space_between"
            )
        )

    def build_main_content(self) -> ft.Container:
        self.topbar = self.build_topbar()
        
        self.kpi_strip = self.build_kpi_strip()
        
        self.ladder_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Row([ft.Icon("layers", color="#c9a24b"), ft.Text("Agent Rank Ladder", size=18, weight="bold")]),
                        ft.Text("Progression tiers from the Mwarokin agent incentive programme", size=13, color="#64748b")
                    ]),
                    ft.Text("Sorted by commission earned this quarter", size=13, color="#94a3b8")
                ], alignment="space_between"),
                ft.Container(id="ladder_container", expand=True, padding=10)
            ]),
            bgcolor="white",
            border_radius=16,
            padding=24,
            margin=ft.margin.only(top=20, left=20, right=20)
        )
        
        # Grid 1
        grid1 = ft.Row(
            controls=[
                self.build_agent_directory(),
                self.build_territory_panel()
            ],
            expand=True,
            spacing=20
        )
        
        # Grid 2
        grid2 = ft.Row(
            controls=[
                self.build_pipeline_panel(),
                self.build_activity_panel()
            ],
            expand=True,
            spacing=20
        )
        
        # Grid 3
        grid3 = ft.Row(
            controls=[
                self.build_payout_panel(),
                self.build_viewings_panel()
            ],
            expand=True,
            spacing=20
        )
        
        main_col = ft.Column(
            controls=[
                self.topbar,
                self.kpi_strip,
                self.ladder_card,
                grid1,
                grid2,
                grid3
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=10
        )
        
        return ft.Container(
            content=main_col,
            expand=True,
            padding=20,
            bgcolor="#f8f9fc"
        )

    def build_topbar(self) -> ft.Container:
        self.search_field = ft.TextField(
            hint_text="Search agents, phone, territory…",
            prefix_icon=ft.Icon("search"),
            width=360,
            bgcolor="white",
            border_radius=12,
            border_color="#e2e8f0",
            on_change=self.on_search_change
        )
        
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Column([
                        ft.Text("Agent Dashboard", size=26, weight="bold"),
                        ft.Text("Performance, commissions and territory coverage across all Mwarokin agencies", 
                               size=14, color="#64748b")
                    ]),
                    ft.Row([
                        self.search_field,
                        ft.Container(
                            content=ft.Row([
                                ft.Icon("location_on", color="#92400e"),
                                ft.Text("All Nairobi zones", size=14),
                                ft.Icon("arrow_drop_down", size=18)
                            ]),
                            padding=12,
                            bgcolor="white",
                            border_radius=999,
                            border=ft.border.all(1, "#e2e8f0")
                        ),
                        ft.IconButton(icon=ft.Icons.NOTIFICATIONS, icon_size=22, 
                                     on_click=lambda e: self.show_toast("6 new notifications")),
                        ft.ElevatedButton(
                            "Invite Agent",
                            icon=ft.Icons.PERSON_ADD,
                            style=ft.ButtonStyle(
                                bgcolor="#92400e",
                                color="white",
                                shape=ft.RoundedRectangleBorder(radius=12)
                            ),
                            on_click=self.open_invite_modal
                        )
                    ], spacing=12)
                ],
                alignment="space_between"
            ),
            padding=ft.padding.only(bottom=20)
        )

    def build_kpi_strip(self) -> ft.Row:
        kpis = [
            ("Commission Payable", "KES 1,842,300", "14.2% vs last month", "coins", "#92400e", True),
            ("Active Agents", "32", "4 onboarded this month", "badge", "#4338ca", True),
            ("Leads This Month", "318", "22% conversion to viewing", "target", "#10b981", True),
            ("Avg Deal Close Time", "6.4 days", "1.1 days faster", "timer", "#d97706", False),
        ]
        
        return ft.Row(
            controls=[
                self.kpi_card(label, value, sub, icon, color, up)
                for label, value, sub, icon, color, up in kpis
            ],
            spacing=16
        )

    def kpi_card(self, label: str, value: str, sub: str, icon: str, color: str, up: bool):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(label, size=13, color="#64748b"),
                    ft.Container(
                        content=ft.Icon(icon, color=color),
                        width=36, height=36, border_radius=10,
                        bgcolor=f"{color}22", alignment=ft.alignment.center
                    )
                ], alignment="space_between"),
                ft.Text(value, size=28, weight="bold"),
                ft.Row([
                    ft.Icon("arrow_upward" if up else "arrow_downward", color="#10b981" if up else "#ef4444", size=16),
                    ft.Text(sub, size=13, color="#10b981" if up else "#ef4444")
                ])
            ]),
            bgcolor="white",
            border_radius=16,
            padding=20,
            expand=True
        )

    def build_agent_directory(self) -> ft.Container:
        self.agent_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Agent")),
                ft.DataColumn(ft.Text("Tier")),
                ft.DataColumn(ft.Text("Status")),
                ft.DataColumn(ft.Text("Deals")),
                ft.DataColumn(ft.Text("Commission")),
                ft.DataColumn(ft.Text("KYC")),
            ],
            rows=[],
            expand=True,
            border_radius=12
        )
        
        tabs = ft.Row([
            ft.Container(content=ft.Text("All", weight="w600"), 
                        padding=ft.padding.symmetric(12, 20), 
                        border_radius=999, bgcolor="#92400e22" if self.current_filter == "all" else None,
                        on_click=lambda e: self.filter_agents("all")),
            ft.Container(content=ft.Text("Active"), 
                        padding=ft.padding.symmetric(12, 20), 
                        border_radius=999,
                        on_click=lambda e: self.filter_agents("active")),
            ft.Container(content=ft.Text("Pending KYC"), 
                        padding=ft.padding.symmetric(12, 20), 
                        border_radius=999,
                        on_click=lambda e: self.filter_agents("pending")),
        ])
        
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Row([ft.Icon("badge"), ft.Text("Agent Directory", size=17, weight="w600")]),
                    tabs
                ], alignment="space_between"),
                ft.Container(
                    content=self.agent_table,
                    expand=True,
                    bgcolor="white",
                    border_radius=12,
                    padding=10
                )
            ]),
            bgcolor="white",
            border_radius=16,
            padding=20,
            expand=True
        )

    def build_territory_panel(self) -> ft.Container:
        self.territory_list = ft.Column(spacing=12)
        return ft.Container(
            content=ft.Column([
                ft.Row([ft.Icon("map"), ft.Text("Territory Coverage", size=17, weight="w600")]),
                self.territory_list
            ]),
            bgcolor="white",
            border_radius=16,
            padding=20,
            expand=True
        )

    def build_pipeline_panel(self) -> ft.Container:
        self.pipeline_container = ft.Column(spacing=18)
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Row([ft.Icon("filter_alt"), ft.Text("Lead Pipeline", size=17, weight="w600")]),
                    ft.ElevatedButton("New Lead", icon=ft.Icons.ADD, 
                                    style=ft.ButtonStyle(bgcolor="#f3f4f6", color="#334155"))
                ], alignment="space_between"),
                self.pipeline_container
            ]),
            bgcolor="white",
            border_radius=16,
            padding=20,
            expand=True
        )

    def build_activity_panel(self) -> ft.Container:
        self.activity_list = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, height=280)
        return ft.Container(
            content=ft.Column([
                ft.Text("Live Activity", size=17, weight="w600"),
                self.activity_list
            ]),
            bgcolor="white",
            border_radius=16,
            padding=20,
            expand=True
        )

    def build_payout_panel(self) -> ft.Container:
        self.payout_list = ft.Column(spacing=12)
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Row([ft.Icon("request_quote"), ft.Text("Payout Requests", size=17, weight="w600")]),
                    ft.Container(content=ft.Text("6 pending", size=13, color="#d97706", weight="w600"),
                                padding=ft.padding.symmetric(4, 12), bgcolor="#fef3c7", border_radius=999)
                ], alignment="space_between"),
                self.payout_list
            ]),
            bgcolor="white",
            border_radius=16,
            padding=20,
            expand=True
        )

    def build_viewings_panel(self) -> ft.Container:
        self.viewings_list = ft.Column(spacing=14)
        return ft.Container(
            content=ft.Column([
                ft.Text("Upcoming Viewings", size=17, weight="w600"),
                self.viewings_list
            ]),
            bgcolor="white",
            border_radius=16,
            padding=20,
            expand=True
        )

    # Render functions
    def render_ladder(self):
        container = self.page.get_control("ladder_container")
        if not container:
            return
        container.controls.clear()
        
        for tier in TIERS:
            members = [a for a in AGENTS if a.tier == tier.key]
            members.sort(key=lambda x: x.commission, reverse=True)
            total_comm = sum(m.commission for m in members)
            shown = members[:6]
            
            avatars = ft.Row([
                ft.Container(
                    content=ft.Text(initials(a.name), size=11, weight="bold", color="white"),
                    width=32, height=32, border_radius=999, bgcolor=a.color,
                    alignment=ft.alignment.center,
                    tooltip=f"{a.name} — {fmt_kes(a.commission)}"
                ) for a in shown
            ], spacing=-8)
            
            if len(members) > 6:
                avatars.controls.append(
                    ft.Container(
                        content=ft.Text(f"+{len(members)-6}", size=11),
                        width=32, height=32, border_radius=999, bgcolor="#e2e8f0",
                        alignment=ft.alignment.center
                    )
                )
            
            rung = ft.Container(
                content=ft.Row([
                    ft.Row([
                        ft.Container(
                            content=ft.Text(tier.name[0], size=24, weight="bold", color=tier.glyph),
                            width=52, height=52, border_radius=12,
                            gradient=ft.LinearGradient(begin=ft.alignment.top_left, end=ft.alignment.bottom_right, 
                                                     colors=[tier.bg.split(',')[0][18:], tier.bg.split(',')[1][:-1]]),
                            alignment=ft.alignment.center
                        ),
                        ft.Column([
                            ft.Text(tier.name, size=16, weight="bold"),
                            ft.Text(tier.req, size=12, color="#64748b")
                        ])
                    ]),
                    avatars,
                    ft.Column([
                        ft.Text(fmt_kes(total_comm), size=15, weight="bold"),
                        ft.Text(f"{len(members)} agents", size=12, color="#64748b")
                    ], horizontal_alignment="end")
                ], alignment="space_between"),
                padding=16,
                margin=ft.margin.only(bottom=8),
                bgcolor="#f8fafc",
                border_radius=12
            )
            container.controls.append(rung)
        self.page.update()

    def render_agents(self):
        if not hasattr(self, 'agent_table'):
            return
        
        filtered = [a for a in AGENTS]
        
        # Apply search
        if hasattr(self, 'search_field') and self.search_field.value:
            q = self.search_field.value.lower()
            filtered = [a for a in filtered if q in a.name.lower() or q in a.territory.lower()]
        
        # Apply filter
        if self.current_filter == "active":
            filtered = [a for a in filtered if a.status == "active"]
        elif self.current_filter == "pending":
            filtered = [a for a in filtered if a.kyc == "pending"]
        
        # Sort
        filtered.sort(key=lambda x: getattr(x, self.sort_key, 0), reverse=self.sort_dir == -1)
        
        self.agent_table.rows.clear()
        
        for agent in filtered:
            tier_obj = next((t for t in TIERS if t.key == agent.tier), None)
            
            row = ft.DataRow(
                cells=[
                    ft.DataCell(
                        ft.Row([
                            ft.CircleAvatar(content=ft.Text(initials(agent.name), size=12), 
                                          bgcolor=agent.color, radius=18),
                            ft.Column([
                                ft.Text(agent.name, weight="w600", size=14),
                                ft.Text(agent.territory, size=12, color="#64748b")
                            ])
                        ])
                    ),
                    ft.DataCell(ft.Container(
                        content=ft.Text(tier_obj.name if tier_obj else agent.tier, size=13, weight="w500"),
                        padding=ft.padding.symmetric(6, 12),
                        bgcolor=f"{tier_obj.color}22" if tier_obj else "#e2e8f0",
                        border_radius=999
                    )),
                    ft.DataCell(ft.Row([
                        ft.Container(width=8, height=8, border_radius=999, 
                                   bgcolor="#10b981" if agent.status == "active" else "#f59e0b"),
                        ft.Text(agent.status.title(), size=13)
                    ])),
                    ft.DataCell(ft.Text(str(agent.deals), size=14, weight="w600")),
                    ft.DataCell(ft.Text(fmt_kes(agent.commission), size=14, weight="w600")),
                    ft.DataCell(ft.Text("✓ Verified" if agent.kyc == "verified" else "Pending", 
                                      color="#10b981" if agent.kyc == "verified" else "#f59e0b"))
                ],
                on_select_changed=lambda e, a=agent: self.open_drawer(a)
            )
            self.agent_table.rows.append(row)
        self.page.update()

    def filter_agents(self, filter_type: str):
        self.current_filter = filter_type
        self.render_agents()

    def on_search_change(self, e):
        self.render_agents()

    def render_territories(self):
        self.territory_list.controls.clear()
        for t in TERRITORIES:
            item = ft.Row([
                ft.Column([
                    ft.Text(t.name, weight="bold"),
                    ft.Text(f"{t.agents} agents · {t.listings} listings", size=12, color="#64748b"),
                    ft.ProgressBar(value=t.pct/100, width=180, color="#92400e", bgcolor="#f3f4f6")
                ]),
                ft.Text(f"{t.pct}%", size=18, weight="bold", color="#92400e")
            ], alignment="space_between")
            self.territory_list.controls.append(item)
        self.page.update()

    def render_pipeline(self):
        self.pipeline_container.controls.clear()
        max_count = max(p.count for p in PIPELINE)
        
        for p in PIPELINE:
            bar = ft.Row([
                ft.Text(p.stage, width=90, size=13),
                ft.Container(
                    content=ft.Text(str(p.count), color="white", size=12, text_align="center"),
                    width=max(60, int(p.count / max_count * 220)),
                    height=32,
                    bgcolor=p.color,
                    border_radius=8,
                    alignment=ft.alignment.center
                )
            ])
            self.pipeline_container.controls.append(bar)
        self.page.update()

    def render_activity(self):
        self.activity_list.controls.clear()
        for act in ACTIVITIES:
            item = ft.Row([
                ft.Container(
                    content=ft.Icon(act["icon"], color=act["color"]),
                    width=36, height=36, border_radius=999, bgcolor=act["bg"],
                    alignment=ft.alignment.center
                ),
                ft.Column([
                    ft.Text(act["text"], size=13),
                    ft.Text(act["time"], size=12, color="#94a3b8")
                ], spacing=2)
            ], spacing=16)
            self.activity_list.controls.append(item)
        self.page.update()

    def render_payouts(self):
        self.payout_list.controls.clear()
        for p in PAYOUTS:
            row = ft.Row([
                ft.Column([
                    ft.Text(p["name"], weight="w600"),
                    ft.Text(p["date"], size=12, color="#64748b")
                ]),
                ft.Text(fmt_kes(p["amount"]), weight="w600", size=15),
                ft.ElevatedButton(
                    "Approve" if p["status"] == "pending" else "Paid",
                    style=ft.ButtonStyle(bgcolor="#92400e" if p["status"] == "pending" else "#10b981", color="white"),
                    on_click=lambda e, pay=p: self.approve_payout(pay)
                ) if p["status"] == "pending" else 
                ft.Container(content=ft.Text("Paid", color="#10b981"), padding=8)
            ], alignment="space_between")
            self.payout_list.controls.append(row)
        self.page.update()

    def approve_payout(self, payout):
        self.show_toast(f"Payout of {fmt_kes(payout['amount'])} approved")
        # Refresh
        self.render_payouts()

    def render_viewings(self):
        self.viewings_list.controls.clear()
        for v in VIEWINGS:
            item = ft.Row([
                ft.Container(
                    content=ft.Icon("calendar_today", size=20, color="#4338ca"),
                    width=42, height=42, border_radius=10, bgcolor="#e0e7ff",
                    alignment=ft.alignment.center
                ),
                ft.Column([
                    ft.Text(v["title"], size=14, weight="w600"),
                    ft.Text(f"{v['agent']} · {v['time']}", size=12, color="#64748b")
                ], spacing=2)
            ], spacing=16)
            self.viewings_list.controls.append(item)
        self.page.update()

    def open_drawer(self, agent: Agent):
        # Simple modal drawer simulation using AlertDialog
        dlg = ft.AlertDialog(
            title=ft.Text(f"{agent.name} - {agent.territory}"),
            content=ft.Column([
                ft.Row([
                    ft.CircleAvatar(content=ft.Text(initials(agent.name)), bgcolor=agent.color, radius=32),
                    ft.Column([
                        ft.Text(agent.name, size=18, weight="bold"),
                        ft.Text(f"{tier.name} Tier", size=14) for tier in TIERS if tier.key == agent.tier
                    ])
                ]),
                ft.Divider(),
                ft.Row([ft.Text(f"Deals: {agent.deals}"), ft.Text(f"Conv: {agent.conv}")]),
                ft.Text(f"Commission: {fmt_kes(agent.commission)}", weight="bold")
            ], spacing=15, tight=True),
            actions=[
                ft.TextButton("Message", on_click=lambda e: self.show_toast("Message sent")),
                ft.TextButton("Review Payout", on_click=lambda e: self.show_toast("Payout review opened")),
                ft.TextButton("Close", on_click=lambda e: self.page.close(dlg))
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def open_invite_modal(self, e):
        def send_invite(e):
            self.page.close(dlg)
            self.show_toast("Invitation sent — agent will receive onboarding link via SMS & email")
        
        dlg = ft.AlertDialog(
            title=ft.Text("Invite New Agent"),
            content=ft.Column([
                ft.TextField(label="Full Name", hint_text="e.g. Wanjiru Kamau"),
                ft.TextField(label="Phone Number", hint_text="+254 7…"),
                ft.TextField(label="Email Address", hint_text="agent@mwarokinestates.co.ke"),
                ft.Row([
                    ft.Dropdown(
                        label="Assigned Territory",
                        options=[ft.dropdown.Option(t) for t in ["Kilimani", "Westlands", "Ruaka", "Karen", "Kasarani"]]
                    ),
                    ft.Dropdown(
                        label="Starting Tier",
                        options=[ft.dropdown.Option(t.name) for t in TIERS]
                    )
                ])
            ], width=500, height=320, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.page.close(dlg)),
                ft.ElevatedButton("Send Invite", icon=ft.Icons.SEND, bgcolor="#92400e", color="white", on_click=send_invite)
            ]
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def show_toast(self, message: str):
        self.page.show_snack_bar(
            ft.SnackBar(
                content=ft.Text(f"✓ {message}"),
                bgcolor="#854d0e",
                duration=4000
            )
        )

    def live_activity_pulse(self):
        new_act = random.choice([
            {"icon": "visibility", "color": "#6366f1", "bg": "#eef2ff", "text": "New lead assigned in <b>Kilimani</b>"},
            {"icon": "monetization_on", "color": "#92400e", "bg": "#fef3c7", "text": "Commission credited to <b>Peter Kamau</b>"}
        ])
        
        item = ft.Row([
            ft.Container(
                content=ft.Icon(new_act["icon"], color=new_act["color"]),
                width=36, height=36, border_radius=999, bgcolor=new_act["bg"],
                alignment=ft.alignment.center
            ),
            ft.Column([
                ft.Text(new_act["text"], size=13),
                ft.Text("Just now", size=12, color="#94a3b8")
            ])
        ], spacing=16)
        
        self.activity_list.controls.insert(0, item)
        if len(self.activity_list.controls) > 6:
            self.activity_list.controls.pop()
        self.page.update()


def main(page: ft.Page):
    MwarokinApp(page)

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8550)
```