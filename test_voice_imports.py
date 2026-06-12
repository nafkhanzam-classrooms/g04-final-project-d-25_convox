#!/usr/bin/env python3
"""Quick validation of Phase 4 voice module imports and syntax."""

import sys

def test_imports():
    """Test that all voice modules can be imported."""
    try:
        print("Testing voice module imports...")
        
        from voice.voice_packet import VoicePacket, VoiceControl
        print("✓ voice_packet.py")
        
        from voice.jitter_buffer import JitterBuffer
        print("✓ jitter_buffer.py")
        
        from voice.codec import SAMPLE_RATE, FRAME_SIZE, encode_pcm, decode_pcm
        print("✓ codec.py")
        
        from voice.voice_room import VoiceRoom, VoiceRoomManager
        print("✓ voice_room.py")
        
        from voice.udp_server import UDPVoiceServer
        print("✓ udp_server.py")
        
        from voice.udp_client import UDPVoiceClient
        print("✓ udp_client.py")
        
        from voice.audio_capture import AudioCapture
        print("✓ audio_capture.py")
        
        from voice.audio_playback import AudioPlayback
        print("✓ audio_playback.py")
        
        from voice import VoicePacket, VoiceRoomManager, JitterBuffer, UDPVoiceServer
        print("✓ voice/__init__.py")
        
        from protocol.packet import PacketType
        assert hasattr(PacketType, 'VOICE_START')
        assert hasattr(PacketType, 'VOICE_STOP')
        assert hasattr(PacketType, 'VOICE_STATUS')
        print("✓ protocol packet types")
        
        from server.service import ConvoxService
        print("✓ server service imports")
        
        from client.client_app import ConvoxClient
        print("✓ client app imports")
        
        print("\n✅ All imports successful!")
        return True
    except Exception as exc:
        print(f"\n❌ Import failed: {exc}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
