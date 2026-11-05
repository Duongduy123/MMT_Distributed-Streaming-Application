# Manual tests

Scripted checks for things automated tests can't cover well, such as real LAN machines, firewalls and browsers. Rubric Step 10 asks for "local network simulation tests (connecting from multiple terminal windows)".

## Today (scaffolding phase)

```powershell
python server.py --help
python client.py --help
python server.py                        # expected: exit code 2, "scaffold only ... not implemented"
python client.py --server 0.0.0.0       # expected: exit code 64, wildcard-address error
python scripts/show_network_info.py     # lists bind vs destination addresses
```

## Planned (once Phases 3–10 exist)

1. **Single machine, multiple terminals**
   - Terminal 1: `python server.py`
   - Terminals 2 and 3: `python client.py --server 127.0.0.1 --ui-port 3001` and `--ui-port 3002`
   - Open `http://127.0.0.1:3001` and `http://127.0.0.1:3002`.
2. **LAN**
   - On A: `python scripts/show_network_info.py`. Allow TCP 8080 and UDP 9000 in the firewall.
   - On B and C: `python client.py --server <A's LAN IPv4>`.
3. For each run, record:
   - the command,
   - the expected and actual result,
   - the date,
   - the machines/OS used.

   Add the results to `docs/PROGRESS.md`.
