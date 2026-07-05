#!/usr/bin/env python3
import asyncio
import sys
import httpx

async def main():
    url = "http://127.0.0.1:3333/sse"
    post_url = None

    async def read_sse():
        nonlocal post_url
        timeout = httpx.Timeout(None)
        
        while True:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream("GET", url) as response:
                        response.raise_for_status()
                        current_event = None
                        
                        async for line in response.aiter_lines():
                            if line.startswith("event: "):
                                current_event = line[7:].strip()
                            elif line.startswith("data: "):
                                data = line[6:].strip()
                                if current_event == "endpoint":
                                    if data.startswith("http"):
                                        post_url = data
                                    else:
                                        post_url = "http://127.0.0.1:3333" + data
                                else:
                                    # It's a JSON-RPC message, pass to stdout
                                    sys.stdout.write(data + "\n")
                                    sys.stdout.flush()
            except Exception as e:
                sys.stderr.write(f"SSE connection error: {e}\n")
                sys.stderr.flush()
                await asyncio.sleep(2) # Retry connection

    async def read_stdin():
        loop = asyncio.get_running_loop()
        timeout = httpx.Timeout(30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            while True:
                line = await loop.run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                
                # Wait until SSE gives us the POST endpoint
                while post_url is None:
                    await asyncio.sleep(0.1)
                
                try:
                    await client.post(post_url, content=line, headers={"Content-Type": "application/json"})
                except Exception as e:
                    sys.stderr.write(f"POST error: {e}\n")
                    sys.stderr.flush()

    await asyncio.gather(read_sse(), read_stdin())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
