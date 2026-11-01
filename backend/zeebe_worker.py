"""Camunda 8 REST job worker for the BPMN task type ``shein-agent``."""

from __future__ import annotations

import logging
import os
import socket
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

# Running this file directly puts backend/ on sys.path.
from returnflow_core import process_bpmn_task  # noqa: E402


LOGGER = logging.getLogger("returnflow.zeebe")
JOB_TYPE = os.getenv("CAMUNDA_JOB_TYPE", "shein-agent")
WORKER_ID = os.getenv("CAMUNDA_WORKER_ID", f"returnflow-{socket.gethostname()}")
JOB_TIMEOUT_MS = int(os.getenv("CAMUNDA_JOB_TIMEOUT_MS", "300000"))
ACTIVATION_BATCH_SIZE = 1


def _camunda_base_url() -> str:
    configured = os.getenv("CAMUNDA_REST_URL", "").strip()
    if configured:
        base = configured.rstrip("/")
    else:
        region = os.getenv("CAMUNDA_REGION", "").strip()
        cluster_id = os.getenv("CAMUNDA_CLUSTER_ID", "").strip()
        if region and cluster_id:
            base = f"https://{region}.api.camunda.io/{cluster_id}/v2"
        else:
            base = "http://localhost:8080/v2"
    return base if base.endswith("/v2") else f"{base}/v2"


class CamundaRestClient:
    """Small REST client with cached OAuth client-credentials authentication."""

    def __init__(self) -> None:
        self.base_url = _camunda_base_url()
        self.oauth_url = os.getenv("CAMUNDA_OAUTH_URL", "https://login.cloud.camunda.io/oauth/token").strip()
        self.client_id = os.getenv("CAMUNDA_CLIENT_ID") or os.getenv("ZEEBE_CLIENT_ID")
        self.client_secret = os.getenv("CAMUNDA_CLIENT_SECRET") or os.getenv("ZEEBE_CLIENT_SECRET")
        self.audience = os.getenv("CAMUNDA_TOKEN_AUDIENCE") or os.getenv("ZEEBE_TOKEN_AUDIENCE")
        self.explicit_token = os.getenv("CAMUNDA_ACCESS_TOKEN") or os.getenv("ZEEBE_ACCESS_TOKEN")
        self.username = os.getenv("CAMUNDA_BASIC_USERNAME")
        self.password = os.getenv("CAMUNDA_BASIC_PASSWORD")
        self._token = self.explicit_token
        self._token_expires_at = float("inf") if self.explicit_token else 0.0
        self.http = httpx.Client(timeout=httpx.Timeout(45.0, connect=10.0))

        if bool(self.client_id) != bool(self.client_secret):
            raise RuntimeError("Set both CAMUNDA_CLIENT_ID and CAMUNDA_CLIENT_SECRET, or neither.")
        if bool(self.username) != bool(self.password):
            raise RuntimeError("Set both CAMUNDA_BASIC_USERNAME and CAMUNDA_BASIC_PASSWORD, or neither.")
        if self.client_id and "api.camunda.io" in self.base_url and not self.audience:
            raise RuntimeError("Set CAMUNDA_TOKEN_AUDIENCE to the audience from the Camunda SaaS API credentials.")

    def _access_token(self) -> str | None:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        if not self.client_id:
            return None
        form = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        if self.audience:
            form["audience"] = self.audience
        response = self.http.post(self.oauth_url, data=form)
        response.raise_for_status()
        token_data = response.json()
        self._token = token_data["access_token"]
        self._token_expires_at = time.time() + int(token_data.get("expires_in", 3600))
        return self._token

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        token = self._access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def post(self, path: str, payload: dict, *, timeout: float | None = None) -> httpx.Response:
        options = {"timeout": timeout} if timeout is not None else {}
        response = self.http.post(
            f"{self.base_url}{path}", json=payload, headers=self._headers(),
            auth=(self.username, self.password) if self.username and self.password else None,
            **options,
        )
        response.raise_for_status()
        return response

    def close(self) -> None:
        self.http.close()


def _activate_jobs(client: CamundaRestClient) -> list[dict]:
    response = client.post(
        "/jobs/activation",
        {
            "type": JOB_TYPE,
            "worker": WORKER_ID,
            "timeout": JOB_TIMEOUT_MS,
            "maxJobsToActivate": ACTIVATION_BATCH_SIZE,
            "fetchVariable": [],
            "requestTimeout": 10000,
        },
        timeout=25.0,
    )
    return response.json().get("jobs", [])


def _complete_job(client: CamundaRestClient, job: dict, variables: dict) -> None:
    client.post(f"/jobs/{job['jobKey']}/completion", {"variables": variables})


def _fail_job(client: CamundaRestClient, job: dict, exc: Exception) -> None:
    retries = max(0, int(job.get("retries", 1)) - 1)
    description = f"{type(exc).__name__}: worker operation failed; inspect local worker logs."
    client.post(
        f"/jobs/{job['jobKey']}/failure",
        {
            "retries": retries,
            "errorMessage": description,
            "retryBackOff": 10000,
        },
    )


def _handle_job(client: CamundaRestClient, job: dict) -> None:
    headers = job.get("customHeaders") or {}
    operation = headers.get("operation")
    job_key = job.get("jobKey", "unknown")
    try:
        if not operation:
            raise ValueError("The activated BPMN job has no 'operation' header.")
        output = process_bpmn_task(operation, job.get("variables") or {})
        _complete_job(client, job, output)
        LOGGER.info("Completed job %s (%s).", job_key, operation)
    except Exception as exc:
        LOGGER.exception("Operation %s failed for job %s.", operation or "<missing>", job_key)
        try:
            _fail_job(client, job, exc)
        except Exception:
            LOGGER.exception("Could not report failure for job %s to Camunda.", job_key)


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    client = CamundaRestClient()
    LOGGER.info("Listening for '%s' jobs at %s as %s.", JOB_TYPE, client.base_url, WORKER_ID)
    try:
        while True:
            try:
                jobs = _activate_jobs(client)
                for job in jobs:
                    _handle_job(client, job)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                LOGGER.error("Camunda activation request failed (%s); retrying in 5 seconds.", type(exc).__name__)
                time.sleep(5)
    except KeyboardInterrupt:
        LOGGER.info("Worker stopped.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
