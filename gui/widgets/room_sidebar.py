"""Room sidebar widget for Convox GUI."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from gui.controllers.tcp_controller import TCPController
from utils.logger import get_logger


class RoomSidebar(QWidget):
    """Sidebar showing available rooms."""

    room_changed = pyqtSignal(str)  # room_name

    def __init__(self, tcp_controller: TCPController):
        super().__init__()
        self.logger = get_logger("RoomSidebar")
        self.tcp_controller = tcp_controller
        self.current_room = "global"
        self.rooms = {"global": 0}  # room_name -> unread_count

        self.init_ui()
        self.setMinimumWidth(200)
        self.setMaximumWidth(250)

    def init_ui(self) -> None:
        """Initialize UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title
        title = QWidget()
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(10, 10, 10, 10)

        title_label = QWidget()
        title_label_text = "Rooms"
        title_label_font = QFont()
        title_label_font.setBold(True)
        
        # Create label manually
        from PyQt6.QtWidgets import QLabel
        title_text = QLabel(title_label_text)
        title_text.setFont(title_label_font)
        title_text.setStyleSheet("color: #ffffff; font-size: 13px;")
        title_layout.addWidget(title_text)
        title_layout.addStretch()

        title.setLayout(title_layout)
        title.setStyleSheet("background-color: #1e1e1e; border-bottom: 1px solid #404040;")
        title.setMaximumHeight(40)
        layout.addWidget(title)

        # Room list
        self.room_list = QListWidget()
        self.room_list.itemClicked.connect(self.on_room_selected)
        self.room_list.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                border: none;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px 5px;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
            QListWidget::item:hover {
                background-color: #353535;
            }
        """)
        layout.addWidget(self.room_list)

        # Add initial global room
        self.add_room("global")

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(10, 10, 10, 10)
        button_layout.setSpacing(5)

        create_btn = QPushButton("+ New")
        create_btn.setMinimumHeight(30)
        create_btn.clicked.connect(self.create_room)
        create_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1084d7;
            }
        """)
        button_layout.addWidget(create_btn)

        join_btn = QPushButton("Join")
        join_btn.setMinimumHeight(30)
        join_btn.clicked.connect(self.join_room)
        join_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2fb34e;
            }
        """)
        button_layout.addWidget(join_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setStyleSheet("background-color: #2b2b2b;")

    def add_room(self, room_name: str) -> None:
        """Add room to sidebar."""
        if room_name in self.rooms:
            return

        self.rooms[room_name] = 0

        item = QListWidgetItem(room_name)
        item.setData(Qt.ItemDataRole.UserRole, room_name)
        self.room_list.addItem(item)

        if room_name == "global":
            self.room_list.setCurrentItem(item)
            self.current_room = room_name

    def on_room_selected(self, item: QListWidgetItem) -> None:
        """Handle room selection."""
        room_name = item.data(Qt.ItemDataRole.UserRole)
        self.current_room = room_name
        self.room_list.setCurrentItem(item)
        self.room_changed.emit(room_name)
        self.logger.info("Room selected: %s", room_name)

    def create_room(self) -> None:
        """Create new room dialog."""
        room_name, ok = QInputDialog.getText(
            self,
            "Create Room",
            "Room name:"
        )
        if ok and room_name:
            self.tcp_controller.create_room(room_name)
            self.logger.info("Creating room: %s", room_name)

    def join_room(self) -> None:
        """Join room dialog."""
        room_name, ok = QInputDialog.getText(
            self,
            "Join Room",
            "Room name:"
        )
        if ok and room_name:
            self.tcp_controller.join_room(room_name)
            self.add_room(room_name)
            self.logger.info("Joining room: %s", room_name)

    def update_room_unread(self, room_name: str) -> None:
        """Update unread count for room."""
        if room_name in self.rooms:
            self.rooms[room_name] += 1
            for i in range(self.room_list.count()):
                item = self.room_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == room_name:
                    unread = self.rooms[room_name]
                    if unread > 0:
                        item.setText(f"{room_name} ({unread})")
                    break
