#!/usr/bin/env python3
# Copyright (c) 2025 Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause

from multiprocessing import Pool
import os
import sys
from time import sleep
from typing import List

import requests

gh_token = os.environ["ACTIONS_RUNTIME_TOKEN"]


def upload_file(args):
    """
    Uploads a file to our file upload service. The service is a GCP CloudRun
    project that returns signed URLs to Google Storage objects we can upload to.
    """
    try:
        url, base, name = args

        headers = {
            "Authentication": f"Bearer {gh_token}",
        }

        # Obtain the signed-url for GCS using Fibonacci backoff/retries
        for x in (1, 2, 3, 5, 0):
            r = requests.put(url, headers=headers, allow_redirects=False)
            if not r.ok:
                correlation_id = r.headers.get("X-Correlation-ID", "?")
                if not x:
                    return (
                        name,
                        f"Unable to get signed url HTTP_{r.status_code}. Correlation ID: {correlation_id} - {r.text}",
                    )
                else:
                    print(
                        f"Error getting signed URL for {name}: Correlation ID: {correlation_id} HTTP_{r.status_code} - {r.text}\n"
                        f"Retrying in {x} seconds",
                        flush=True,
                        file=sys.stderr,
                    )
                    sleep(x)

        # Upload the file to the signed URL with backoff/retry logic
        url = r.headers["location"]
        path = os.path.join(base, name)
        for x in (1, 2, 3, 0):
            try:
                r = requests.put(
                    url,
                    data=open(path, "rb"),
                    headers={"Content-type": "application/octet-stream"},
                )
            except Exception as e:
                print(
                    f"Unexpected error uploading {name}: {e}",
                    flush=True,
                    file=sys.stderr,
                )
                sleep(x)
                continue
            if not r.ok:
                if not x:
                    return (
                        name,
                        f"Unable to upload content HTTP_{r.status_code} - {r.text}",
                    )
                else:
                    print(
                        f"Unable to upload content for {name}: HTTP_{r.status_code} - {r.text}\n"
                        f"Retrying in {x} seconds",
                        flush=True,
                        file=sys.stderr,
                    )
                    sleep(x)

        return name, None
    except Exception as e:
        return name, str(e)


def get_files_to_publish(path: str) -> List[str]:
    paths = []
    for root, dirs, files in os.walk(path):
        for file in files:
            paths.append(os.path.join(root, file)[len(path) :])
    return paths


def main(num_threads: int, artifacts_dir: str, base_url: str, output_file: str):
    paths = get_files_to_publish(artifacts_dir)
    print(f"= Found {len(paths)} files to publish to {base_url}", flush=True)

    retry_work = []
    work = [(f"{base_url}{x}", artifacts_dir, x) for x in paths]
    with Pool(num_threads) as p:
        results = p.imap_unordered(upload_file, work)
        for i, res in enumerate(results):
            name, err = res
            print(f"= {i+1} of {len(work)} - {name}", flush=True)
            if err:
                print(f"|-> ERROR: {err}", flush=True)
                retry_work.append(name)

    failure_ratio = len(retry_work) / len(paths)
    if failure_ratio > 0.5:
        print(
            f"= Too many failures ({len(retry_work)} of {len(paths)} - {failure_ratio:.2%}). Aborting.",
            flush=True,
        )
        sys.exit(1)

    failed = False
    if retry_work:
        print(f"= Failed to publish {len(retry_work)} files. Retrying...", flush=True)
        work = [(f"{base_url}{x}", artifacts_dir, x) for x in retry_work]
        with Pool(num_threads) as p:
            results = p.imap_unordered(upload_file, work)
            for i, res in enumerate(results):
                name, err = res
                print(f"= {i+1} of {len(work)} - {name} - RETRY loop", flush=True)
                if err:
                    print(f"|-> ERROR: {err}", flush=True)
                    failed = True

    if failed:
        sys.exit(1)

    with open(output_file, "a") as f:
        f.write(f"url={base_url}")


if __name__ == "__main__":
    artifacts_dir = os.environ["INPUT_PATH"]
    if artifacts_dir[-1] != "/":
        artifacts_dir = artifacts_dir + "/"

    file_server = os.environ["INPUT_FILESERVER_URL"]
    if file_server[-1] == "/":
        file_server = file_server[:-1]

    repo = os.environ["GITHUB_REPOSITORY"]
    run_id = os.environ["GITHUB_RUN_ID"]
    run_attempt = os.environ["GITHUB_RUN_ATTEMPT"]
    url = f"{file_server}/{repo}/{run_id}-{run_attempt}/"

    num_threads_str = os.environ.get("INPUT_UPLOAD_THREADS", "5")
    num_threads = int(num_threads_str)

    output_file = os.environ["GITHUB_OUTPUT"]

    main(num_threads, artifacts_dir, url, output_file)
