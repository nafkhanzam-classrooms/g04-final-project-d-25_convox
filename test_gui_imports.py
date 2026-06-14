#!/usr/bin/env python3
"""Quick validation of GUI module imports and architecture."""

import sys


def test_imports() -> bool:
    try:
        print("Testing GUI module imports...")

        # Controllers
        from gui.controllers.event_dispatcher import EventDispatcher, get_dispatcher  # noqa: F401
        print("✓ event_dispatcher.py")
        from gui.controllers.tcp_controller import TCPController, TCPWorker  # noqa: F401
        print("✓ tcp_controller.py")
        from gui.controllers.udp_voice_controller import UDPVoiceController  # noqa: F401
        print("✓ udp_voice_controller.py")
        from gui.controllers.gui_state_manager import GuiStateManager  # noqa: F401
        print("✓ gui_state_manager.py")

        # Models
        from gui.models.app_model import (  # noqa: F401
            ApplicationModel,
            FileTransfer,
            Friend,
            Message,
            Room,
            User,
            UserStatus,
        )
        print("✓ app_model.py")

        # Styles
        from gui.styles import colors  # noqa: F401
        from gui.styles.theme import apply_theme, load_theme  # noqa: F401
        print("✓ styles/theme.py + colors.py")

        # Windows
        from gui.windows.login_window import LoginWindow  # noqa: F401
        from gui.windows.dashboard_window import DashboardWindow  # noqa: F401
        from gui.windows.chat_window import ChatWindow  # noqa: F401
        print("✓ windows: login_window.py, dashboard_window.py, chat_window.py")

        # Widgets
        from gui.widgets.room_sidebar import RoomSidebar  # noqa: F401
        from gui.widgets.chat_area import ChatArea  # noqa: F401
        from gui.widgets.message_bubble import MessageBubble  # noqa: F401
        from gui.widgets.online_users import OnlineUserPanel  # noqa: F401
        from gui.widgets.friend_panel import FriendPanel  # noqa: F401
        from gui.widgets.voice_controls import VoiceControls  # noqa: F401
        from gui.widgets.upload_widget import UploadWidget  # noqa: F401
        from gui.widgets.notification_widget import NotificationWidget  # noqa: F401
        print("✓ widgets")

        # App
        from gui.app import ConvoxGuiApp  # noqa: F401
        print("✓ app.py")

        # Auth (server-side, used to ensure protocol stays in sync)
        from server.auth import AuthService, hash_password, verify_password  # noqa: F401
        print("✓ server/auth.py")

        from protocol.packet import PacketType
        for required in ("LOGIN", "REGISTER", "AUTH_SUCCESS", "AUTH_FAILED", "SESSION_ACK"):
            assert hasattr(PacketType, required), f"missing PacketType.{required}"
        print("✓ packet types: LOGIN/REGISTER/AUTH_SUCCESS/AUTH_FAILED/SESSION_ACK")

        print("\n✅ All imports successful!")
        return True
    except ImportError as exc:
        print(f"\n❌ Import failed: {exc}")
        print("Install GUI deps with: pip install PyQt6")
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"\n❌ Error: {exc}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    sys.exit(0 if test_imports() else 1)
