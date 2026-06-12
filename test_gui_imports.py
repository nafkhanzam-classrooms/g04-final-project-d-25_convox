#!/usr/bin/env python3
"""Quick validation of Phase 5 GUI module imports and architecture."""

import sys

def test_imports():
    """Test that all GUI modules can be imported."""
    try:
        print("Testing GUI module imports...")

        # Event dispatcher
        from gui.controllers.event_dispatcher import get_dispatcher, EventDispatcher
        print("✓ event_dispatcher.py")

        # TCP controller
        from gui.controllers.tcp_controller import TCPController, TCPWorker
        print("✓ tcp_controller.py")

        # Models
        from gui.models.app_model import ApplicationModel, User, Room, Message, Friend, FileTransfer
        print("✓ app_model.py")

        # Windows
        from gui.windows.login_window import LoginWindow
        print("✓ login_window.py")

        from gui.windows.dashboard_window import DashboardWindow
        print("✓ dashboard_window.py")

        # Widgets
        from gui.widgets.room_sidebar import RoomSidebar
        print("✓ room_sidebar.py")

        from gui.widgets.chat_area import ChatArea
        print("✓ chat_area.py")

        from gui.widgets.online_users import OnlineUserPanel
        print("✓ online_users.py")

        from gui.widgets.voice_controls import VoiceControls
        print("✓ voice_controls.py")

        from gui.widgets.upload_widget import UploadWidget
        print("✓ upload_widget.py")

        from gui.widgets.notification_widget import NotificationWidget
        print("✓ notification_widget.py")

        # Main app
        from gui.app import ConvoxGuiApp
        print("✓ app.py")

        print("\n✅ All imports successful!")
        print("\nArchitecture Summary:")
        print("  - Event Dispatcher: Central signal hub for realtime GUI updates")
        print("  - TCP Controller: Threaded TCP communication with server")
        print("  - Application Model: Client-side state management")
        print("  - Windows: Login, Dashboard (main UI)")
        print("  - Widgets: Chat, Rooms, Users, Voice, Upload, Notifications")
        print("\nSignal-Slot Flow:")
        print("  TCP Worker Thread → Event Dispatcher → GUI Widgets")
        print("  (non-blocking, thread-safe communication)")
        print("\n✅ PyQt6 GUI Phase 5 ready for UI testing!")

        return True
    except ImportError as exc:
        print(f"\n❌ Import failed: {exc}")
        print("\nNote: PyQt6 must be installed to run GUI")
        print("Install with: pip install PyQt6")
        return False
    except Exception as exc:
        print(f"\n❌ Error: {exc}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
