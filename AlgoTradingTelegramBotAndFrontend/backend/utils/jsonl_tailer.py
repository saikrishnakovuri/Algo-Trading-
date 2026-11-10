import asyncio
import json
import os

import asyncio
import json
import os

async def tail_jsonl(file_path, last_n=100):
    if not os.path.exists(file_path):
        return []
    
    with open(file_path, 'rb') as f:
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        buffer = []
        pointer = file_size - 1
        
        # Backward seek for lines
        while len(buffer) < last_n and pointer >= 0:
            f.seek(pointer)
            byte = f.read(1)
            if byte == b'\n':
                if pointer < file_size - 1: # Found a full line
                    buffer.insert(0, f.readline().decode('utf-8').strip())
            pointer -= 1
            if pointer < 0: # Hit start of file
                f.seek(0)
                buffer.insert(0, f.readline().decode('utf-8').strip())
        
        # Filter empty strings and parse JSON
        results = []
        for line in buffer:
            if line:
                try:
                    results.append(json.loads(line))
                except:
                    continue
        return results[-last_n:]

async def watch_jsonl(file_path, callback):
    if not os.path.exists(file_path):
        return
    
    with open(file_path, 'r') as f:
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                await asyncio.sleep(0.5)
                continue
            try:
                data = json.loads(line)
                await callback(data)
            except:
                pass
