"""CDP spike: prove frames stream AND input lands correctly at a NON-1:1 canvas scale."""
import asyncio, base64, json, sys
sys.path.insert(0, "/Users/dhiren/Deccan AI/E Commerce Broswer Gym")

async def main():
    import uvicorn, websockets, urllib.request
    from live_browser.service import app, VIEWPORT_W, VIEWPORT_H

    cfg = uvicorn.Config(app, host="127.0.0.1", port=8877, log_level="error")
    server = uvicorn.Server(cfg)
    task = asyncio.create_task(server.serve())
    for _ in range(100):
        await asyncio.sleep(0.1)
        if server.started: break

    def post(path, body):
        r = urllib.request.Request("http://127.0.0.1:8877"+path, data=json.dumps(body).encode(),
                                   headers={"content-type":"application/json"}, method="POST")
        return json.loads(urllib.request.urlopen(r, timeout=60).read())
    def get(path):
        return json.loads(urllib.request.urlopen("http://127.0.0.1:8877"+path, timeout=30).read())

    print("1. open a live session on the gym")
    s = await asyncio.to_thread(post, "/live/sessions", {"url": "http://localhost:8000/", "owner": "diego@deccan.ai"})
    sid, ticket = s["session_id"], s["ticket"]
    print(f"   session={sid} viewport={s['viewport']}")

    print("2. connect the stream websocket")
    url = f"ws://127.0.0.1:8877/live/stream/{sid}?ticket={ticket}"
    async with websockets.connect(url, origin="http://localhost:8080") as ws:
        hello = json.loads(await ws.recv())
        print(f"   hello: controller={hello['controller']} viewport={hello['viewport']}")

        frames = []
        for _ in range(3):
            m = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
            if m.get("type") == "frame":
                frames.append(m)
        px = base64.b64decode(frames[0]["data"])
        print(f"   FRAMES: got {len(frames)}, first={len(px)} bytes, jpeg={px[:2]==b'\\xff\\xd8'}")

        before = (await asyncio.to_thread(get, f"/live/sessions/{sid}"))["url"]
        print(f"3. click a link using NORMALIZED coords (canvas scale-agnostic)")
        # Find a real link's centre as a FRACTION of the viewport, simulating a
        # client whose canvas is a different size than 1280x800.
        from live_browser.service import SESSIONS
        sess = SESSIONS[sid]
        box = await sess.page.locator("a[href*='/cart']").first.bounding_box()
        nx, ny = (box["x"]+box["width"]/2)/VIEWPORT_W, (box["y"]+box["height"]/2)/VIEWPORT_H
        print(f"   target box={box} -> normalized=({nx:.4f}, {ny:.4f})")
        # A client canvas of 900x563 would have sent these pixel coords:
        print(f"   (a 900x563 canvas would send px ({nx*900:.0f},{ny*563:.0f}) - wrong if sent raw)")

        await ws.send(json.dumps({"type":"click","id":1,"nx":nx,"ny":ny}))
        ack = None
        while ack is None:
            m = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
            if m.get("type") == "ack": ack = m
        print(f"   ack: {ack}")
        await asyncio.sleep(2.0)
        after = (await asyncio.to_thread(get, f"/live/sessions/{sid}"))["url"]
        print(f"   URL before={before}")
        print(f"   URL after ={after}")
        print(f"   CLICK LANDED CORRECTLY: {after != before and '/cart' in after}")

        print("4. stale/replayed input is rejected")
        await ws.send(json.dumps({"type":"click","id":1,"nx":0.5,"ny":0.5}))
        m = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
        while m.get("type") != "ack": m = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
        print(f"   replay ack: applied={m.get('applied')} reason={m.get('reason')}")

    print("5. security checks")
    try:
        async with websockets.connect(f"ws://127.0.0.1:8877/live/stream/{sid}?ticket=bogus.x.y", origin="http://localhost:8080"):
            print("   BAD ticket accepted  <-- FAIL")
    except Exception as e:
        print(f"   bad ticket rejected: {type(e).__name__}")
    try:
        async with websockets.connect(f"ws://127.0.0.1:8877/live/stream/{sid}?ticket={ticket}", origin="http://evil.example"):
            print("   (origin allowlist is '*' in dev, so this is expected to pass)")
    except Exception as e:
        print(f"   bad origin rejected: {type(e).__name__}")

    await asyncio.to_thread(post, f"/live/sessions/{sid}/close", {})
    print("6. closed:", await asyncio.to_thread(get, "/live/health"))
    server.should_exit = True
    await task

asyncio.run(main())
