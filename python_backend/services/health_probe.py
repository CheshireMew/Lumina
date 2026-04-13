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
    ) -> bool:
        url = f"http://{host}:{port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return response.status == 200
        except Exception:
            return False

    def is_service_reachable(
        self,
        port: int,
        path: str = "/health",
        host: str = "127.0.0.1",
    ) -> tuple[bool, str]:
        if self.is_http_healthy(port, path, host):
            return True, "http"
        if self.is_port_open(port, host):
            return True, "tcp"
        return False, "none"
