# Computer Networks Assignment — System Architecture & Transport Design

> **Mục đích:** Tập hợp kiến trúc triển khai và các concept Network/Transport mà nhóm đang thống nhất cho assignment *Distributed and Streaming-based Client-Server Collaboration Application*.
>
> **Phạm vi:** Hai loại process (`server process`, `client process`), centralized server trên Machine A, frontend phân tán theo từng máy, TCP Control Plane, UDP Data Plane, Reliability, Flow Control, Congestion Control, Pacer, relay, port/bind, luồng hoạt động và các điểm cần chốt trước khi implementation.
>
> **Trạng thái:** Tài liệu kiến trúc làm việc. Những nội dung ghi **OPEN DECISION** hoặc **SPEC CONFLICT** chưa được xem là quyết định kỹ thuật cuối cùng.

---

## 1. Tổng quan kiến trúc đã thống nhất

Nhóm chọn mô hình **centralized client-server với frontend phân tán theo máy**:

- **Machine A** chạy một `server process`.
- **Machine B/C/...** chạy mỗi máy một `client process`.
- Frontend của server và frontend của client là hai giao diện khác nhau, nhưng đều sử dụng HTML/CSS/JavaScript đơn giản.
- TCP được sử dụng cho các thao tác điều khiển/kết nối thông thường: connect/handshake, login/authentication, session, presence và đồng bộ danh sách user.
- UDP được sử dụng cho data plane: direct chat, global chat và dữ liệu file. UDP transport tự triển khai Reliability, Flow Control, Congestion Control và pacing.
- UDP server trên Machine A làm điểm relay trung tâm. B và C không cần gửi UDP trực tiếp cho nhau trong mô hình relay này.

### 1.1 Sơ đồ thành phần

```text
                         Wi-Fi / LAN
             (Ví dụ: các máy nằm trong cùng subnet)

  MACHINE A — SERVER PROCESS
  LAN IP: 192.168.1.10 (ví dụ)
  ┌──────────────────────────────────────────────────────┐
  │ Server Frontend                                      │
  │ TCP :3000 — server dashboard / monitoring            │
  ├──────────────────────────────────────────────────────┤
  │ Backend + TCP Control Plane                          │
  │ TCP :8080 — connect, login, session, presence, users │
  ├──────────────────────────────────────────────────────┤
  │ UDP Transport Server                                 │
  │ UDP :9000 — relay, reliability, flow control, CC     │
  └──────────────────────────────────────────────────────┘
                ▲                         ▲
                │ TCP Control             │ UDP Data
                │ + UDP relay             │
       ┌────────┴─────────┐       ┌───────┴───────────┐
       │                  │       │                   │
  MACHINE B         MACHINE C    ...              MACHINE N
  CLIENT PROCESS    CLIENT PROCESS
  ┌────────────────┐ ┌────────────────┐
  │ Client UI      │ │ Client UI      │
  │ TCP :3000      │ │ TCP :3000      │
  │ bound to       │ │ bound to       │
  │ 127.0.0.1      │ │ 127.0.0.1      │
  ├────────────────┤ ├────────────────┤
  │ TCP client     │ │ TCP client     │
  │ to A:8080      │ │ to A:8080      │
  ├────────────────┤ ├────────────────┤
  │ UDP client     │ │ UDP client     │
  │ to A:9000      │ │ to A:9000      │
  └────────────────┘ └────────────────┘
```

### 1.2 Vì sao gọi là centralized server nhưng distributed frontend?

- **Centralized server:** Authentication, sessions, user presence, UDP relay và trạng thái server tập trung tại Machine A.
- **Distributed frontend:** Mỗi máy chạy giao diện phù hợp với process trên máy đó. A có server dashboard; B/C có client UI local.
- **Không phải peer-to-peer:** Trong kiến trúc hiện tại, B gửi UDP đến A; A nhận và relay dữ liệu đến C. B không cần biết UDP endpoint của C để gửi trực tiếp.

---

## 2. Hai process và trách nhiệm

## 2.1 Server process — chạy trên Machine A

Lệnh khởi chạy ví dụ:

```powershell
python server.py
```

Server process khởi tạo ba thành phần logic. Ba thành phần có thể là các module/thread bên trong cùng một process, không bắt buộc là ba OS process riêng.

| Thành phần | Bind address đề xuất | Protocol | Port | Trách nhiệm |
|---|---|---:|---:|---|
| Server Frontend | `0.0.0.0` hoặc LAN IP cụ thể | TCP/HTTP | `3000` | Dashboard, trạng thái server, danh sách kết nối, monitoring |
| Backend + TCP Control Plane | `0.0.0.0` hoặc LAN IP cụ thể | TCP | `8080` | Kết nối control, login, auth, session, presence, user list, file metadata/control |
| UDP Transport Server | `0.0.0.0` hoặc LAN IP cụ thể | UDP | `9000` | Nhận/gửi datagram, transport state, relay, reliability, flow control, congestion control, pacer |

### Server Frontend — TCP 3000

- Phục vụ giao diện quản trị dành cho người vận hành Machine A.
- Có thể hiển thị server IP, port, số client online, session, trạng thái TCP/UDP, thống kê packet, retransmission, RTT, `cwnd`, `rwnd` và throughput.
- Nếu cần cho máy khác truy cập dashboard, listener phải bind vào LAN interface (ví dụ `0.0.0.0`), firewall phải cho phép TCP 3000 và người dùng mở `http://192.168.1.10:3000`.
- Nếu dashboard chỉ dành cho người vận hành tại A, có thể bind `127.0.0.1` để chỉ truy cập local.

### Backend + TCP Control Plane — TCP 8080

Đây là điểm vào cho các hoạt động control-plane của client:

- Application-level connect/handshake và đăng ký client.
- Authentication/login và trả kết quả đăng nhập.
- Tạo, kiểm tra và thu hồi session/token.
- Theo dõi client đang online/offline.
- Đồng bộ user list và presence events.
- Điều phối file transfer ở mức control/metadata, ví dụ file offer, accept/reject, tên file, kích thước, checksum và trạng thái.
- Liên kết danh tính/session đã xác thực với UDP connection tương ứng.

**Phân biệt hai loại handshake:**

1. TCP three-way handshake (`SYN`, `SYN-ACK`, `ACK`) do OS TCP stack thực hiện khi client gọi `connect()`.
2. Application-level handshake/login là thông điệp của ứng dụng sau khi TCP connection đã được thiết lập.

Assignment có rubric về basic TCP handshake và ACK. Nhóm cần thể hiện được client kết nối và nhận phản hồi ở tầng ứng dụng, không chỉ dựa vào việc OS hoàn tất TCP handshake.

**OPEN DECISION — giao thức chạy trên TCP 8080:**

Vì nhóm muốn tích hợp HTTP backend và TCP Control Plane cùng port `8080`, cần chọn một giao thức thống nhất cho listener:

- **Phương án phù hợp với cấu trúc ba port:** tự triển khai HTTP/1.1 request/response trên raw TCP socket tại port 8080; các thao tác control được biểu diễn bằng HTTP endpoints. Presence server-push có thể dùng một cơ chế HTTP streaming (ví dụ SSE) hoặc polling/long-polling được tự triển khai.
- Nếu muốn dùng custom binary TCP protocol riêng thay cho HTTP, không thể để HTTP parser và binary parser cùng đọc tùy tiện một TCP byte stream. Khi đó cần một port TCP riêng hoặc một cơ chế multiplexing/framing được định nghĩa rõ.

Không mở hai TCP listener độc lập cùng bind `0.0.0.0:8080`.

### UDP Transport Server — UDP 9000

- Một UDP socket server trên A có thể phục vụ nhiều client endpoint.
- Nhận datagram từ B/C trên cùng UDP listening port `9000`.
- Tra cứu connection/session tương ứng bằng connection identifier và trạng thái endpoint đã được xác thực; không tin username tự khai trong payload.
- Phân tích packet/frame và gọi các module Reliability, Flow Control, Congestion Control.
- Relay chat/file đến đúng client đích.
- Quản lý trạng thái độc lập cho từng kết nối/chiều truyền.

## 2.2 Client process — chạy trên Machine B/C

Lệnh ví dụ:

```powershell
python client.py --server 192.168.1.10 --tcp-port 8080 --udp-port 9000 --ui-port 3000
```

Client process gồm:

1. **Client UI HTTP listener:** phục vụ frontend local và các local API cho browser.
2. **TCP client module:** mở TCP socket tới Machine A:8080 để thực hiện control-plane operations.
3. **UDP client module:** mở UDP socket để gửi/nhận datagram với Machine A:9000.
4. **Transport modules:** reliability, flow control, congestion control và pacer ở phía client sender/receiver.
5. **UI bridge/event mechanism:** chuyển event giữa Python client modules và JavaScript local UI.

### Client Frontend — local TCP 3000

- Client UI phục vụ user đang dùng chính máy B/C.
- Bind đề xuất: `127.0.0.1:3000`.
- User mở `http://127.0.0.1:3000` trên cùng máy.
- JavaScript gọi local endpoints của client process, ví dụ `fetch('/api/messages')`, hoặc dùng một HTTP event stream local để nhận message/presence.
- Local UI/API không cần expose ra LAN.

### TCP client module

- Kết nối tới địa chỉ IP/port của server A, ví dụ `192.168.1.10:8080`.
- Thực hiện application-level connect/handshake, login/authentication và session management.
- Nhận user list/presence events.
- Gửi/nhận control messages và file metadata theo giao thức nhóm chốt.

### UDP client module

- Gửi datagram tới `192.168.1.10:9000`.
- Dùng cùng UDP socket để nhận response từ A.
- Local source port thường do OS tự cấp (ephemeral port), không cần phải là `9000`.
- Duy trì packet/sequence state, ACK/SACK, retransmission, receive/send window, `cwnd`, pacing và các timer theo kết nối.

---

## 3. Bind, listen, connect và địa chỉ IP/port

### 3.1 Bind là gì?

`bind()` gắn một socket với địa chỉ IP và port local trên máy hiện tại. Với server socket, đây thường là địa chỉ mà server chờ kết nối/datagram đi vào.

```python
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(("127.0.0.1", 3000))
sock.listen()
```

Đoạn này tạo TCP listener chỉ nhận kết nối qua loopback của máy hiện tại.

### 3.2 Các địa chỉ thường gặp

| Địa chỉ | Ý nghĩa |
|---|---|
| `127.0.0.1` | Loopback/localhost; chỉ máy hiện tại truy cập được qua interface loopback |
| `0.0.0.0` | Địa chỉ bind wildcard IPv4; listener nhận trên các IPv4 interface phù hợp của máy |
| `192.168.1.10` | Ví dụ LAN IP cụ thể của Machine A; client khác trong LAN dùng địa chỉ này để kết nối |

`0.0.0.0` là địa chỉ bind phía server, không phải địa chỉ đích mà client nên nhập.

### 3.3 Bảng địa chỉ và port mẫu

Giả sử:

- A: `192.168.1.10`
- B: `192.168.1.20`
- C: `192.168.1.30`

| Máy | Socket | Local bind/source | Remote destination |
|---|---|---|---|
| A | Server Frontend | `0.0.0.0:3000/TCP` | Browser truy cập `192.168.1.10:3000` |
| A | Backend/Control | `0.0.0.0:8080/TCP` | Client kết nối `192.168.1.10:8080` |
| A | UDP server | `0.0.0.0:9000/UDP` | Client gửi `192.168.1.10:9000` |
| B | Client UI | `127.0.0.1:3000/TCP` | Browser B mở `127.0.0.1:3000` |
| B | TCP client | OS cấp source port ephemeral | `192.168.1.10:8080/TCP` |
| B | UDP client | OS cấp source port ephemeral (hoặc local bind được cấu hình riêng) | `192.168.1.10:9000/UDP` |
| C | Client UI | `127.0.0.1:3000/TCP` | Browser C mở `127.0.0.1:3000` |
| C | TCP client | OS cấp source port ephemeral | `192.168.1.10:8080/TCP` |
| C | UDP client | OS cấp source port ephemeral (hoặc local bind được cấu hình riêng) | `192.168.1.10:9000/UDP` |

**Quan trọng:** B/C không bắt buộc mở UDP server ở local port 9000. Port `9000` trong command client là destination port của UDP server A. Một UDP socket client có thể gửi đến A và nhận reply trên chính socket đó.

### 3.4 Hai máy có thể cùng dùng port 3000 không?

Có. Machine A và Machine B là hai máy khác nhau nên có thể cùng dùng TCP port `3000`.

Tuy nhiên, nếu Machine A vừa chạy server dashboard bind `0.0.0.0:3000`, vừa chạy thêm client process mà client UI cũng bind `127.0.0.1:3000`, có thể xảy ra xung đột bind trên cùng máy. Nếu host A cũng muốn tham gia như một client, hãy cấu hình client UI port khác (ví dụ `3001`) hoặc thiết kế rõ cách chia sẻ listener. Đây là cấu hình cần quyết định trước khi hỗ trợ host-user mode.

---

## 4. Browser, frontend local và Python client process

Browser không trực tiếp tạo raw UDP socket bằng JavaScript thông thường. Vì vậy, client process đóng vai trò native agent cho giao diện.

### 4.1 Luồng browser → local client process

```text
Browser trên B
    |
    | HTTP request tới cùng origin
    | http://127.0.0.1:3000/api/...
    v
HTTP listener của Client Process B
    |
    | Gọi hàm/module nội bộ hoặc đưa command vào queue
    v
TCP Client / UDP Client trong cùng process
```

Không cần tạo process thứ ba. Frontend server, local API và các network client modules có thể là các phần/module/thread trong một `client process`.

### 4.2 Ví dụ JavaScript local API

```javascript
// Chạy trong browser tại http://127.0.0.1:3000
async function sendChatMessage(to, text) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ to, text })
  });

  if (!response.ok) {
    throw new Error("Local client rejected the chat request");
  }

  return response.json();
}
```

Trong ví dụ này, `fetch()` chỉ gọi local HTTP listener của client process. Python client process mới là thành phần tạo custom UDP packet và gửi đến A:9000.

### 4.3 Ví dụ Python raw UDP client

```python
import socket

server_address = ("192.168.1.10", 9000)

udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# Không bind local port cố định: OS sẽ tự cấp ephemeral port khi gửi.
udp_socket.sendto(b"EXAMPLE_CUSTOM_PACKET", server_address)
```

Đây chỉ là ví dụ socket cơ bản; payload thật phải tuân thủ packet format và protocol của nhóm.

---

## 5. TCP Control Plane

TCP Control Plane quản lý thông tin cần thiết để client gia nhập, xác thực và duy trì trạng thái trong hệ thống.

### 5.1 Nhiệm vụ

| Chức năng | Mô tả |
|---|---|
| Connect | Client mở TCP connection đến A:8080 |
| Application handshake | Client và server trao đổi thông điệp khởi tạo và ACK ở tầng ứng dụng |
| Authentication | Client gửi thông tin đăng nhập; server kiểm tra và trả kết quả |
| Session management | Server cấp/kiểm tra session token và gắn identity với connection |
| Presence | Server cập nhật online/offline khi client login, logout hoặc timeout |
| User list | Client nhận danh sách user hiện online |
| File control/metadata | Trao đổi offer, accept/reject, tên file, kích thước, hash và trạng thái nếu nhóm chọn TCP cho metadata |

### 5.2 Presence broadcast là gì?

Trong kiến trúc này, “broadcast presence” là broadcast ở **application layer**: khi B online, server A gửi notification cho các client đang đăng nhập. Không nhất thiết là UDP broadcast tới `255.255.255.255`.

Ví dụ:

```text
B --TCP--> A:8080: LOGIN_SUCCESS
A cập nhật session của B
A --TCP--> C:8080: PRESENCE(user=B, status=online)
A --TCP--> các client khác: PRESENCE(user=B, status=online)
```

### 5.3 Presence update/server push

HTTP request/response thông thường không tự động đẩy event từ server về browser. Nhóm cần chọn một cơ chế rõ ràng:

- Polling: client định kỳ hỏi server có presence update mới không.
- Long polling: server giữ request cho tới khi có event hoặc timeout.
- Server-Sent Events (SSE): một HTTP response stream một chiều từ server đến client; không phải WebSocket.
- Persistent custom TCP control protocol: cần framing và parser riêng.

Nếu giữ cả HTTP API lẫn TCP Control Plane trên port `8080`, ưu tiên một giao thức duy nhất trên listener. Không trộn HTTP bytes và binary custom messages tùy tiện trong cùng TCP stream.

---

## 6. UDP Data Plane và centralized relay

### 6.1 Vai trò UDP server A

- A bind UDP socket tại `0.0.0.0:9000`.
- Mỗi B/C dùng một UDP client socket riêng và gửi datagram tới A:9000.
- A quản lý connection identifier, remote endpoint, session binding và transport state.
- A relay chat/file từ sender đến recipient.
- B/C không cần thiết lập UDP peer-to-peer với nhau trong topology này.

### 6.2 Direct chat flow

```text
B Browser
   | HTTP localhost
   v
B Client Process
   | UDP datagram
   v
A UDP Server :9000
   | kiểm tra session/connection, xử lý transport
   | tra recipient C và relay packet/data
   v
C UDP Client
   | local event/API
   v
C Browser
```

### 6.3 Global chat flow

```text
B -> UDP A:9000
A xác thực sender và xử lý transport
A fan-out message tới các client online (trừ sender nếu protocol quy định)
A -> C, D, ... qua UDP
```

Mỗi recipient có endpoint và trạng thái transport riêng. Một client chậm không nên làm blocking toàn bộ việc gửi tới các client còn lại; queue/relay buffer cần giới hạn dung lượng.

### 6.4 File transfer flow

Khuyến nghị phân chia theo quyết định TCP Control Plane / UDP Data Plane:

1. B gửi file offer/metadata qua TCP Control Plane: recipient, file name, size, SHA-256.
2. A kiểm tra C online và chuyển offer đến C.
3. C accept/reject qua TCP Control Plane.
4. Khi được accept, B truyền nội dung file thành các chunks qua UDP Data Plane.
5. A nhận và relay từng phần sang C; không giữ toàn bộ file trong RAM.
6. C reassemble/ghi file và cập nhật SHA-256.
7. C gửi kết quả `FILE_DONE`/status qua control path; A chuyển tiếp kết quả tới B.

**Phân biệt ACK transport và file completion:** ACK từ A về B chỉ xác nhận A nhận một packet/frame theo hop B→A. Nó không chứng minh C đã nhận hoặc ghi hoàn tất file. Chỉ khi C xác nhận đủ dữ liệu và checksum hợp lệ mới được báo file hoàn tất end-to-end.

---

## 7. Reliability — đảm bảo truyền tin cậy trên UDP

UDP tự thân không đảm bảo delivery, ordering hay de-duplication. Reliability module của nhóm tự triển khai những chức năng này.

### 7.1 Các cơ chế chính

| Cơ chế | Vai trò |
|---|---|
| Sequence number | Đánh số frame mới theo thứ tự tăng dần |
| Cumulative ACK | Xác nhận frame liên tục cuối cùng đã nhận |
| SACK | Thông báo các frame/range đã đến nhưng chưa liền mạch |
| Ring Buffer | Giữ frame đến sớm và hỗ trợ reassembly theo sequence |
| RTO | Phát hiện frame chưa được ACK và kích hoạt retransmission |
| Fast Retransmit | Retransmit sớm khi có đủ duplicate ACK kèm SACK evidence |
| Checksum/CRC32 | Phát hiện frame bị hỏng |
| SHA-256 | Kiểm tra toàn vẹn file sau khi ghép |

### 7.2 Header fields theo tài liệu Reliability hiện tại

Tài liệu `reliability-tcp.docx` mô tả các trường:

| Field | Kích thước trong tài liệu | Ý nghĩa |
|---|---:|---|
| `seq` | 4 bytes | Sequence number của DATA frame |
| `ack` | 4 bytes | Cumulative ACK, tương ứng LFR |
| `sack_count + SACK ranges` | `1 + 8*n` bytes | Danh sách range nhận sớm; tối đa 4 range theo tài liệu |
| `rwnd` | 2 bytes | Receive window còn trống |
| `flags` | 1 byte | DATA, ACK, WND_PROBE, RETX... |
| `timestamp` | 4 bytes | Timestamp dùng đo RTT |
| `checksum` | 4 bytes | CRC32 của header và data |

Đây là cấu trúc theo tài liệu nhóm cung cấp; cần thống nhất endian, đơn vị timestamp, checksum coverage và giới hạn payload trong protocol specification cuối cùng.

### 7.3 Cumulative ACK và SACK

Ví dụ: receiver đã nhận frame 12 và 13 nhưng frame 11 bị mất.

```text
Sender gửi:       11, 12, 13
Receiver nhận:        12, 13
Receiver phản hồi: ACK = 10, SACK = [12, 13]
Sender:           chỉ retransmit frame 11
```

Không dùng Go-Back-N để gửi lại toàn bộ các frame phía sau. Các frame đã được SACK xác nhận không cần retransmit chỉ vì cumulative ACK chưa tiến lên.

### 7.4 RTO và RTT

Tài liệu Reliability chọn công thức kiểu RFC 6298:

- Mẫu RTT chỉ lấy từ frame chưa từng retransmit (Karn's algorithm).
- Lần đo đầu: `SRTT = R`, `RTTVAR = R / 2`.
- Các lần sau cập nhật `RTTVAR` trước rồi `SRTT`.
- `RTO = SRTT + 4 * RTTVAR`.
- RTO ban đầu: 1 giây; min 200 ms; max 60 giây theo lựa chọn thiết kế trong tài liệu.
- Mỗi lần timeout không thành công, exponential backoff; ACK mới đưa RTO về giá trị tính toán.
- Timeout chỉ retransmit đúng frame mất; frame đã SACK thì bỏ qua.

### 7.5 Fast Retransmit

Theo tài liệu Reliability, khi Sender nhận 3 duplicate ACK cùng cumulative ACK, kèm SACK cho thấy frame phía sau đã đến, Sender suy ra frame đầu tiên sau ACK đó có thể bị mất và retransmit ngay.

Reliability module phát hiện sự kiện loss; Congestion Control nhận thông báo loss để cập nhật `cwnd`. Hai module cần phối hợp recovery state để tránh giảm congestion window nhiều lần cho cùng một recovery period.

### 7.6 Zero-window deadlock và WND_PROBE

Nếu Receiver quảng bá `rwnd = 0`, Sender dừng gửi dữ liệu mới và bật persist/probe timer.

- Khi timer hết hạn, Sender gửi `WND_PROBE`.
- Receiver phải trả lời bằng ACK chứa `rwnd` hiện tại, kể cả khi buffer vẫn đầy.
- Nếu vẫn zero window, Sender tăng thời gian probe bằng exponential backoff.
- Nếu window mở lại, Sender hủy probe timer và tiếp tục gửi.
- ACK trả lời WND_PROBE không được dùng để đo RTT hoặc tính duplicate ACK cho Fast Retransmit theo tài liệu Reliability.

### 7.7 Các điểm Reliability cần sửa/đồng bộ

Tài liệu `reliability-tcp.docx` tự ghi nhận các điểm cần chỉnh:

1. Frame trùng (`seq <= LFR`) phải bị bỏ phần payload nhưng Receiver vẫn gửi lại cumulative ACK; không im lặng bỏ toàn bộ packet.
2. Đổi tên `MaxByteBuff` dùng cho số slot frame thành `MaxSlotBuff`; tách với buffer capacity tính theo byte.
3. Không mở rộng receive window/LAF chỉ vì frame vừa đến nếu ứng dụng chưa đọc/giải phóng buffer. Window chỉ trượt theo lượng buffer thực sự được giải phóng.
4. `WND_PROBE` dùng sequence/offset của byte/frame tiếp theo chưa được xác nhận theo quy ước protocol đã chốt; tài liệu gợi ý `LastByteAck + 1`.

---

## 8. Flow Control — bảo vệ buffer của Receiver

### 8.1 Flow Control khác Congestion Control

| | Flow Control | Congestion Control |
|---|---|---|
| Biến chính | `rwnd` | `cwnd` |
| Bảo vệ | Buffer của Receiver | Mạng trung gian/shared network |
| Tín hiệu | Receiver quảng bá free buffer/credit | Loss, timeout và/hoặc tín hiệu congestion khác |
| Quyết định | Receiver còn nhận được bao nhiêu | Network sender được phép giữ bao nhiêu data in flight |

Sender phải đồng thời tôn trọng cả hai giới hạn.

### 8.2 Sender window

Công thức khái quát:

```text
SWS = min(rwnd, cwnd)
inflight = LFS - LAR                 # nếu đếm theo frame/packet
allowed_to_send = SWS - inflight
```

Hoặc nếu triển khai theo byte:

```text
allowed_bytes = min(rwnd_bytes, cwnd_bytes) - bytes_in_flight
```

**Không trộn đơn vị:** nếu `cwnd` tính bằng byte thì `rwnd` cũng phải đổi sang byte trước khi lấy `min()`. Nếu tính theo packet/frame thì cả hai phải cùng đơn vị và xử lý packet size không đồng nhất rõ ràng.

### 8.3 Sender state

- `SWS`: Send Window Size.
- `LAR`: Last Acknowledgment Received; mép trái/cumulative progress phía sender.
- `LFS`: Last Frame Sent; frame cuối cùng đã gửi.
- `inflight`: số frame/byte đã gửi nhưng chưa được xác nhận tương ứng.

Sender không được vượt quá mép phải cửa sổ:

```text
LFS <= LAR + SWS
```

Công thức này chỉ dùng khi các đại lượng đang được tính theo cùng đơn vị sequence/frame.

### 8.4 Receiver state

- `RWS`: Receive Window Size/capacity.
- `LFR`: Last Frame Received liên tục; cumulative receive progress.
- `LAF`: Largest Acceptable Frame; mép phải hiện tại của vùng receiver cho phép nhận.
- Ring Buffer giữ những frame đến sớm trong cửa sổ.

Receiver chỉ chấp nhận frame nằm trong receive window; frame cũ/trùng được xử lý bằng duplicate detection và ACK; frame vượt giới hạn bị loại và phản hồi bằng ACK/rwnd phù hợp.

### 8.5 Ring Buffer

Tài liệu Flow Control mô tả vị trí slot:

```text
buffer_index = sequence_number % MaxSlotBuff
```

Dùng Ring Buffer giúp tái sử dụng slot sau khi dữ liệu cũ đã được xử lý/giải phóng.

Cần phân biệt:

- `MaxSlotBuff`: số slot frame trong Ring Buffer.
- `MaxByteBuff`: dung lượng buffer tính bằng byte.

### 8.6 Receiver quảng bá rwnd

Receiver tính lượng buffer còn trống từ capacity và lượng data đang giữ chờ ứng dụng đọc. `rwnd` được thông báo trong ACK (hoặc piggyback vào packet chiều ngược nếu protocol định nghĩa).

Khi ứng dụng đọc dữ liệu, buffer được giải phóng và Receiver có thể quảng bá receive window mới.

### 8.7 Flow control qua server relay

Với đường truyền B → A → C, cần xét khả năng tiếp nhận ở cả hai chặng:

- B→A: A là receiver của chặng đầu.
- A→C: C là receiver của chặng thứ hai.
- Nếu C đọc chậm, A phải giới hạn relay queue và không tiếp tục nhận/giữ dữ liệu vô hạn từ B.
- Credit/backpressure phải truyền tác động ngược về B khi phía C không thể tiếp nhận thêm.

Tài liệu thiết kế trước đó gợi ý giới hạn relay queue theo từng client. Con số cụ thể phải được thống nhất trong config và được kiểm thử.

---

## 9. Congestion Control — bảo vệ mạng

### 9.1 Các biến chính

| Biến | Ý nghĩa |
|---|---|
| `cwnd` | Congestion window: giới hạn data chưa được ACK mà network sender được phép giữ in flight |
| `ssthresh` | Ngưỡng giữa slow start và congestion avoidance |
| `W_max` | Congestion window trước loss, dùng làm mốc CUBIC |
| `MSS` | Maximum Segment Size theo quy ước protocol |
| `srtt` | Smoothed RTT |
| `BtlBw` | Bottleneck bandwidth estimate nếu pacing formula yêu cầu |
| `RTprop` | Minimum RTT estimate trong thiết kế dùng BBR/BDP |

Congestion Control độc lập với Receive Window nhưng phối hợp với Flow Control khi ra quyết định gửi.

### 9.2 CUBIC

Tài liệu Congestion Control hiện tại chỉ định:

- `beta = 0.7`.
- `C = 0.4`.
- Slow start bắt đầu `cwnd = 2` packet và `ssthresh = 8` packet.
- Mỗi ACK trong slow start cộng thêm 1 packet theo mô hình giản lược; cửa sổ xấp xỉ tăng gấp đôi mỗi RTT.
- Khi đạt `ssthresh`, chuyển sang CUBIC congestion avoidance.

Công thức CUBIC trong tài liệu:

```text
K = cube_root(W_max * (1 - beta) / C)
W(t) = C * (t - K)^3 + W_max
```

Trong đó `t` là thời gian kể từ loss/epoch reference được định nghĩa trong implementation. Cần dùng monotonic clock, giữ epoch nhất quán và không reset epoch ở mọi ACK.

### 9.3 Fast loss response

Theo tài liệu Congestion Control:

1. Trigger: 3 duplicate ACK có SACK gap evidence.
2. Lưu `W_max` trước khi giảm cửa sổ.
3. Giảm cửa sổ theo `beta = 0.7`.
4. Retransmit missing frame do Reliability module thực hiện, không phải CUBIC controller.
5. Chỉ giảm congestion window tối đa một lần cho cùng recovery period.

### 9.4 Timeout response

Tài liệu Congestion Control hiện tại mô tả timeout là severe loss:

- Lưu `W_max`.
- `ssthresh = max(floor(cwnd * 0.7), 2)` theo đơn vị packet trong đặc tả giản lược.
- `cwnd = 1` packet.
- Quay lại slow start.

Giá trị min và unit phải được chuẩn hóa nếu controller lưu cửa sổ theo byte.

### 9.5 Điều kiện được gửi

Một packet chỉ đủ điều kiện gửi khi đồng thời:

1. Không vượt congestion window:
   `bytes_in_flight + packet_size <= cwnd_bytes`.
2. Không vượt flow-control credit/rwnd.
3. Pacer có đủ token hoặc đã tới thời điểm gửi theo pacing policy.
4. Scheduler chọn packet theo thứ tự ưu tiên hợp lệ.

ACK-only packet không nhất thiết tính vào bytes-in-flight; tuân thủ quy ước packet type của protocol.

### 9.6 SPEC CONFLICT — CUBIC initialization

Các tài liệu đang có hai cấu hình:

| Nguồn | Initial `cwnd` | Initial `ssthresh` |
|---|---:|---:|
| `congestioncontrol.docx` / simplified specification | 2 MSS | 8 MSS |
| Bản thiết kế chi tiết trước đó | 10 MSS | infinity |

**Không được trộn hai cấu hình.** Tài liệu này ghi nhận cấu hình 2 MSS/8 MSS là lựa chọn theo đặc tả Congestion Control giản lược hiện tại; nhóm cần xác nhận và ghi quyết định chính thức trước khi code.

### 9.7 SPEC CONFLICT — CUBIC pacing formula

Các tài liệu cũng có hai mô tả pacing:

**Công thức trong `congestioncontrol.docx`:**

```text
pacing_rate = pacing_gain * BtlBw
interval = packet_size / pacing_rate
```

Gain steady-state được mô tả là 1.0.

**Công thức CUBIC-specific trong bản thiết kế chi tiết trước đó:**

```text
Slow Start:          pacing_rate = 2.0 * cwnd / srtt
Congestion Avoidance: pacing_rate = 1.2 * cwnd / srtt
```

Đây là hai policy khác nhau. Nếu dùng `BtlBw`, cần có delivery-rate sampler/bandwidth estimator. Nếu không implement estimator, không được đặt một `BtlBw` giả và tuyên bố pacing dựa trên bottleneck bandwidth. Nhóm phải chốt policy trước khi hoàn thành pacer.

---

## 10. Pacer — dàn đều tốc độ gửi

Pacer tránh việc sender gửi toàn bộ window trong một vòng lặp gây micro-burst.

### 10.1 Token bucket

Theo bản thiết kế chi tiết:

- Token được tích lũy theo `pacing_rate`.
- Bucket capacity: 10 packet (nên quy đổi thành byte capacity, ví dụ `10 * MSS`).
- Gửi packet kích thước `packet_size` cần đủ số token tương ứng.
- Khi gửi, trừ token theo packet size.
- Token không được vượt bucket capacity.
- Dùng monotonic time để tính lượng token được refill.

Công thức:

```text
tokens = min(bucket_capacity,
             tokens + elapsed_seconds * pacing_rate)
```

Packet chỉ được pace khi:

```text
tokens >= packet_size
```

Sau khi gửi:

```text
tokens -= packet_size
```

### 10.2 Scheduling

- Pacer không tự encode packet hoặc gọi send socket nếu kiến trúc yêu cầu central scheduler quản lý việc gửi.
- Pacer trả lời câu hỏi “khi nào packet đủ điều kiện được gửi?”.
- Scheduler quyết định packet nào được gửi, sau đó gọi raw UDP socket send operation.
- Không dùng busy-wait hoặc vòng lặp spin để đợi token.
- Timer phải được reschedule/cancel khi queue rỗng, rate thay đổi hoặc connection đóng.

### 10.3 Ưu tiên MSG trước FILE

Theo tài liệu Congestion Control, tại mỗi pacing tick:

1. Control/urgent chat packet được xét trước theo priority policy.
2. MSG được ưu tiên trước FILE chunks.
3. FILE vẫn được gửi khi có slot/token/window phù hợp.
4. Priority không được phép vượt `cwnd`, `rwnd` hoặc bypass pacer.
5. Không reorder packet trong cùng stream trái với ordering requirement.

---

## 11. Quan hệ giữa Reliability, Flow Control, Congestion Control và Pacer

Bốn thành phần giải quyết bốn vấn đề khác nhau:

| Thành phần | Câu hỏi cần trả lời |
|---|---|
| Reliability | Packet/frame bị mất, hỏng, trùng hoặc đến sai thứ tự thì xử lý thế nào? |
| Flow Control | Receiver còn đủ buffer để nhận bao nhiêu dữ liệu? |
| Congestion Control | Mạng hiện cho phép bao nhiêu dữ liệu in-flight? |
| Pacer | Nên trải các packet đủ điều kiện gửi theo thời gian như thế nào? |

### 11.1 Sender decision flow

```text
Application có DATA cần gửi
        |
        v
Reliability tạo/tra frame cần truyền
        |
        v
Flow Control kiểm tra rwnd/credit
        |
        v
Congestion Control kiểm tra cwnd
        |
        v
Pacer kiểm tra token / thời điểm gửi
        |
        v
Scheduler chọn packet theo priority
        |
        v
Raw UDP socket gửi datagram
        |
        v
Lưu sent metadata để ACK/loss/RTT xử lý
```

Đây là sơ đồ logic; thứ tự chi tiết giữa scheduler và các eligibility checks có thể khác trong code, miễn kết quả không bypass bất cứ giới hạn nào.

### 11.2 ACK feedback path

```text
UDP socket nhận ACK/SACK
        |
        v
Reliability parse ACK, xác định acknowledged/lost frames
        |
        +--> cập nhật sent buffer / retransmission state
        |
        +--> cập nhật bytes_in_flight và RTT sample
        |
        +--> Congestion Control: on_ack() / on_loss()
        |
        +--> Flow Control: cập nhật rwnd/credit
        |
        v
Scheduler/Pacer cập nhật packet eligibility và send timing
```

---

## 12. Relay semantics và connection state

### 12.1 Endpoint mapping

UDP server A cần quản lý mapping giữa authenticated user/session và UDP connection endpoint.

Ví dụ conceptually:

```text
user_id = "user_B"
session_id = "..."
conn_id = ...
remote_udp_endpoint = ("192.168.1.20", 51023)
```

Không nên coi IP:port là identity người dùng. IP/port có thể thay đổi; session/connection identifier và quá trình xác thực mới xác định client logic.

### 12.2 Reliability theo hop hay end-to-end — OPEN DECISION

Với centralized relay, nhóm cần định nghĩa rõ:

- **Hop-by-hop transport:** B↔A có reliability/flow/congestion state riêng; A↔C có state riêng. A ACK B khi A nhận dữ liệu; A chịu trách nhiệm relay tiếp và retry ở chặng A→C.
- **End-to-end transport qua relay:** B và C giữ end-to-end packet/ACK state, A chỉ forward datagram. Cơ chế này phức tạp hơn đối với server relay.

**Khuyến nghị cho kiến trúc centralized server:** dùng hop-by-hop transport state cho từng leg, đồng thời có application-level delivery receipt từ C về B. Khi đó:

- ACK B nhận từ A = server đã nhận packet.
- Delivery receipt B nhận sau khi C xác nhận = message đã tới client đích.
- `FILE_DONE` từ C sau khi SHA-256 match = file được nhận hoàn chỉnh.

Nếu nhóm chọn phương án này, mỗi leg cần state riêng: packet number/sequence, sent buffer, ACK ranges, RTT, RTO, `rwnd`, `cwnd`, pacer và queue.

---

## 13. Concurrency và tổ chức code

Assignment yêu cầu server xử lý nhiều client đồng thời và cho phép multi-threading hoặc asynchronous I/O. Với yêu cầu nhóm đặt ra về raw socket và tránh high-level networking abstractions, một hướng triển khai là dùng `socket` kết hợp threading và queue/scheduler tự quản lý.

### 13.1 Server process (mô hình gợi ý)

```text
server.py
  ├── HTTP listener thread (server UI :3000)
  ├── TCP control listener thread (:8080)
  │     └── handler cho từng client connection
  ├── UDP receive loop (:9000)
  ├── transport/scheduler worker(s)
  └── shared server state
        ├── sessions
        ├── user presence
        ├── UDP connection table
        ├── relay queues
        └── transport state per connection
```

### 13.2 Client process (mô hình gợi ý)

```text
client.py
  ├── Local HTTP listener thread (127.0.0.1:3000)
  ├── TCP client connection/receiver
  ├── UDP socket receive loop
  ├── local command/event queues
  └── transport state
        ├── reliability
        ├── flow control
        ├── congestion control
        └── pacer/scheduler
```

Đây là logical decomposition; thread count và synchronization cần chọn phù hợp, tránh share mutable transport state không có quy ước owner.

### 13.3 Quy tắc kiến trúc

- UI không truy cập trực tiếp state nội bộ của transport.
- Application/backend không tự gọi UDP `sendto()` ở mọi nơi; việc gửi nên qua transport/scheduler API.
- Network layer không phụ thuộc khái niệm user/chat/file nhiều hơn metadata cần thiết để relay.
- Data processing/router chịu trách nhiệm map user, conversation, file transfer sang stream/connection.
- Queue và relay buffer phải có giới hạn để tránh memory growth.
- Socket receive/send errors, timeout và disconnect phải được xử lý để không làm crash toàn server.

---

## 14. Ràng buộc assignment và thư viện

### 14.1 Yêu cầu chính thức

Đề bài yêu cầu sử dụng raw sockets và cấm high-level networking libraries/frameworks như Flask/Django và WebSockets. Đề cũng yêu cầu hỗ trợ concurrency, custom application protocol, sequencing/sliding window, ACK/retransmission, congestion control và local network execution.

### 14.2 Hướng triển khai an toàn

| Nhiệm vụ | Hướng triển khai |
|---|---|
| TCP client/server | Python `socket.SOCK_STREAM` |
| UDP client/server | Python `socket.SOCK_DGRAM` |
| HTTP frontend/backend listener | Tự xử lý HTTP trên raw TCP socket nếu cần tuân thủ nghiêm ngặt raw socket requirement |
| Concurrency | `threading`/synchronization/queue tự tổ chức hoặc cơ chế được giảng viên chấp thuận |
| Reliability | Tự implement ACK/SACK/RTO/retransmission |
| Flow Control | Tự implement rwnd/sliding window/Ring Buffer/probe timer |
| Congestion Control | Tự implement CUBIC |
| Pacer | Tự implement token bucket/scheduler |
| UI | HTML/CSS/JavaScript đơn giản; browser chỉ gọi HTTP local API, không gửi raw UDP |

### 14.3 Không sử dụng

Tránh các framework/thư viện thay thế phần networking hoặc protocol cần tự xây dựng, ví dụ:

- Flask, Django, FastAPI hoặc web framework tương tự.
- WebSockets/Socket.IO.
- Scapy.
- aioquic hoặc QUIC/transport implementation có sẵn.
- Twisted hoặc networking framework tương tự.
- Thư viện cung cấp sẵn CUBIC, reliability, sliding window, packet pacing hoặc custom transport.

Việc một module thuộc Python standard library không tự động có nghĩa là module đó phù hợp. Cần xét abstraction mà module cung cấp và constraint của giảng viên. `socket` là API raw socket được yêu cầu; frontend browser APIs như `fetch()` chỉ dùng để gọi local HTTP UI/API, không thay thế custom UDP transport.

---

## 15. Short run examples

Các IP dưới đây chỉ là ví dụ. IP thực tế phải lấy từ network adapter của Machine A.

### 15.1 Chạy server trên Machine A

```powershell
python server.py
```

Output minh họa:

```text
[SERVER] LAN IPv4: 192.168.1.10
[SERVER] Frontend: TCP 0.0.0.0:3000
[SERVER] Backend/Control: TCP 0.0.0.0:8080
[SERVER] UDP Transport: UDP 0.0.0.0:9000
[SERVER] Ready
```

Truy cập server dashboard từ A hoặc LAN nếu đã expose:

```text
http://127.0.0.1:3000/        # từ chính A
http://192.168.1.10:3000/     # từ B/C nếu dashboard được mở ra LAN
```

### 15.2 Chạy client trên Machine B

```powershell
python client.py --server 192.168.1.10 --tcp-port 8080 --udp-port 9000 --ui-port 3000
```

Client process:

- bind local UI listener vào `127.0.0.1:3000`;
- kết nối TCP tới `192.168.1.10:8080`;
- mở UDP socket và gửi tới `192.168.1.10:9000`.

Browser trên B mở:

```text
http://127.0.0.1:3000/
```

Machine C chạy lệnh tương tự và mở local URL tương tự trên chính C.

### 15.3 Test nhiều client trên một máy

Có thể chạy server và nhiều client trên cùng máy để test logic ban đầu bằng loopback, nhưng mỗi local client UI phải dùng port khác nhau, ví dụ `3001`, `3002`, ... để tránh xung đột. UDP client source ports có thể để OS cấp tự động.

---

## 16. Network setup và troubleshooting

1. A, B, C phải có thể giao tiếp qua LAN/Wi-Fi.
2. Kiểm tra LAN IPv4 của A bằng `ipconfig` trên Windows.
3. A phải bind server listener đúng interface (`0.0.0.0` hoặc IP LAN cụ thể).
4. Windows Firewall trên A phải cho phép inbound TCP `3000`, TCP `8080` và UDP `9000` theo nhu cầu.
5. Guest Wi-Fi/client isolation có thể chặn B/C giao tiếp trực tiếp với A; cần kiểm tra chính sách router.
6. Không dùng IP Docker/WSL/VirtualBox nhầm với Wi-Fi LAN IP của A.
7. Nếu client không kết nối được, kiểm tra protocol và port: TCP 8080 khác UDP 9000; TCP và UDP là hai transport protocol riêng.
8. Không cần port forwarding trên router nếu các máy chỉ giao tiếp trong cùng LAN và router không chặn traffic nội bộ.

---

## 17. Các quyết định còn mở cần nhóm xác nhận

| ID | Vấn đề | Đề xuất hiện tại | Trạng thái |
|---|---|---|---|
| D1 | Giao thức trên TCP 8080 | Raw HTTP/1.1 API cho Control Plane; không trộn binary protocol không framing | OPEN DECISION |
| D2 | Presence server-push | Chọn polling, long polling hoặc SSE tự triển khai | OPEN DECISION |
| D3 | File metadata | TCP Control Plane; file bytes/chunks qua UDP | Đề xuất |
| D4 | Reliability qua relay | Hop-by-hop transport reliability + end-to-end delivery receipt | Đề xuất |
| D5 | Host A có tham gia chat không? | Nếu có, cần client UI port riêng hoặc cơ chế chia sẻ listener | OPEN DECISION |
| D6 | CUBIC initial window | 2 MSS / 8 MSS theo simplified spec hay 10 MSS / infinity theo detailed design | SPEC CONFLICT |
| D7 | CUBIC pacing formula | `pacing_gain * BtlBw` hay `gain * cwnd / srtt` | SPEC CONFLICT |
| D8 | Units | Chuẩn hóa `cwnd`, `rwnd`, `bytes_in_flight`, pacing rate theo byte; sequence vẫn theo frame/offset | Cần xác nhận |
| D9 | Session ↔ UDP connection mapping | Dùng session/connection identifier đã xác thực; không tin username tự khai | Cần thiết kế chi tiết |
| D10 | Port 3000 trên host nếu host cũng chạy client | Chọn port khác cho host client UI (ví dụ 3001) | OPEN DECISION |
| D11 | Assignment TCP/UDP wording | PDF có chỗ mô tả TCP reliable transfer nhưng milestone yêu cầu reliable file transfer over UDP | Cần hỏi giảng viên |
| D12 | Multi-client state/queue limits | Xác định giới hạn queue và state theo client/connection | Cần cấu hình và test |

---

## 18. Checklist implementation

### Architecture

- [ ] `server.py` khởi chạy server frontend, backend/control TCP và UDP server.
- [ ] `client.py` khởi chạy local UI, TCP client và UDP client.
- [ ] Server UI và client UI là hai giao diện khác nhau.
- [ ] Client UI chỉ bind loopback.
- [ ] Server listeners bind đúng interface và có firewall rule phù hợp.
- [ ] Client dùng A's LAN IP và đúng TCP/UDP destination port.

### TCP Control Plane

- [ ] Application-level connect/handshake có request/response rõ ràng.
- [ ] Authentication và session management.
- [ ] Presence online/offline và user list synchronization.
- [ ] Cơ chế nhận presence update được xác định.
- [ ] Session được liên kết an toàn với UDP connection.
- [ ] Giao thức trên port 8080 không bị trộn lẫn HTTP và binary framing không kiểm soát.

### UDP Data Plane

- [ ] A có UDP server tại port 9000.
- [ ] Mỗi client có UDP socket riêng và có thể gửi/nhận qua cùng socket.
- [ ] A quản lý connection endpoint/session mapping.
- [ ] Direct chat và global chat được relay đúng.
- [ ] File metadata/control và file chunks được phân chia rõ TCP/UDP.
- [ ] Relay queue có giới hạn và backpressure.

### Transport mechanisms

- [ ] Reliability ACK/SACK/RTO/Fast Retransmit/reassembly.
- [ ] Flow Control rwnd/sliding window/Ring Buffer/WND_PROBE.
- [ ] Congestion Control CUBIC/slow start/loss recovery/timeout.
- [ ] Pacer token bucket và MSG-before-FILE priority.
- [ ] Mọi state đúng scope theo connection/direction.
- [ ] Tôn trọng đồng thời congestion window, receive window và pacer.

### Constraints and tests

- [ ] Dùng raw `socket` cho TCP/UDP networking.
- [ ] Không dùng web framework, WebSocket hoặc transport/congestion library có sẵn.
- [ ] HTTP listener được triển khai theo cách tương thích với assignment constraints.
- [ ] Có unit tests cho Reliability, Flow Control, CUBIC và Pacer.
- [ ] Có LAN integration test ít nhất hai client.
- [ ] Có test loss, reorder, duplicate, timeout, zero-window và concurrent clients.
- [ ] Ghi rõ test nào đã chạy và kết quả thực tế.

---

## 19. Glossary

| Thuật ngữ | Ý nghĩa |
|---|---|
| Process | Một chương trình đang chạy trong hệ điều hành |
| Socket | Endpoint giao tiếp mạng mà chương trình dùng để gửi/nhận dữ liệu |
| Bind | Gắn socket với local IP/port |
| Listen | Đặt TCP socket vào trạng thái chờ connection |
| Accept | Nhận một TCP connection mới từ pending queue |
| Connect | Client yêu cầu kết nối tới remote IP/port |
| LAN IP | Địa chỉ IP của máy trong mạng nội bộ |
| Loopback | Địa chỉ local `127.0.0.1` |
| TCP Control Plane | Kênh điều khiển: connect, login, session, presence, control metadata |
| UDP Data Plane | Kênh truyền dữ liệu: chat, file chunks và custom transport packets |
| Relay | Server nhận dữ liệu từ một client rồi chuyển tiếp đến client khác |
| `rwnd` | Receive window do receiver quảng bá |
| `cwnd` | Congestion window do sender's congestion controller quản lý |
| `SWS` | Send window size; giới hạn kết hợp flow và congestion control |
| ACK | Acknowledgement xác nhận dữ liệu đã nhận |
| SACK | Selective Acknowledgement báo các range đã nhận |
| RTO | Retransmission timeout |
| CUBIC | Congestion-control algorithm điều chỉnh congestion window |
| Pacer | Cơ chế dàn đều thời điểm gửi packet |
| Backpressure | Cơ chế làm sender chậm/dừng khi downstream không thể nhận thêm |

---

## 20. Tài liệu nguồn được dùng

Tài liệu này tổng hợp từ các tài liệu nhóm đã cung cấp và các quyết định kiến trúc được thảo luận:

1. `Assignment 1 - Distributed Streaming-based Client-Server Collaboration Application.pdf` — mục tiêu ứng dụng, raw socket requirement, concurrency, milestones và submission.
2. `congestioncontrol.docx` — `rwnd`/`cwnd`, SWS, slow start, CUBIC, loss response và pacing priority.
3. `flowcontrol-tcp.docx` — Control Plane/Data Plane split, sliding window, Ring Buffer, rwnd, persist/probe timer.
4. `reliability-tcp.docx` — header fields, ACK/SACK, CRC32, RTO, Karn's algorithm, fast retransmit, retry limit và file hash.
5. `Thiết-kế-Reliability-Flow-Control-Congestion-Control (2).docx` — kiến trúc transport/stream, relay, flow-control backpressure, congestion-control interface, CUBIC/Pacer, local UI và concurrency.
6. `Assign1-Design (1).docx` — system architecture, packet structure và application-layer protocol design.

> Khi có quyết định mới từ nhóm/giảng viên, hãy cập nhật tài liệu này và đánh dấu thay đổi. Không coi các mục `OPEN DECISION`/`SPEC CONFLICT` là yêu cầu đã được thống nhất.
