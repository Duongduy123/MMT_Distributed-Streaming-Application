"""Protocol contracts, split by layer so that no enum mixes layers (review item 2).

* ``application_messages`` -- application categories carried end-to-end (AUTH, MSG, FILE, ...)
* ``control_messages``     -- control-plane operations carried over HTTP/1.1 on TCP 8080 (D1)
* ``transport_frames``     -- custom UDP transport frame kinds (DATA, ACK, WND_PROBE, ...)
* ``packet_header`` / ``serialization`` -- wire format contracts, GATED ON D14

All enums use ``enum.auto()``: their values are NOT wire codes. Numeric codes, header layout,
endianness and serialization are defined only after D14 (sequence model) is resolved.
"""
