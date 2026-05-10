import pytest
import websockets
import asyncio
import json
import os


def test_terminal_websocket():
    container_port = os.getenv("TEST_CONTAINER_PORT", "56820")
    uri = f"ws://localhost:{container_port}/ws/editor"

    async def run_test():
        try:
            async with websockets.connect(uri) as ws:
                # Init shell
                await ws.send('<message type="terminal_input"><command></command><cwd>./</cwd></message>')
                
                # Consume prompt
                for _ in range(5):
                    try:
                        await asyncio.wait_for(ws.recv(), timeout=0.5)
                    except asyncio.TimeoutError:
                        break
                        
                # Send raw data
                data_json = json.dumps("ls\r")
                req = f'<message type="terminal_input"><raw_data>{data_json}</raw_data></message>'
                await ws.send(req)
                
                # Check response
                res = await asyncio.wait_for(ws.recv(), timeout=2.0)
                assert res is not None
                assert "terminal_output" in res
                
                # Send exit
                await ws.send('<message type="terminal_input"><command>exit</command></message>')
        except Exception as e:
            pytest.fail(f"WebSocket test failed: {e}")

    asyncio.run(run_test())


def test_terminal_command_execution():
    container_port = os.getenv("TEST_CONTAINER_PORT", "56820")
    uri = f"ws://localhost:{container_port}/ws/editor"

    async def run_test():
        try:
            async with websockets.connect(uri) as ws:
                # Init shell
                await ws.send('<message type="terminal_input"><command></command><cwd>/tmp/box5</cwd></message>')
                
                # Consume prompt
                for _ in range(5):
                    try:
                        await asyncio.wait_for(ws.recv(), timeout=0.5)
                    except asyncio.TimeoutError:
                        break
                        
                # Send echo command
                data_json = json.dumps("echo hello_world\r")
                req = f'<message type="terminal_input"><raw_data>{data_json}</raw_data></message>'
                await ws.send(req)
                
                # Check response contains echo output
                found_echo = False
                for _ in range(10):
                    try:
                        res = await asyncio.wait_for(ws.recv(), timeout=2.0)
                        if "hello_world" in res:
                            found_echo = True
                            break
                    except asyncio.TimeoutError:
                        break
                
                assert found_echo, "Echo output not found in terminal response"
                
                # Exit shell
                await ws.send('<message type="terminal_input"><command>exit</command></message>')
        except Exception as e:
            pytest.fail(f"WebSocket command test failed: {e}")

    asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])