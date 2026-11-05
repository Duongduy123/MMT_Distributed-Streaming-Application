"""Hand-written HTTP/1.1 over raw ``socket.SOCK_STREAM`` -- ONE shared implementation.

Decision D1 (provisional): TCP 8080 speaks HTTP/1.1; there is exactly one listener on it.
The same layer serves four roles, so no HTTP code is duplicated:

* server dashboard listener   (server process, default 127.0.0.1:3000)
* backend / control listener  (server process, default 0.0.0.0:8080)
* client local UI listener    (client process, default 127.0.0.1:3000; static files + /api/*)
* control-plane HTTP client   (client process -> SERVER_IP:8080)

``http.server``, ``http.client``, ``socketserver``, ``urllib.request`` and every web framework
are prohibited (see docs/CONSTRAINT_AUDIT.md). Status: SCAFFOLD (interfaces only).
"""
