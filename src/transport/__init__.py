"""Shared custom UDP transport, used by BOTH the server and the client process.

There is exactly one implementation of each mechanism here; the server and client create
independent *instances* per (connection, direction) -- see ``connection_state``.

Modules and status:
    contracts           SCAFFOLD   Protocols: CongestionController, TimerHost, TimerHandle
    timer_host          SCAFFOLD   threading-based TimerHost (D11), skeleton only
    congestion_control  EXISTING IMPLEMENTATION (copied byte-identical; compliance UNVERIFIED, D13)
    pacer               EXISTING IMPLEMENTATION (copied byte-identical; D13)
    paced_sender        EXISTING IMPLEMENTATION (copied byte-identical; D13)
    connection_state    SCAFFOLD   per-direction state container
    reliability         GATED ON D14
    flow_control        GATED ON D14
    scheduler           SCAFFOLD   process-wide send scheduler interface
    send_queue          re-exports queue types from paced_sender (no duplication)

Rule: transport code never imports ``src.server`` or ``src.client`` and knows nothing about
users, chats or files beyond neutral priority classes.
"""
