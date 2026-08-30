import json
import os
import socket
import urllib.request


class HealthProbe:
    def is_port_open(self, port: int, host: str = "127.0.0.1") -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex((host, port)) == 0

    def is_http_healthy(
        self,
        port: int,
        path: str = "/health",
        host: str = "127.0.0.1",
        timeout: float = 1.0,
        expected_target: str | None = None,
        owner_id: str | None = None,
    ) -> bool:
        url = f"http://{host}:{port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                if response.status != 200:
                    return False
                payload = json.loads(response.read().decode("utf-8"))
                runtime = payload.get("runtime") if isinstance(payload, dict) else None
                if not isinstance(runtime, dict):
                    return False
                if runtime.get("product") != "lumina" or runtime.get("protocolVersion") != 1:
                    return False
                if expected_target and runtime.get("target") != expected_target:
                    return False
                if owner_id and runtime.get("ownerId") != owner_id:
                    return False
                return True
        except Exception:
            return False

    def is_service_reachable(
        self,
        port: int,
        path: str = "/health",
        host: str = "127.0.0.1",
        expected_target: str | None = None,
        owner_id: str | None = None,
    ) -> tuple[bool, str]:
        if self.is_http_healthy(
            port,
            path,
            host,
            expected_target=expected_target,
            owner_id=owner_id,
        ):
            return True, "http"
        if self.is_port_open(port, host):
            return False, "identity-mismatch"
        return False, "none"

    def request_shutdown(
        self,
        port: int,
        host: str = "127.0.0.1",
        owner_id: str | None = None,
    ) -> bool:
        request = urllib.request.Request(
            f"http://{host}:{port}/runtime/shutdown",
            method="POST",
            headers={"X-Lumina-Runtime-Owner": owner_id or os.environ.get("LUMINA_RUNTIME_OWNER", "")},
        )
        try:
            with urllib.request.urlopen(request, timeout=2.0) as response:
                return response.status == 200
        except Exception:
            return False
