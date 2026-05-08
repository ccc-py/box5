from fastapi import FastAPI, WebSocket

app = FastAPI()

@app.websocket('/test')
async def test_ws(websocket):
    await websocket.accept()
    await websocket.send_text('hello')
    await websocket.close()