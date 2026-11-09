"""Download a file over HTTP in parallel byte ranges, then check its checksum. Used by the 0.datasets download notebooks."""

import hashlib
import http.client
import os
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

CHUNK = 1 << 24


def _open(url, first=None, last=None):
    headers = {"User-Agent": "agent-local"}
    if first is not None:
        headers["Range"] = f"bytes={first}-{last}"
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120)


def download(url, path, checksum="", streams=16):
    """Fetch `url` into `path` through `path`.part, in `streams` parallel byte ranges when the server allows them (one
    connection is slow from the cluster's compute nodes). `checksum` is "md5:<hex>", "sha256:<hex>", or empty or "-" for
    none; a mismatch keeps the .part file and raises. Returns the file's sha256 when no checksum was given. A stopped
    download (a failed range, a preempted job) resumes from the .part file and its .progress file, which holds the next
    byte to fetch of each range."""
    algo, _, digest = checksum.partition(":")
    if "ncbi.nlm.nih.gov" in url:  # NCBI refuses (503) more than a few connections at once
        streams = min(streams, 4)
    part = path.with_name(path.name + ".part")
    for attempt in range(5):
        try:
            with _open(url, 0, 0) as r:  # a 206 reply means byte ranges work, and Content-Range carries the size
                size = int(r.headers["Content-Range"].split("/")[1]) if r.status == 206 else None
            break
        except (OSError, http.client.HTTPException):
            if attempt == 4:
                raise
            time.sleep(60 * 2**attempt)
    if size is None:  # no byte ranges: one stream
        with open(part, "wb") as f, _open(url) as r:
            while chunk := r.read(CHUNK):
                f.write(chunk)
    else:
        step = -(-size // streams)
        starts = range(0, size, step)
        progress = path.with_name(path.name + ".progress")
        done, resume = {s: s for s in starts}, False  # range start -> next byte to fetch
        if part.exists() and progress.exists() and part.stat().st_size == size:
            saved = dict(tuple(map(int, line.split())) for line in progress.read_text().splitlines())
            if set(saved) == set(starts):  # not written with another number of streams
                done, resume = saved, True
        lock = threading.Lock()
        with open(part, "r+b" if resume else "wb") as f:
            f.truncate(size)

            def fetch(start):
                first, last = done[start], min(start + step, size) - 1
                for attempt in range(8):  # servers drop or refuse (503) some of many connections; resume where it stopped
                    if first > last:
                        break
                    try:
                        with _open(url, first, last) as r:
                            assert r.status == 206, (url, r.status)
                            while chunk := r.read(CHUNK):
                                os.pwrite(f.fileno(), chunk, first)
                                first += len(chunk)
                                with lock:
                                    done[start] = first
                                    progress.with_suffix(".tmp").write_text("".join(f"{k} {v}\n" for k, v in done.items()))
                                    progress.with_suffix(".tmp").replace(progress)
                        if first <= last:  # the server closed the connection cleanly before the end of the range
                            raise ConnectionError(f"closed at byte {first} of {last}")
                        break
                    except (OSError, http.client.HTTPException) as e:  # URLError, HTTPError, timeouts, cut connections
                        if attempt == 7:
                            raise
                        print(f"{path.name}: retry {attempt + 1} at byte {first}: {e}", flush=True)
                        time.sleep(30 * 2**attempt)
                assert first == last + 1, (url, first, last)

            with ThreadPoolExecutor(streams) as pool:
                list(pool.map(fetch, starts))  # list() re-raises a failed range
        progress.unlink()  # complete; a checksum mismatch below then restarts from scratch
    h = hashlib.new(algo if digest else "sha256")
    with open(part, "rb") as f:
        while chunk := f.read(CHUNK):
            h.update(chunk)
    assert not digest or h.hexdigest() == digest, f"{path.name}: {algo} differs, kept as {part}"
    part.rename(path)
    return None if digest else h.hexdigest()
