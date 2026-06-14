"""End-to-end auth-handshake test against a real ConvoxServer instance.

Boots the server on an ephemeral port, then drives the auth flow with a
plain TCP client - no Qt or terminal client involved - to make sure the
wire protocol matches both sides.

To avoid conflicts with the persistent ``database/convox.db`` we use
fresh, randomised usernames per run instead of swapping out the
database backend.
"""

import os
import socket
import sys
import threading
import time
import unittest
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from protocol.packet import PacketType, build_packet, receive_packet  # noqa: E402


def _send(sock: socket.socket, packet_type: PacketType, **fields) -> None:
    sock.sendall(build_packet(packet_type, **fields))


def _unique(stub: str) -> str:
    return f"{stub}_{uuid.uuid4().hex[:6]}"


class AuthHandshakeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from server.server import ConvoxServer  # local import to defer DB init

        cls.server = ConvoxServer()
        cls.server.server_socket.bind(("127.0.0.1", 0))
        cls.server.server_socket.listen(8)
        cls.host, cls.port = cls.server.server_socket.getsockname()

        def _accept_loop() -> None:
            try:
                while True:
                    conn, addr = cls.server.server_socket.accept()
                    threading.Thread(
                        target=cls.server.handle_client,
                        args=(conn, addr),
                        daemon=True,
                    ).start()
            except OSError:
                return

        cls._thread = threading.Thread(target=_accept_loop, daemon=True)
        cls._thread.start()
        time.sleep(0.05)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            cls.server.server_socket.close()
        except OSError:
            pass

    def _connect(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.port))
        sock.settimeout(2.0)
        return sock

    def test_register_then_login(self) -> None:
        username = _unique("alice")
        sock = self._connect()
        try:
            _send(sock, PacketType.REGISTER, username=username, password="hunter22")
            response = receive_packet(sock)
            self.assertIsNotNone(response)
            self.assertEqual(response["type"], PacketType.AUTH_SUCCESS.value)

            _send(sock, PacketType.LOGIN, username=username, password="hunter22")
            ack1 = receive_packet(sock)
            self.assertIsNotNone(ack1)
            self.assertEqual(ack1["type"], PacketType.AUTH_SUCCESS.value)
            self.assertEqual(ack1.get("username"), username)
            self.assertTrue(ack1.get("session_token"))

            ack2 = receive_packet(sock)
            self.assertIsNotNone(ack2)
            self.assertEqual(ack2["type"], PacketType.SESSION_ACK.value)
        finally:
            sock.close()

    def test_login_with_wrong_password_is_rejected(self) -> None:
        username = _unique("bob")
        # Register through a quick session
        sock = self._connect()
        try:
            _send(sock, PacketType.REGISTER, username=username, password="rightpass")
            self.assertEqual(
                receive_packet(sock)["type"], PacketType.AUTH_SUCCESS.value
            )
        finally:
            sock.close()

        sock = self._connect()
        try:
            _send(sock, PacketType.LOGIN, username=username, password="wrongpass")
            response = receive_packet(sock)
            self.assertIsNotNone(response)
            self.assertEqual(response["type"], PacketType.AUTH_FAILED.value)
        finally:
            sock.close()

    def test_register_duplicate_is_rejected(self) -> None:
        username = _unique("carol")
        sock = self._connect()
        try:
            _send(sock, PacketType.REGISTER, username=username, password="goodpass")
            self.assertEqual(
                receive_packet(sock)["type"], PacketType.AUTH_SUCCESS.value
            )

            _send(sock, PacketType.REGISTER, username=username, password="otherpass")
            second = receive_packet(sock)
            self.assertEqual(second["type"], PacketType.AUTH_FAILED.value)
        finally:
            sock.close()


if __name__ == "__main__":
    unittest.main()
