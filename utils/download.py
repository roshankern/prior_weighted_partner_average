"""Download a file over HTTP in parallel byte ranges, then check its checksum. Used by the 0.datasets download notebooks."""

import hashlib
import http.client
import os
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
    none; a mismatch keeps the .part file and raises. Returns the file's sha256 when no checksum was given."""
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
    with open(part, "wb") as f:
        if size is None:  # no byte ranges: one stream
            with _open(url) as r:
                while chunk := r.read(CHUNK):
                    f.write(chunk)
        else:
            f.truncate(size)
            step = -(-size // streams)

            def fetch(first):
                last = min(first + step, size) - 1
                for attempt in range(8):  # servers drop or refuse (503) some of many connections; resume where it stopped
                    try:
                        with _open(url, first, last) as r:
                            assert r.status == 206, (url, r.status)
                            while chunk := r.read(CHUNK):
                                os.pwrite(f.fileno(), chunk, first)
                                first += len(chunk)
                        break
                    except (OSError, http.client.HTTPException) as e:  # URLError, HTTPError, timeouts, cut connections
                        if attempt == 7:
                            raise
                        print(f"{path.name}: retry {attempt + 1} at byte {first}: {e}", flush=True)
                        time.sleep(30 * 2**attempt)
                assert first == last + 1, (url, first, last)

            with ThreadPoolExecutor(streams) as pool:
                list(pool.map(fetch, range(0, size, step)))  # list() re-raises a failed range
    h = hashlib.new(algo if digest else "sha256")
    with open(part, "rb") as f:
        while chunk := f.read(CHUNK):
            h.update(chunk)
    assert not digest or h.hexdigest() == digest, f"{path.name}: {algo} differs, kept as {part}"
    part.rename(path)
    return None if digest else h.hexdigest()
