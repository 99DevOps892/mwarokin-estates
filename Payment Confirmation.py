"""
Modern Professional Premium Python Code — Mwarokin Estates Payment Confirmation
PyQt5 implementation of the provided payment UI with advanced features.
"""

import sys
import os
import tempfile
import webbrowser
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QFrame, QGridLayout, QSizePolicy,
    QMessageBox, QStyle, QStyleOption, QSpacerItem
)
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint,
    pyqtProperty, QByteArray, QClipboard
)
from PyQt5.QtGui import (
    QFont, QFontDatabase, QColor, QPalette, QPixmap, QPainter,
    QPen, QBrush, QLinearGradient, QPainterPath, QIcon
)


# ============================================================================
# Data Model
# ============================================================================
class PaymentData:
    """Holds payment details for each bill type."""
    def __init__(self, amount, description, reference, txn_id, method, confirmation, label):
        self.amount = amount
        self.description = description
        self.reference = reference
        self.txn_id = txn_id
        self.method = method
        self.confirmation = confirmation
        self.label = label


PAYMENT_DICT = {
    "rent": PaymentData(
        1250.00,
        "Monthly Rent — Unit 4B (Premium Suite)",
        "MWK-R-2409-421",
        "TXN-MWK-82F4A1E3",
        "Visa •••• 4821",
        "Your rent payment of $1,250.00 for Unit 4B has been applied successfully. "
        "No outstanding balance. Thank you for being a valued resident.",
        "Rent"
    ),
    "amenities": PaymentData(
        89.50,
        "Amenities Package — Gym, Pool, Fibre WiFi, Concierge",
        "MWK-AMEN-0626-892",
        "TXN-MWK-9F3B2D7C",
        "Mastercard •••• 2276",
        "Amenities fee of $89.50 successfully paid. Your access to the fitness centre, "
        "pool, and premium WiFi is confirmed through June 30, 2026.",
        "Amenities"
    ),
    "paybill": PaymentData(
        210.30,
        "Utilities & Service Paybill — Water, Electricity, Waste",
        "MWK-UB-9981-45",
        "TXN-MWK-3A9E7F2B",
        "Bank Transfer · KCB",
        "Your paybill of $210.30 covering water, electricity, and waste services is "
        "confirmed. Outstanding balance: $0.00. Next meter reading on July 1.",
        "Paybill"
    )
}


# ============================================================================
# Modern Styling (QSS)
# ============================================================================
STYLE_SHEET = """
QMainWindow {
    background: qlineargradient(x1:0.15, y1:0, x2:0.85, y2:1,
                                stop:0 #1C4438, stop:0.6 #132D26, stop:1 #0B1B16);
}
QTabWidget::pane {
    background: #FCF9F0;
    border-radius: 6px 18px 18px 18px;
    border: none;
    margin-top: 0px;
}
QTabBar::tab {
    font-family: "Inter";
    font-size: 13px;
    font-weight: 600;
    color: rgba(252,249,240,0.65);
    background: rgba(252,249,240,0.05);
    border: 1px solid rgba(252,249,240,0.14);
    border-bottom: none;
    padding: 10px 18px 10px 16px;
    border-radius: 10px 10px 0 0;
    margin-right: 4px;
    min-width: 80px;
}
QTabBar::tab:selected {
    background: #FCF9F0;
    color: #1E4A3B;
    border-color: #FCF9F0;
}
QTabBar::tab:hover:!selected {
    background: rgba(252,249,240,0.09);
    color: #FCF9F0;
}
QLabel#brandLabel {
    font-family: "Fraunces";
    font-weight: 500;
    font-size: 28px;
    color: #FCF9F0;
    letter-spacing: -0.01em;
}
QLabel#brandLabel em {
    font-style: italic;
    color: #D9B759;
}
QLabel#statusChip {
    background: rgba(217,183,89,0.1);
    border: 1px solid rgba(217,183,89,0.35);
    color: #EFDCA0;
    font-size: 12px;
    font-weight: 500;
    padding: 8px 14px;
    border-radius: 100px;
}
QLabel#successTitle {
    font-family: "Fraunces";
    font-weight: 500;
    font-size: 22px;
    color: #241F17;
}
QLabel#successSub {
    font-size: 13px;
    color: #635A49;
}
QLabel#amountLabel {
    font-family: "JetBrains Mono";
    font-size: 10px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #8C8271;
}
QLabel#amountValue {
    font-family: "Fraunces";
    font-weight: 600;
    font-size: 44px;
    color: #1E4A3B;
    line-height: 1;
}
QLabel#billTag {
    font-size: 11px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 6px;
    background: #EAE0C6;
    color: #635A49;
}
QLabel.detailLabel {
    font-size: 13px;
    color: #635A49;
}
QLabel.detailValue {
    font-size: 13px;
    font-weight: 500;
    color: #241F17;
}
QLabel.detailValue.mono {
    font-family: "JetBrains Mono";
    font-size: 12px;
}
QFrame#confirmationBox {
    background: rgba(30,74,59,0.06);
    border: 1px solid rgba(30,74,59,0.15);
    border-radius: 10px;
    padding: 14px 16px;
}
QFrame#confirmationBox QLabel {
    font-size: 13px;
    line-height: 1.55;
    color: #635A49;
}
QPushButton#primaryBtn {
    font-family: "Inter";
    font-size: 13px;
    font-weight: 600;
    background: #1E4A3B;
    color: #FCF9F0;
    border: none;
    border-radius: 9px;
    padding: 11px 14px;
}
QPushButton#primaryBtn:hover {
    background: #2A5E4B;
}
QPushButton#primaryBtn:pressed {
    transform: scale(0.97);
}
QPushButton#ghostBtn {
    font-family: "Inter";
    font-size: 13px;
    font-weight: 600;
    background: transparent;
    color: #1E4A3B;
    border: 1px solid rgba(36,31,23,0.14);
    border-radius: 9px;
    padding: 11px 14px;
}
QPushButton#ghostBtn:hover {
    background: rgba(30,74,59,0.06);
}
QPushButton#ghostBtn:pressed {
    transform: scale(0.97);
}
QLabel#footerNote {
    font-size: 11px;
    color: rgba(252,249,240,0.55);
}
"""


# ============================================================================
# Custom Seal Widget (drawn with QPainter)
# ============================================================================
class SealWidget(QLabel):
    """Animated seal with a brass gradient and a checkmark."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(104, 104)
        self._scale = 1.0
        self._rotation = 0.0
        self.animation = QPropertyAnimation(self, b"scale")
        self.animation.setDuration(550)
        self.animation.setStartValue(1.7)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.OutBack)
        self.animation.finished.connect(lambda: self.set_rotation(0))
        self.animation.start()

    def get_scale(self):
        return self._scale

    def set_scale(self, value):
        self._scale = value
        self.update()

    def set_rotation(self, deg):
        self._rotation = deg
        self.update()

    scale = pyqtProperty(float, get_scale, set_scale)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(self._scale, self._scale)
        painter.rotate(self._rotation)

        # Outer circle (brass gradient)
        gradient = QLinearGradient(0, -52, 0, 52)
        gradient.setColorAt(0, QColor("#EFDCA0"))
        gradient.setColorAt(0.5, QColor("#C9A227"))
        gradient.setColorAt(1, QColor("#8E6A1F"))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor("#6E501A"), 1.5))
        painter.drawEllipse(-52, -52, 104, 104)

        # Inner dashed circle
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#6E501A"), 1.0, Qt.DashLine))
        painter.drawEllipse(-44, -44, 88, 88)

        # Text "MWAROKIN ESTATES" (simplified using drawText)
        painter.setPen(QColor("#4E3A12"))
        font = painter.font()
        font.setFamily("JetBrains Mono")
        font.setPixelSize(7)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        painter.setFont(font)
        painter.drawText(QRect(-40, -44, 80, 16), Qt.AlignCenter, "MWAROKIN ESTATES")

        # Checkmark
        painter.setPen(QPen(QColor("#3B2C0F"), 6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        path = QPainterPath()
        path.moveTo(-16, 0)
        path.lineTo(-4, 12)
        path.lineTo(18, -12)
        painter.drawPath(path)

        # Bottom text "VERIFIED PAID"
        painter.setPen(QColor("#4E3A12"))
        font.setPixelSize(7)
        painter.setFont(font)
        painter.drawText(QRect(-40, 26, 80, 16), Qt.AlignCenter, "VERIFIED PAID")


# ============================================================================
# Pulse Animation for Status Dot
# ============================================================================
class StatusDot(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(7, 7)
        self.setStyleSheet("background: #5CD79A; border-radius: 3px;")
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(2200)
        self.animation.setLoopCount(-1)
        self.animation.setStartValue(QRect(0, 0, 7, 7))
        self.animation.setEndValue(QRect(-6, -6, 19, 19))
        self.animation.start()


# ============================================================================
# Main Window
# ============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mwarokin Estates — Payment Confirmation")
        self.setMinimumSize(960, 680)
        self.setStyleSheet(STYLE_SHEET)

        # Central widget and main layout
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # ---- Header ----
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)
        brand = QLabel('<span style="font-family: Fraunces; font-weight:500; font-size:clamp(26px,3.4vw,36px); color:#FCF9F0;">Mwarokin <em style="font-style:italic; color:#D9B759;">Estates</em></span>')
        brand.setObjectName("brandLabel")
        brand.setTextFormat(Qt.RichText)
        status_chip = QLabel("Payment Confirmed")
        status_chip.setObjectName("statusChip")
        dot = StatusDot()
        chip_layout = QHBoxLayout()
        chip_layout.addWidget(dot)
        chip_layout.addWidget(status_chip)
        chip_layout.setSpacing(8)
        chip_widget = QWidget()
        chip_widget.setLayout(chip_layout)

        header_layout.addWidget(brand)
        header_layout.addStretch()
        header_layout.addWidget(chip_widget)
        main_layout.addLayout(header_layout)

        # ---- Tabs ----
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(False)
        self.tabs.setMovable(False)

        # Create tabs
        for key in ["rent", "amenities", "paybill"]:
            tab_widget = self.create_tab_content(key)
            label = PAYMENT_DICT[key].label
            # Add a small index suffix
            index = ["01", "02", "03"][["rent", "amenities", "paybill"].index(key)]
            self.tabs.addTab(tab_widget, f"{label}   {index}")

        self.tabs.currentChanged.connect(self.on_tab_changed)
        main_layout.addWidget(self.tabs)

        # ---- Footer ----
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(26)
        footer_items = [
            ("⏱", "Real-time confirmation"),
            ("📄", "E-receipt available"),
            ("🔓", "Zero convenience fee"),
        ]
        for icon, text in footer_items:
            label = QLabel(f"{icon}  {text}")
            label.setObjectName("footerNote")
            footer_layout.addWidget(label)
        footer_layout.addStretch()
        main_layout.addLayout(footer_layout)

        # Load initial tab
        self.current_key = "rent"
        self.update_ui(self.current_key)

        # Store reference to current tab's right panel for actions
        self.right_panel = None

    # ------------------------------------------------------------------------
    # Create tab content (left + right panels)
    # ------------------------------------------------------------------------
    def create_tab_content(self, key):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Left panel (main receipt)
        left_panel = QFrame()
        left_panel.setObjectName("leftPanel")
        left_panel.setStyleSheet("""
            QFrame#leftPanel {
                background: #FCF9F0;
                border-radius: 6px 0 0 18px;
                padding: 30px;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(16)

        # Success row
        success_row = QHBoxLayout()
        success_row.setSpacing(16)

        check_badge = QLabel()
        check_badge.setFixedSize(52, 52)
        check_badge.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                        stop:0 #2F6B4F, stop:1 #1F4D38);
            border-radius: 26px;
        """)
        check_badge.setAlignment(Qt.AlignCenter)
        # Draw checkmark with QPainter on a pixmap
        pix = QPixmap(52, 52)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#FCF9F0"), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawLine(14, 26, 24, 36)
        painter.drawLine(24, 36, 38, 18)
        painter.end()
        check_badge.setPixmap(pix)

        success_text = QVBoxLayout()
        title = QLabel("Payment successful")
        title.setObjectName("successTitle")
        sub = QLabel("Processed securely — your ledger has been updated in real time.")
        sub.setObjectName("successSub")
        success_text.addWidget(title)
        success_text.addWidget(sub)

        success_row.addWidget(check_badge)
        success_row.addLayout(success_text)
        left_layout.addLayout(success_row)

        # Amount block
        amount_label = QLabel("Amount paid")
        amount_label.setObjectName("amountLabel")
        amount_value = QLabel()
        amount_value.setObjectName("amountValue")
        bill_tag = QLabel()
        bill_tag.setObjectName("billTag")
        left_layout.addWidget(amount_label)
        left_layout.addWidget(amount_value)
        left_layout.addWidget(bill_tag)

        # Details rows (grid)
        details_grid = QGridLayout()
        details_grid.setVerticalSpacing(12)
        details_grid.setHorizontalSpacing(20)
        details_grid.setContentsMargins(0, 12, 0, 12)

        labels = ["Description", "Reference", "Date & time", "Method", "Transaction ID"]
        self.detail_labels = {}
        self.detail_values = {}

        for i, lbl in enumerate(labels):
            label_widget = QLabel(lbl)
            label_widget.setObjectName("detailLabel")
            label_widget.setProperty("class", "detailLabel")
            details_grid.addWidget(label_widget, i, 0, Qt.AlignLeft)

            value_widget = QLabel()
            value_widget.setObjectName("detailValue")
            value_widget.setProperty("class", "detailValue")
            if lbl == "Reference" or lbl == "Transaction ID":
                value_widget.setProperty("class", "detailValue mono")
                value_widget.setStyleSheet("font-family: 'JetBrains Mono'; font-size: 12px;")
            details_grid.addWidget(value_widget, i, 1, Qt.AlignRight)
            self.detail_labels[lbl] = label_widget
            self.detail_values[lbl] = value_widget

        left_layout.addLayout(details_grid)

        # Confirmation note
        note_frame = QFrame()
        note_frame.setObjectName("confirmationBox")
        note_layout = QHBoxLayout(note_frame)
        note_layout.setSpacing(10)
        note_icon = QLabel("📧")
        note_icon.setStyleSheet("font-size: 16px;")
        note_text = QLabel()
        note_text.setWordWrap(True)
        note_layout.addWidget(note_icon)
        note_layout.addWidget(note_text)
        left_layout.addWidget(note_frame)

        # Store references to update later
        self.amount_value = amount_value
        self.bill_tag = bill_tag
        self.note_text = note_text

        # Right panel (stub)
        right_panel = QFrame()
        right_panel.setObjectName("rightPanel")
        right_panel.setStyleSheet("""
            QFrame#rightPanel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #F5EFDE, stop:1 #FCF9F0);
                border-radius: 0 18px 18px 0;
                padding: 30px 25px;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setAlignment(Qt.AlignCenter)
        right_layout.setSpacing(12)

        # Seal
        seal = SealWidget()
        right_layout.addWidget(seal, alignment=Qt.AlignCenter)

        verified_label = QLabel("Verified & secured")
        verified_label.setStyleSheet("font-family: 'Fraunces'; font-weight: 500; font-size: 15px; color: #1E4A3B;")
        right_layout.addWidget(verified_label, alignment=Qt.AlignCenter)

        verified_sub = QLabel("RBC-compliant audit trail")
        verified_sub.setStyleSheet("font-size: 11px; color: #8C8271; letter-spacing: 0.02em;")
        right_layout.addWidget(verified_sub, alignment=Qt.AlignCenter)

        # Buttons
        btn_download = QPushButton("Download receipt")
        btn_download.setObjectName("primaryBtn")
        btn_download.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        btn_download.clicked.connect(self.download_receipt)

        btn_print = QPushButton("Print")
        btn_print.setObjectName("ghostBtn")
        btn_print.setIcon(self.style().standardIcon(QStyle.SP_Printer))
        btn_print.clicked.connect(self.print_receipt)

        btn_copy = QPushButton("Copy transaction ID")
        btn_copy.setObjectName("ghostBtn")
        btn_copy.setIcon(self.style().standardIcon(QStyle.SP_FileDialogContentsView))
        btn_copy.clicked.connect(self.copy_txn)

        right_layout.addWidget(btn_download)
        right_layout.addWidget(btn_print)
        right_layout.addWidget(btn_copy)

        # Divider + security note
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("border-top: 1px dashed rgba(36,31,23,0.14); margin: 12px 0;")
        right_layout.addWidget(divider)

        sec_note = QLabel("🔒  Bank-grade encryption")
        sec_note.setStyleSheet("font-size: 11px; color: #8C8271;")
        right_layout.addWidget(sec_note, alignment=Qt.AlignCenter)

        # Perforation and tear stub (we'll put at bottom of left panel, but easier to add a separate widget after the tab content)
        # Instead, we add a small frame at the bottom of the tab widget, but we'll put it outside the tab content.
        # Since we have the tab widget, we'll add a separate widget below it? But the design shows it inside the card.
        # We'll add a frame at the bottom of the tab's main layout? Actually we can add a separate widget after the tab widget in main layout.

        # We'll handle the perforation and tear stub outside the tab content, as a separate widget in main_layout.
        # But we need it to be part of the card. So we'll add it after the tab widget and style it to look like it's attached.

        # Store right panel for later use (download/print)
        self.right_panel = right_panel

        # Add panels to layout
        layout.addWidget(left_panel, 2)
        layout.addWidget(right_panel, 1)

        # Store references for easy update
        setattr(self, f"tab_{key}", widget)
        return widget

    # ------------------------------------------------------------------------
    # Update UI when tab changes
    # ------------------------------------------------------------------------
    def on_tab_changed(self, index):
        keys = ["rent", "amenities", "paybill"]
        if index < len(keys):
            self.current_key = keys[index]
            self.update_ui(self.current_key)

    def update_ui(self, key):
        data = PAYMENT_DICT[key]
        # Update left panel
        self.amount_value.setText(f"${data.amount:,.2f}")
        self.bill_tag.setText(data.label)
        self.detail_values["Description"].setText(data.description)
        self.detail_values["Reference"].setText(data.reference)
        # Date & time
        now = datetime.now().strftime("%B %d, %Y — %H:%M EAT")
        self.detail_values["Date & time"].setText(now)
        self.detail_values["Method"].setText(data.method)
        self.detail_values["Transaction ID"].setText(data.txn_id)
        self.note_text.setText(data.confirmation)

        # Update tear stub (we'll do later)
        # We'll store the txn id in a variable and update a label in the tear stub widget.
        self.current_txn = data.txn_id

        # Restart seal animation
        # We need to find the seal widget in the right panel
        for child in self.right_panel.children():
            if isinstance(child, SealWidget):
                child.animation.stop()
                child.set_scale(1.7)
                child.set_rotation(-18)
                child.animation.start()
                break

    # ------------------------------------------------------------------------
    # Helper: generate receipt HTML
    # ------------------------------------------------------------------------
    def generate_receipt_html(self):
        data = PAYMENT_DICT[self.current_key]
        now = datetime.now().strftime("%B %d, %Y — %H:%M EAT")
        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Mwarokin Estates Receipt — {data.reference}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: 'Inter', sans-serif; background: #0E211B; margin:0; padding:48px 16px; display:flex; justify-content:center; color:#241F17; }}
  .receipt {{ width:100%; max-width:480px; background:#FCF9F0; border-radius:6px 18px 18px 18px; box-shadow:0 30px 60px -20px rgba(0,0,0,0.5); overflow:hidden; }}
  .head {{ padding:32px 32px 20px; text-align:center; border-bottom:1px dashed rgba(36,31,23,0.14); }}
  .head .brand {{ font-family: 'Fraunces', serif; font-weight:600; font-size:24px; margin:0; color:#1E4A3B; }}
  .head .tag {{ font-family: 'JetBrains Mono', monospace; font-size:10px; letter-spacing:.16em; text-transform:uppercase; color:#B68A2E; margin:6px 0 0; }}
  .seal-wrap {{ display:flex; justify-content:center; margin:22px 0 4px; }}
  .amount {{ font-family: 'Fraunces', serif; font-weight:600; font-size:40px; text-align:center; color:#1E4A3B; margin:6px 0 2px; }}
  .status {{ text-align:center; font-size:12px; color:#2F6B4F; font-weight:600; letter-spacing:.04em; margin-bottom:24px; }}
  .rows {{ padding:0 32px 8px; }}
  .row {{ display:flex; justify-content:space-between; gap:10px; padding:11px 0; border-bottom:1px dotted rgba(36,31,23,0.14); font-size:13px; }}
  .row .l {{ color:#635A49; }} .row .v {{ font-weight:500; text-align:right; }}
  .mono {{ font-family: 'JetBrains Mono', monospace; font-size:12px; }}
  .note {{ margin:20px 32px; padding:14px 16px; background:rgba(30,74,59,0.06); border:1px solid rgba(30,74,59,0.15); border-radius:10px; font-size:12.5px; line-height:1.6; color:#635A49; }}
  .foot {{ text-align:center; padding:18px 32px 30px; font-size:11px; color:#8C8271; }}
  @media print {{ body{{background:#fff;padding:0;}} .receipt{{box-shadow:none;}} }}
</style>
</head>
<body>
<div class="receipt">
  <div class="head">
    <p class="brand">Mwarokin Estates</p>
    <p class="tag">Official Payment Receipt</p>
  </div>
  <div class="seal-wrap">
    <svg width="88" height="88" viewBox="0 0 120 120">
      <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#EFDCA0"/><stop offset="50%" stop-color="#C9A227"/><stop offset="100%" stop-color="#8E6A1F"/>
      </linearGradient></defs>
      <circle cx="60" cy="60" r="56" fill="url(#g)"/>
      <circle cx="60" cy="60" r="47" fill="none" stroke="#6E501A" stroke-width="1" stroke-dasharray="2 3"/>
      <path d="M40 62l13 13 26-28" fill="none" stroke="#3B2C0F" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  </div>
  <p class="amount">${data.amount:,.2f}</p>
  <p class="status">PAID & CONFIRMED</p>
  <div class="rows">
    <div class="row"><span class="l">Bill type</span><span class="v">{data.label}</span></div>
    <div class="row"><span class="l">Description</span><span class="v">{data.description}</span></div>
    <div class="row"><span class="l">Reference</span><span class="v mono">{data.reference}</span></div>
    <div class="row"><span class="l">Transaction ID</span><span class="v mono">{data.txn_id}</span></div>
    <div class="row"><span class="l">Date & time</span><span class="v">{now}</span></div>
    <div class="row" style="border-bottom:none;"><span class="l">Method</span><span class="v">{data.method}</span></div>
  </div>
  <div class="note">{data.confirmation}</div>
  <div class="foot">This is a digitally issued receipt from Mwarokin Estates.<br>Keep it for your records.</div>
</div>
</body>
</html>"""
        return html

    # ------------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------------
    def download_receipt(self):
        html = self.generate_receipt_html()
        data = PAYMENT_DICT[self.current_key]
        filename = f"Mwarokin_Receipt_{data.reference}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
        QMessageBox.information(self, "Download", f"Receipt saved as {filename}")

    def print_receipt(self):
        html = self.generate_receipt_html()
        # Save to temporary file and open in default browser with print dialog
        fd, path = tempfile.mkstemp(suffix=".html", prefix="mwarokin_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html)
        webbrowser.open(path)
        QMessageBox.information(self, "Print", "Receipt opened in browser. Use browser's print function.")

    def copy_txn(self):
        data = PAYMENT_DICT[self.current_key]
        clipboard = QApplication.clipboard()
        clipboard.setText(data.txn_id)
        QMessageBox.information(self, "Copied", f"Transaction ID copied: {data.txn_id}")


# ============================================================================
# Application Entry Point
# ============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # Load fonts (optional, but we use system fonts)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
