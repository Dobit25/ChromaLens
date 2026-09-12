# Kế hoạch tối ưu FPS cho ChromaLens

> **Governance note (2026-09-12):** Đây là working plan của nhánh
> `feature/fps-increment`, không thay thế `plan.md` hoặc
> `evaluation/protocol-v2.md`. Definition of Done chính thức của T15 vẫn là
> **ít nhất 20 processed FPS, p95 không quá 120 ms**, không có xu hướng tăng
> latency/RSS liên tục trong phép đo 300 giây. Mốc 15 FPS và phương án cải
> thiện tương đối bên dưới chỉ là demo floor/contingency để phân tích, không
> đủ để tự tuyên bố T15 `DONE`.

**Thời gian thực hiện:** 11–16/09/2026  
**Quỹ thời gian:** tương đương 5 ngày công cho mỗi thành viên, tối đa 4 giờ/người/ngày  
**Nhân sự:** 3 người, mỗi người 20 giờ, tổng cộng 60 giờ-người  
**Phần cứng mục tiêu:** camera tích hợp và laptop cá nhân của nhóm; không có máy demo chuyên dụng  
**Mốc mã nguồn đã kiểm tra:** nhánh `main` tại commit `d876e6acaa7373928bdfc796265051a36a80d680`  
**Trạng thái:** sẵn sàng phân công; chưa bắt đầu triển khai

## 1. Kết luận điều hành

Mục tiêu trong 5 ngày là làm sản phẩm hiện tại mượt hơn nhưng không được làm giảm chất lượng phân vùng trang phục, che giấu kết quả cũ hoặc đưa ra tuyên bố “thời gian thực” khi chưa có đủ bằng chứng.

Sản phẩm hiện có **hai loại tốc độ hoàn toàn khác nhau**:

1. **Pipeline/display FPS:** số khung hình đã xử lý và hiển thị cho người dùng trong một giây.
2. **Fresh SCHP inference FPS:** số lần mô hình SCHP thực sự tạo ra một mask ngữ nghĩa mới trong một giây.

Không được gộp hai chỉ số này thành một. Kiến trúc bất đồng bộ hiện tại đã cho phép giao diện tiếp tục cập nhật giữa các SCHP keyframe bằng cách lan truyền mask gần nhất qua optical flow. Đây là phần đã làm đúng và cần được tối ưu tiếp, không xây lại từ đầu.

Chiến lược đề xuất:

- trước tiên đo riêng thời gian của từng công đoạn và tạo baseline có thể lặp lại;
- tối ưu phần lấy hình từ camera và giao diện hiển thị độc lập với phần suy luận AI;
- tối ưu tiền xử lý SCHP, cấu hình OpenVINO, hậu xử lý, optical flow và các phép tính màu/recolor bị lặp lại;
- giữ SCHP FP32 đầu vào 512×512 làm chế độ chất lượng, trừ khi phương án mới vượt qua đầy đủ cổng kiểm tra tương đương;
- giữ MediaPipe và độ phân giải 320×240 làm phương án dự phòng công khai, có nhãn rõ ràng;
- chỉ tích hợp những thay đổi có số đo chứng minh và có thể hoàn tác riêng lẻ.

Mục tiêu phát hành thực tế là **đạt tối thiểu 15 pipeline FPS ở chế độ GUI 640×360 trên laptop cá nhân được chọn làm máy tham chiếu**. Nếu giới hạn phần cứng khiến 15 FPS chưa đạt được, điều kiện chấp nhận thay thế là tăng ít nhất 20% median FPS so với baseline của chính máy đó và giảm ít nhất 15% p95 latency, với toàn bộ cổng chất lượng vẫn được giữ nguyên. Nhóm **không nên cam kết 15 SCHP mask mới mỗi giây** trên CPU hiện tại: benchmark trực tiếp của mô hình chỉ đạt 3,19 FPS, còn trong sản phẩm đang đạt khoảng 1,5–2,2 SCHP keyframe/giây. Muốn đạt 15 suy luận ngữ nghĩa mới mỗi giây sẽ cần mô hình nhẹ hơn đáng kể, phần cứng/runtime khác hoặc chấp nhận đánh đổi chất lượng sau khi kiểm chứng.

## 2. Cơ sở bằng chứng và tình trạng sản phẩm hiện tại

### 2.1 Thứ tự ưu tiên của bằng chứng

Kế hoạch này đã đối chiếu các tài liệu được cung cấp với trạng thái mới nhất của repository. Khi số liệu bàn giao cũ mâu thuẫn với nhánh `main` hiện tại, commit hiện tại và coding log mới nhất được ưu tiên.

Nguồn bằng chứng chính của dự án:

- [Repository tại commit đã kiểm tra](https://github.com/DangTrinhdzZz/ChromaLens/tree/d876e6acaa7373928bdfc796265051a36a80d680)
- [README và trạng thái demo hiện tại](https://github.com/DangTrinhdzZz/ChromaLens/blob/d876e6acaa7373928bdfc796265051a36a80d680/README.md)
- [Biên bản nghiệm thu SCHP/OpenVINO](https://github.com/DangTrinhdzZz/ChromaLens/blob/d876e6acaa7373928bdfc796265051a36a80d680/docs/t10-schp-openvino.md)
- [Báo cáo hiệu năng và AI có trách nhiệm](https://github.com/DangTrinhdzZz/ChromaLens/blob/d876e6acaa7373928bdfc796265051a36a80d680/evaluation/results/curated/performance_responsible_ai/report.md)
- [Thông tin mô hình, checksum và giới hạn bản quyền](https://github.com/DangTrinhdzZz/ChromaLens/blob/d876e6acaa7373928bdfc796265051a36a80d680/models/README.md)
- [Nhật ký triển khai và phát hành](https://github.com/DangTrinhdzZz/ChromaLens/blob/d876e6acaa7373928bdfc796265051a36a80d680/codinglog.md)

Các tài liệu rubric đánh giá, hướng dẫn AI có đạo đức, consent form, bảng nghiên cứu, thứ tự task, phân chia công việc, kế hoạch, context, hướng dẫn repository, báo cáo test webcam và ghi chú bàn giao cũng đã được đọc. Những ràng buộc liên quan đã được đưa vào kế hoạch: xử lý cục bộ, xin đồng ý khi dùng dữ liệu người thật, báo cáo số liệu trung thực, nêu rõ giới hạn, có bằng chứng regression và luôn duy trì phương án dự phòng.

### 2.2 Cấu hình product/demo hiện tại

| Hạng mục | Trạng thái tại commit đã kiểm tra |
| --- | --- |
| Sản phẩm | Ứng dụng ChromaLens chạy cục bộ với webcam/video, hỗ trợ người có rối loạn sắc giác; có giao diện Product và Diagnostic |
| Nguồn hình mặc định | Người dùng phải chủ động chọn `--webcam`; camera index 0 |
| Kích thước camera yêu cầu | 480×360; trong lần đo, driver thực tế chọn 640×360 |
| Backend phân vùng chính | `schp-atr` |
| Mô hình | SCHP ResNet-101 human parsing, huấn luyện theo 18 lớp ATR; ChromaLens dùng upper-clothes, skirt, pants và dress |
| Đầu vào mô hình | Cố định 512×512 |
| Runtime production | OpenVINO 2025.4.1, FP32, CPU; chế độ `auto` ưu tiên IR đã xác minh |
| Lập lịch webcam | Một worker SCHP bất đồng bộ; mailbox pending/completed dung lượng 1; Farneback optical flow ở 1/4 độ phân giải; giới hạn tuổi mask 2.000 ms |
| Lập lịch video | Mặc định suy luận đồng bộ từng frame để kết quả đánh giá có thể tái lập |
| Backend dự phòng | `mediapipe-selfie-torso`; person mask kết hợp heuristic thân người/khuôn mặt, không tương đương semantic parsing của SCHP |
| UI/rendering | Camera OpenCV đặt trong khung Product/Diagnostic bên ngoài được dựng bằng Pillow |
| Pipeline màu | White balance từng frame, trích màu trong mask bằng K-means xác định, phân tích rủi ro CVD, recolor chọn lọc, matching và rendering |
| Kiểm thử tự động mới nhất | 302 test pass trong release gate gần nhất được ghi nhận |
| Máy đã đo | Lenovo 83DV, Intel Core i5-13450HX, RAM 15,78 GiB, Windows, Python 3.10.20 |
| Sensor-to-photon latency | Chưa đo |

SCHP được phát triển cho human parsing chi tiết và sửa nhiễu nhãn, không phải mô hình video edge siêu nhẹ. Điều này phù hợp với vai trò semantic của nó nhưng không đồng nghĩa với throughput cao khi chạy live ([bài báo SCHP](https://arxiv.org/abs/1910.09777)).

### 2.3 Hiệu năng hiện đã đo

Các số liệu sau được đo trên laptop cá nhân Lenovo 83DV. Do nhóm không có kinh phí cho máy demo riêng, máy này được dùng làm **máy tham chiếu ban đầu** cho việc tối ưu. Kết quả chỉ có hiệu lực với cấu hình máy/camera đã ghi, không đại diện cho mọi laptop và không phải sensor-to-photon latency.

| Cấu hình | Pipeline FPS | SCHP FPS mới | Latency p50/p95 đã báo cáo | Ý nghĩa |
| --- | ---: | ---: | ---: | --- |
| SCHP đồng bộ cũ, 640×480, headless | 0,89 | Xấp xỉ pipeline FPS | 1.195/1.411,65 ms, từ lúc `read()` trả về đến render | Cho thấy vì sao suy luận SCHP từng frame làm nghẽn sản phẩm |
| SCHP async hiện tại, 640×480, headless | 11,82 | 2,21 | 110/171,15 ms, từ `read()` trả về đến render | Kết quả 640×480 tốt nhất hiện có |
| SCHP async GUI, yêu cầu 480×360 nhưng thực tế 640×360 | 10,75 | 1,48 | 110/156 ms, từ `read()` trả về đến khi gửi frame cho GUI | Lần đo cuối của lệnh mặc định |
| Cùng chế độ GUI 640×360, lần chạy trước | 13,75 | 1,46 | 78/141 ms | Cho thấy độ biến thiên đáng kể giữa các lần chạy |
| SCHP async GUI, dự phòng 320×240 | 18,71 | 1,58 | 32/63 ms | Đường hiển thị nhanh hơn; đầu vào mô hình vẫn là 512×512 |
| OpenVINO IR trực tiếp, CPU sync/latency | — | 3,19 | Inference median 298,89 ms | Xấp xỉ trần tính toán cho một inference |
| OpenVINO IR trực tiếp, CPU async/throughput | — | 3,80 | Median latency 1.185,31 ms với 5 request | Throughput cao hơn nhưng latency live không phù hợp |
| OpenVINO IR trực tiếp, GPU sync | — | 1,75 | 564,89 ms | Chậm hơn CPU trên máy đã đo |
| OpenVINO IR trực tiếp, GPU async | — | 1,78 | 2.245,87 ms | Không phù hợp với product/hardware hiện tại |

Lần chạy GUI mặc định cuối cùng xử lý 120 frame, giữ 86 mẫu đo, kết thúc với mask propagated có tuổi 968 ms, ghi nhận 65 lần ghi đè frame camera và 103 lần ghi đè mailbox inference, đồng thời đánh dấu 14 frame degraded. Một số frame “degraded” thực chất chỉ là trường hợp phân tích không áp dụng được bình thường, ví dụ chỉ có một cụm màu trong khi đánh giá rủi ro cần cặp hai màu. Vì vậy phải tách degraded theo reason code trước khi coi đây là tỷ lệ lỗi hiệu năng.

Baseline MediaPipe lịch sử từng đạt 19,728 FPS ở webcam GUI và 24,169 FPS với video headless. Tuy nhiên MediaPipe dùng hợp đồng phân vùng khác nên đây chỉ là bằng chứng cho chế độ dự phòng, không chứng minh có thể thay SCHP mà không mất chức năng. Google mô tả Selfie Segmenter là mô hình person/background nhị phân, còn Selfie Multiclass chỉ có một lớp clothes tổng hợp ở 256×256; cả hai không trực tiếp cung cấp phân biệt upper/lower/dress/skirt như SCHP ([Google MediaPipe Image Segmenter](https://developers.google.com/edge/mediapipe/solutions/vision/image_segmenter)).

### 2.4 Phạm vi phần cứng thực tế của nhóm

Trong sprint này, nhóm chỉ tối ưu trên camera tích hợp của laptop cá nhân. Không mua GPU, camera hoặc máy demo mới và không lấy kết quả cloud/server làm FPS của sản phẩm local.

Quy tắc đo trên laptop cá nhân:

- Chọn **một laptop và camera tích hợp làm máy tham chiếu chính**, trước mắt là Lenovo 83DV đã có baseline. Mọi cổng release chính được quyết định trên máy này.
- Hai thành viên còn lại có thể chạy compatibility smoke test trên laptop của mình, nhưng kết quả phải để riêng theo `machine_id`; không lấy trung bình FPS giữa các máy khác cấu hình.
- Mọi so sánh before/after phải chạy trên cùng laptop, cùng camera, cùng độ phân giải thực tế, cùng power mode và cùng điều kiện nền.
- Dùng video cố định để so sánh thay đổi code có thể tái lập; dùng webcam laptop cho nghiệm thu trải nghiệm cuối.
- Nếu sau này chuyển sang laptop khác, phải tạo baseline mới cho laptop đó. Không dùng số liệu Lenovo 83DV để cam kết hiệu năng trên máy chưa đo.
- Tối ưu phải ưu tiên cách chạy tốt trên CPU laptop phổ thông và luôn giữ fallback. Không xây giải pháp chỉ hoạt động trên GPU rời của một thành viên.

### 2.5 Những phần đã hoàn thành, không được làm lại

- Thread lấy frame mới nhất từ webcam với mailbox dung lượng 1.
- Telemetry đếm frame camera bị ghi đè.
- Worker SCHP keyframe bất đồng bộ với mailbox hữu hạn.
- Lan truyền mask sang frame hiện tại bằng optical flow.
- Telemetry về nguồn mask, tuổi mask, keyframe và SCHP FPS.
- K-means chỉ fit tối đa 4.096 pixel trang phục được chọn theo cách xác định.
- Chuyển đổi Lab giới hạn trong bounding box của trang phục.
- Một lần inverse warp đa kênh cho logits SCHP.
- Các phương án SCHP đầu vào nhỏ hơn và INT8 đã thử nhưng bị loại.
- MediaPipe và 320×240 đã tồn tại dưới dạng fallback rõ ràng.

Các task kiểu “tạo capture thread”, “tạo latest-frame buffer” hoặc “chuyển SCHP sang async” đã lỗi thời đối với `main` hiện tại.

## 3. Chẩn đoán bottleneck

### 3.1 Mô hình hiện tại có mâu thuẫn với mục tiêu FPS không?

**Nếu mục tiêu là 15 semantic mask mới/giây trên CPU này: có.** Mô hình SCHP FP32 512×512 chỉ đạt 3,19 FPS trong benchmark CPU trực tiếp và khoảng 1,5–2,2 keyframe mới/giây bên trong ứng dụng. Chỉ thay đổi cách lập lịch không thể đưa mô hình hiện tại lên 15 inference mới/giây.

**Nếu mục tiêu là giao diện sản phẩm phản hồi ở 15–18 FPS: chưa chắc.** Kiến trúc async-keyframe hiện tại có thể tách tốc độ hiển thị khỏi tốc độ inference, miễn là mask propagated luôn có nhãn nguồn, có giới hạn tuổi, được kiểm tra hợp lệ và bị xóa khi không còn an toàn.

Do đó:

- phần chất lượng semantic tập trung tăng fresh SCHP FPS và giảm tuổi mask;
- phần display FPS tập trung độc lập vào capture, optical flow, phân tích màu, recolor và presentation;
- không gọi mask propagated là inference AI mới;
- không được tự động đổi họ mô hình mà không thông báo.

### 3.2 FPS thấp có phải chỉ do cấu hình máy không?

Không. Bằng chứng cho thấy ba nhóm nguyên nhân:

1. **Chi phí mô hình:** một SCHP inference trực tiếp mất khoảng 299 ms median. Đây vẫn là bottleneck chính của fresh-mask.
2. **Chi phí xử lý theo số pixel:** chỉ cần giảm camera/output từ 640×360 xuống 320×240 đã tăng GUI FPS từ 10,75–13,75 lên 18,71, trong khi SCHP FPS vẫn gần 1,5. Như vậy phần hiển thị/phân tích tăng theo số pixel, còn mô hình vẫn cố định 512×512.
3. **Điều kiện máy và camera/backend:** hai lần chạy cùng cấu hình GUI cho kết quả 10,75 và 13,75 FPS. Power mode, nhiệt độ, tiến trình nền, camera backend, độ phân giải thực tế và cấu hình thread OpenCV/OpenVINO đều phải được khóa và ghi nhận.

OpenCV nêu rõ hành vi của capture property phụ thuộc phần cứng, driver và API backend. Vì vậy nhóm phải ghi **giá trị thực tế** của width, height, FPS, backend và kết quả thiết lập buffer thay vì chỉ tin vào tham số đã yêu cầu ([OpenCV Video I/O properties](https://docs.opencv.org/4.13.0/d4/d15/group__videoio__flags__base.html)).

### 3.3 Các hotspot phía hiển thị cần đo để xác nhận hoặc loại bỏ

Các mục sau mới là giả thuyết cho tới khi có stage timing:

- Farneback dense optical flow ở 1/4 độ phân giải trên phần lớn frame hiển thị;
- sao chép mask nhiều lần và cấp phát remap grid theo từng vùng;
- white-balance diagnostics và color conversion toàn frame mỗi lần lặp;
- phân cụm màu và gán cluster cho mọi display frame dù semantic mask chỉ là propagated;
- lặp lại CVD candidate search và CIEDE2000 cho những cụm màu gần như không đổi;
- chuyển đổi Lab và blend recolor toàn frame trong khi chỉ ROI trang phục thay đổi;
- tạo canvas Pillow, vẽ, đổi BGR↔RGB và copy ở từng frame presentation;
- hành vi `imshow`/event wait và chế độ camera do driver thương lượng.

Microbenchmark presentation hiện tại ở 640×480 khoảng 15,5 ms cho Product và 11,9 ms cho Diagnostic. Đây không phải nguyên nhân duy nhất khiến sản phẩm chỉ đạt 10–14 FPS, nhưng vẫn đủ lớn để tối ưu sau khi xác nhận trong vòng lặp thật.

## 4. Mục tiêu và các cổng nghiệm thu bắt buộc

### 4.1 Mục tiêu phát hành trên laptop tham chiếu

Kết quả được tính bằng median của ba lần chạy có kiểm soát sau warm-up ba giây. Không dùng một lần chạy tốt nhất làm bằng chứng nghiệm thu.

| Chỉ số | Số liệu hiện tại | Mục tiêu tối thiểu | Mục tiêu cao hơn |
| --- | ---: | ---: | ---: |
| Pipeline FPS GUI 640×360 thực tế | 10,75 và 13,75 | ≥15,0; hoặc tăng ≥20% nếu bị giới hạn phần cứng | ≥18,0 |
| GUI 640×360, p50 từ `read()` trả về đến submit | 78–110 ms | ≤70 ms | ≤55 ms |
| GUI 640×360, p95 từ `read()` trả về đến submit | 141–156 ms | ≤120 ms | ≤90 ms |
| Pipeline FPS 640×480 headless | 11,82 | ≥14,0 | ≥16,0 |
| Fresh SCHP keyframe FPS | 1,46–2,21 live; 3,19 direct sync | ≥2,3 trong GUI 640×360 có kiểm soát | ≥2,7 |
| Mask age p95 | Chưa báo cáo theo phân phối | ≤1.000 ms | ≤750 ms |
| Frame stale/unavailable do lỗi vận hành sau warm-up | Chưa tách riêng | ≤2% | ≤1% |
| FPS fallback GUI 320×240 | 18,71 | ≥20,0 | ≥22,0 |

Nếu không thể đạt 15 FPS mà không làm giảm chất lượng hoặc tính trung thực, bản phát hành chỉ được chấp nhận khi median FPS tăng ít nhất 20% và p95 latency giảm ít nhất 15% trên cùng laptop tham chiếu. Khi đó phải giữ fallback 320×240/MediaPipe và báo cáo rõ giới hạn phần cứng. Không được nới cổng chất lượng chỉ để đạt một con số FPS tròn.

### 4.2 Quy tắc chấp nhận một phương án tối ưu

Chỉ merge phương án khi đáp ứng ít nhất một lợi ích và toàn bộ cổng an toàn:

- tăng median pipeline FPS tối thiểu 5%; **hoặc** giảm display latency p95 tối thiểu 10%; **hoặc** cải thiện đáng kể fresh SCHP FPS/mask age;
- không làm chỉ số chính khác xấu đi quá 5% nếu không có quyết định đánh đổi được ghi rõ;
- vượt toàn bộ kiểm tra chức năng, hình ảnh, temporal, bộ nhớ và đạo đức;
- có configuration switch hoặc commit riêng có thể revert nếu thay đổi scheduling.

### 4.3 Cổng chất lượng và tính trung thực

| Cổng | Kết quả bắt buộc |
| --- | --- |
| Thay đổi runtime SCHP | Giữ cùng tập lớp trang phục trên 5 fixture cố định; per-class mask IoU ≥0,995 so với FP32/512 hiện tại; không mất lớp |
| Thay đổi propagation | Trên motion clip cố định, mean IoU giảm không quá 0,03 so với async baseline; không dùng mask quá age cap; fast-motion/occlusion phải clear hoặc báo degraded rõ ràng |
| Trích xuất màu | Giữ tên màu chính/phụ trên exact cases hiện có; chênh cluster ratio tuyệt đối ≤0,03; không sửa source frame |
| Recolor | Thay đổi pixel chỉ nằm trong risk/garment mask cho phép; đổi profile/severity phải vô hiệu cache ngay |
| UI | Pixel camera không bị che trừ khi người dùng bật cover; Product/Diagnostic controls và telemetry vẫn đúng |
| Tests | Toàn bộ 302 test hiện có và các test performance contract mới phải pass |
| Bộ nhớ | Soak 5 phút sau warm-up không có RSS tăng liên tục qua 4 cửa sổ; RSS cuối không cao hơn steady-state median quá 25 MiB; queue/cache phải có giới hạn |
| Metrics | Báo riêng pipeline FPS, fresh SCHP FPS, mask source/age, capture/inference drops, p50/p95, resolution/backend thực tế và degradation theo reason code |
| Tuyên bố latency | Tiếp tục ghi sensor-to-photon là `NOT_MEASURED` nếu chưa đo bằng thiết bị đồng bộ bên ngoài |
| Dữ liệu/đạo đức | Xử lý cục bộ; không dùng video người thật thiếu consent; profile là lựa chọn người dùng, không phải chẩn đoán; không commit/upload frame người thật |

Các phương án SCHP đầu vào 256/384 và hai candidate NNCF INT8 không được đưa vào bốn ngày đầu vì đã thất bại ở cổng class/IoU. Chỉ mở lại nếu có tập calibration/validation có consent và đại diện tốt hơn đáng kể, đồng thời product owner phê duyệt đây là hướng nghiên cứu riêng.

## 5. Quy trình đo trước khi tối ưu

### 5.1 Khóa môi trường benchmark

Trước mỗi chuỗi benchmark, ghi lại:

- Git commit và trạng thái clean/dirty;
- SHA-256 của checkpoint, IR và manifest;
- phiên bản Python, NumPy, OpenCV, OpenVINO, MediaPipe, DaltonLens và pytest;
- `machine_id`, hãng/model laptop, CPU, RAM, GPU nếu có, phiên bản Windows, tên camera tích hợp, OpenCV API backend, width/height/FPS/fourcc thực tế;
- tên CPU/GPU, OpenVINO compiled-model properties, số thread, số stream và số inference request;
- trạng thái cắm sạc, Windows/Lenovo power mode, nhiệt độ CPU trước/sau nếu lấy được và ứng dụng nền;
- Product/Diagnostic mode, theme, cover, backend, runtime, live mode, resolution yêu cầu, warm-up, duration và GUI/headless.

Không điều chỉnh hệ điều hành trong lúc lấy baseline. Đầu tiên đo cấu hình hiện tại, sau đó mỗi lần chỉ thay đổi một biến. Các lượt A/B quyết định release phải chạy trên laptop tham chiếu; laptop khác chỉ dùng để kiểm tra khả năng khởi động và lỗi tương thích.

### 5.2 Ma trận benchmark rút gọn cho quỹ 60 giờ

Dùng một clip 60 giây cố định để tái lập và webcam tích hợp để đo trải nghiệm thật. Vì nhóm chỉ có 60 giờ, case P0 phải hoàn thành và chạy ba lần sau warm-up; case P1 chỉ chạy một lượt chẩn đoán, sau đó mở rộng khi P0 đã hoàn tất.

| Ưu tiên | Case | Nguồn | Backend/chế độ | Kích thước | Mục đích |
| --- | --- | --- | --- | --- | --- |
| P0 | B01 | Webcam laptop preview-only | Không AI | Resolution thực tế | Trần camera + UI |
| P1 | B02 | Video cố định | Không AI hoặc fixture bypass | 640×360 | Trần decode/copy |
| P1 | B03 | Video cố định | SCHP sync | 640×360 | Chi phí phân tích từng frame và khả năng tái lập |
| P0 | B04 | Webcam laptop | SCHP async | 640×360 thực tế | Case nghiệm thu sản phẩm chính |
| P1 | B05 | Webcam laptop | SCHP async | 640×360 thực tế | Chi phí Diagnostic telemetry |
| P1 | B06 | Webcam laptop | SCHP async | 640×480 | Đối chiếu mốc 11,82 FPS cũ |
| P0 | B07 | Webcam laptop | SCHP async | 320×240 | Nghiệm thu fallback tốc độ |
| P0-smoke | B08 | Webcam laptop | MediaPipe | 640×360 thực tế | Xác minh fallback khởi động; không dùng làm semantic equivalence |
| P0 | B09 | 5 fixture công khai | SCHP hiện tại/candidate | Native + input 512 | Cổng class/IoU |
| P0 | B10 | Motion clip cố định | SCHP async hiện tại/candidate | 640×360 | Mask age, propagation IoU và hành vi stale |

### 5.3 Stage timer ưu tiên theo quỹ thời gian

P1 chỉ cần thêm các timer P0 đủ để xác định bottleneck của vòng lặp thật:

1. capture wait/read và tuổi frame từ capture đến consume;
2. tổng segmentation adapter và riêng optical-flow propagation;
3. white balance;
4. color extraction;
5. risk + recolor + matching;
6. render camera view;
7. compose presentation Product/Diagnostic;
8. `imshow`/event wait và tổng loop time.

P3 dùng microbenchmark riêng để tách SCHP thành prepare-input, OpenVINO infer, restore-logits và argmax/softmax/components. Chỉ thêm timer chi tiết hơn vào full pipeline khi một nhóm P0 chiếm ít nhất 20% loop time. Cách này tránh dùng quá nhiều giờ để instrument các stage nhỏ.

Mỗi stage P0 phải báo count, mean, p50, p95, max, số lần skip và error/degraded reason. Dữ liệu timer dùng bounded deque hoặc streaming aggregate. Phải so sánh khi bật/tắt instrumentation và overhead không vượt 2% tổng loop time.

## 6. Cơ cấu nhóm và quyền sở hữu file

Dùng tên vai trò P1–P3 cho tới khi product owner gán người cụ thể.

| Người | Vai trò | File/module sở hữu chính | Không tự ý sửa nếu chưa có phê duyệt |
| --- | --- | --- | --- |
| **P1** | Performance lead và integration owner | Metrics, benchmark scripts, environment manifest, acceptance report, integration branch, giải quyết merge trong `app.py`/`pipeline.py` | Semantic mô hình và hành vi UI nếu chưa được P2/P3 review |
| **P2** | Phụ trách capture, renderer và presentation | `camera.py`, `renderer.py`, `presentation.py`, test camera/GUI | SCHP backend, segmentation contract, color science |
| **P3** | Phụ trách inference và chi phí phân tích | `segmentation/schp_backend.py`, `segmentation/async_keyframes.py`, `white_balance.py`, `color_extraction.py`, `recolor.py`, test tập trung | Main-loop integration, CLI default, release tag |

Các file dễ xung đột như `app.py`, `pipeline.py`, contracts, dependency locks và lệnh release trong README chỉ do P1 tích hợp sau khi review. Quy tắc này tránh three-way merge và telemetry bị tích hợp dở dang.

## 7. Phân rã công việc chi tiết theo từng người

### 7.1 P1 — Trưởng nhóm hiệu năng và phụ trách tích hợp, 20 giờ

| ID | Module và nhiệm vụ nhỏ | Giờ | Phụ thuộc | Output/điều kiện hoàn thành |
| --- | --- | ---: | --- | --- |
| A0 | **An toàn phiên bản:** kiểm tra `main` sạch, ghi commit/model hash, tạo integration branch và push baseline tag sau khi owner duyệt | 1 | Không | Baseline khôi phục được ở local và remote |
| A1 | **Baseline P0:** chạy B01, B04, B07, B09, B10 và B08 smoke; ghi `machine_id`, camera mode, power/thermal state | 4 | A0 | JSON/CSV baseline trên laptop tham chiếu; lượng hóa biến thiên ba lượt ở case FPS |
| A2 | **Observability P0:** triển khai 8 nhóm stage timer, capture-age, reason counter và environment manifest | 4 | A1 | Timer P0 hoạt động; overhead <2%; test pass |
| A3 | **A/B harness gọn:** so hai commit/config trên cùng clip/laptop và xuất median, p50/p95, mask age, RSS | 2 | A2 | Một lệnh tạo bảng keep/reject |
| A4 | **Tích hợp:** review candidate P2/P3, giải quyết shared-file change và chạy focused test sau từng merge | 4 | A2 và candidate B/C | Integration branch xanh; mỗi candidate revert được riêng |
| A5 | **Kiểm định/báo cáo cuối:** chạy lại P0 matrix, soak 5 phút, full suite và bảng before/after | 4 | A4 | Báo cáo cuối, lệnh chạy và giới hạn laptop tham chiếu |
| A6 | **Release/rollback drill:** dependency check, clean diff, release tag và thử khôi phục baseline | 1 | A5 | Khôi phục trong ≤10 phút; tag resolve trên remote |

### 7.2 P2 — Phụ trách capture, renderer và presentation, 20 giờ

| ID | Module và nhiệm vụ nhỏ | Giờ | Phụ thuộc | Output/điều kiện hoàn thành |
| --- | --- | ---: | --- | --- |
| B0 | **Audit capture:** xác nhận capacity-one reader, resolution/FPS/backend/fourcc thực của camera laptop, buffer setting, capture age và overwrite | 2 | A0; có thể song song A1 | Không làm lại queue/thread; có báo cáo camera tham chiếu |
| B1 | **Capture microbenchmark có điều kiện:** đo preview-only; chỉ so `CAP_ANY`, MSMF, DSHOW khi capture/GUI chiếm ≥20% loop hoặc capture age tăng | 2 | B0 và A2 | Chỉ giữ backend ổn định và nhanh hơn; nếu capture không phải bottleneck thì dừng task sớm |
| B2 | **Tối ưu presentation:** cache layout, font, label, background/panel và theme asset; giảm canvas allocation và BGR↔RGB copy | 5 | Timer A2 | Presentation p50 giảm ≥25%; camera pixel và snapshot đúng |
| B3 | **Tối ưu renderer:** reuse bounded buffer, bỏ technical overlay không cần trong Product mode, chỉ dựng static text khi state đổi | 3 | B2 | Lợi ích còn trong full loop; Diagnostic không mất telemetry |
| B4 | **Stress GUI/camera laptop:** đổi mode/theme/cover/profile, disconnect/close, 320×240 và 640×360 | 3 | B1–B3 | Không deadlock, source mutation, cache/queue vô hạn hoặc lỗi control |
| B5 | **Hỗ trợ tích hợp:** commit tách biệt, benchmark delta, visual test và sửa regression tích hợp | 3 | B2–B4 và A4 | P1 tích hợp được mà không sửa segmentation file |
| B6 | **Xác nhận cuối:** kiểm tra hai theme/mode trên laptop/camera tham chiếu và smoke trên tối đa một laptop khác | 2 | A5 | Checklist và một lượt chạy cuối 60 giây trên máy tham chiếu |

### 7.3 P3 — Phụ trách inference và analytical compute, 20 giờ

| ID | Module và nhiệm vụ nhỏ | Giờ | Phụ thuộc | Output/điều kiện hoàn thành |
| --- | --- | ---: | --- | --- |
| C0 | **Profile từng pha SCHP:** đo affine preparation, tensor copy, OpenVINO, inverse-logit warp và argmax/softmax/components | 3 | A2; có thể chuẩn bị microbench trong A1 | Xếp hạng bottleneck inference/postprocess trên fixture và video cố định |
| C1 | **OpenVINO grid rút gọn:** thử default/LATENCY và thread setting auto, 4, 8 trên chính laptop tham chiếu; loại oversubscription | 3 | C0 | Chọn single-stream setting tốt nhất qua ba lần đo, mask không đổi |
| C2 | **Tối ưu propagation:** cache remap grid theo shape, tính flow một lần/frame, reuse cho mọi region, giảm copy và giữ validation | 4 | A2 và C0 | Propagation p50/p95 giảm; không tăng invalid/stale mask |
| C3 | **Scheduler phân tích:** chỉ cập nhật color/risk/candidate nặng ở fresh keyframe hoặc visual-change trigger; reuse phải có `analysis_age_ms` và bounded cache | 5 | A2; review với P1 | Cache invalidate đúng; không gọi cached result là current |
| C4 | **Tối ưu ROI:** giới hạn recolor conversion/blend trong bounding box; chưa mở lại K-means sampling nếu không phải hotspot | 2 | C3 | Full-loop tốt hơn và containment chính xác |
| C5 | **Quality/regression suite:** fixture class/IoU, motion/occlusion, màu, recolor containment, source immutability và shutdown | 2 | C1–C4 | Mỗi candidate được nhận có test |
| C6 | **Xác nhận backend cuối:** hash, compiled properties, fresh SCHP rate, mask-age distribution và fallback startup | 1 | A5 | Backend checklist hoàn tất |

OpenVINO cung cấp hai performance hint LATENCY và THROUGHPUT, đồng thời khuyến nghị benchmark trên đúng thiết bị đích. Throughput mode có thể dùng nhiều stream/request, tốn thêm bộ nhớ và tăng latency. Vì sản phẩm chỉ có một live stream và ưu tiên độ mới của kết quả, C1 phải tối ưu low latency trước; multi-request throughput chỉ là thí nghiệm có đo đạc ([OpenVINO performance hints](https://docs.openvino.ai/2025/openvino-workflow/running-inference/optimize-inference/high-level-performance-hints.html)). OpenVINO cũng có `AsyncInferQueue`, nhưng việc sử dụng là tùy chọn: ứng dụng hiện đã có scheduler latest-frame một worker và queue hữu hạn. Chỉ thay khi chứng minh được giảm mask age mà không tạo backlog hoặc xử lý frame lỗi thời ([OpenVINO AsyncInferQueue](https://docs.openvino.ai/2025/api/ie_python_api/_autosummary/openvino.AsyncInferQueue.html)).

## 8. Phần việc độc lập và quan hệ phụ thuộc

### 8.1 Có thể làm độc lập sau khi khóa baseline contract

| Công việc | Vì sao độc lập | Điểm cần phối hợp |
| --- | --- | --- |
| B0/B1 audit camera backend | Chỉ nằm trong source acquisition và preview measurement | Dùng tên metric của A2 khi instrumentation hoàn thành |
| B2 cache/static presentation | Chỉ sửa `presentation.py` và visual test | Giữ nguyên input/output contract của renderer |
| C0/C1 benchmark pha SCHP/cấu hình | Chỉ nằm trong backend và microbenchmark | Dùng cùng model/fixture hash như A1 |
| C2 tối ưu cấp phát optical flow | Chỉ nằm trong async segmentation adapter | Giữ segmentation telemetry contract |
| A/B harness của P1 | Chỉ tiêu thụ output, không đổi UI/model semantic | Cần thống nhất schema CSV/JSON |

### 8.2 Công việc có phụ thuộc bắt buộc

| Task phía sau | Phải chờ | Lý do |
| --- | --- | --- |
| Mọi tuyên bố tăng hiệu năng | Baseline A1 và timer A2 | Nếu không sẽ không biết cải thiện đến từ stage nào |
| Nghiệm thu B2/B3 | Timer presentation/renderer của A2 | Microbenchmark nhanh hơn có thể không cải thiện live loop |
| Nghiệm thu C1 | Phase profile C0 | Tránh chỉnh OpenVINO khi hậu xử lý mới là bottleneck |
| Scheduler phân tích C3 | Hợp đồng provenance/age do P1 duyệt | Dữ liệu reuse không được giả là kết quả frame hiện tại |
| Sửa `pipeline.py`/`app.py` | Cửa sổ integration do P1 điều phối | Tránh xung đột merge và state thay đổi dở dang |
| Quyết định mục tiêu cuối | Candidate B và C được đo riêng rồi mới kết hợp | Phát hiện tranh chấp CPU thread/băng thông bộ nhớ |
| Release tag | P0 matrix, soak, test và clean diff | Tag phải trỏ tới một recovery point đã xác minh |

### 8.3 Thứ tự tích hợp

1. Tạo baseline tag và integration branch.
2. Merge instrumentation và A/B harness.
3. Merge candidate presentation/capture của P2.
4. Merge candidate OpenVINO/propagation của P3.
5. Merge candidate analytical/ROI của P3.
6. Chạy combined contention test và tinh chỉnh.
7. Hoàn thành báo cáo, release tag và rollback drill.

Mỗi candidate phải benchmark độc lập trước khi kết hợp. Nếu kết quả kết hợp kém vì hai thay đổi tranh CPU core hoặc memory bandwidth, giữ phương án mang lại giá trị cao hơn và loại hoặc chỉnh lại phương án còn lại.

## 9. Lịch triển khai theo ngày

Cụm “5 ngày tính từ hôm nay đến 16/09” bao phủ 6 ngày theo lịch. Kế hoạch này quy đổi thành **20 giờ/người**, tương đương 5 ngày × 4 giờ: 3 giờ ngày 11/09; 4 giờ/ngày trong 12–14/09; 3 giờ ngày 15/09; và 2 giờ release gate ngày 16/09. Không thành viên nào làm quá 4 giờ/ngày và không bắt đầu cải tiến mới vào ngày 16/09.

### 11/09 — Ngày 1: khóa phiên bản và baseline P0, 3 giờ/người

| Người | Công việc | Output cuối ngày |
| --- | --- | --- |
| P1 | A0 trong 1 giờ; A1 trong 2 giờ; khóa metric và lệnh benchmark | Bảng commit/hash baseline, sơ đồ branch, lượt B01/B04/B07 đầu tiên |
| P2 | B0 trong 2 giờ; khảo sát B2 trong 1 giờ | Báo cáo camera/backend/resolution thực; danh sách phần presentation có thể cache |
| P3 | Hoàn thành C0 trong 3 giờ | Bảng timing từng pha SCHP trên laptop tham chiếu |

**Checkpoint:** Nếu không tái lập được `main`, model hash hoặc lệnh demo hiện tại, dừng tối ưu và sửa khả năng tái lập trước.

### 12/09 — Ngày 2: observability và các cải tiến độc lập đầu tiên, 4 giờ/người

| Người | Công việc | Output cuối ngày |
| --- | --- | --- |
| P1 | Hoàn thành 2 giờ còn lại của A1; làm 2 giờ đầu A2 | Ma trận P0 hiện tại; stage timing cốt lõi bắt đầu xuất JSON/CSV |
| P2 | B1 trong 2 giờ; B2 trong 2 giờ | Quyết định camera backend hoặc dừng B1 nếu không phải bottleneck; prototype static cache |
| P3 | C1 trong 3 giờ; bắt đầu C2 trong 1 giờ | Bảng keep/reject runtime setting; thiết kế remap-grid cache |

**Checkpoint:** Chọn hai candidate display-side và hai candidate inference/analysis có tiềm năng cao nhất. Loại các ý tưởng suy đoán không tác động tới top contributor đã đo.

### 13/09 — Ngày 3: triển khai candidate tách biệt, 4 giờ/người

| Người | Công việc | Output cuối ngày |
| --- | --- | --- |
| P1 | Hoàn thành 2 giờ còn lại của A2; làm A3 trong 2 giờ | Công cụ A/B một lệnh; instrumentation branch xanh |
| P2 | Hoàn thành B2 trong 2 giờ; làm 2 giờ đầu B3 | Candidate presentation và phần chính của renderer kèm stage delta |
| P3 | Hoàn thành C2 trong 3 giờ; thiết kế C3 với P1 trong 1 giờ | Candidate propagation và hợp đồng analysis-age đã review |

**Checkpoint:** P1 benchmark riêng candidate của P2 và P3. Candidate không đạt ngưỡng hoặc fail quality chỉ được sửa một vòng; sau đó phải loại để bảo vệ lịch.

### 14/09 — Ngày 4: tối ưu analytical pipeline và tích hợp có kiểm soát, 4 giờ/người

| Người | Công việc | Output cuối ngày |
| --- | --- | --- |
| P1 | Hoàn thành A4 trong 4 giờ; merge instrumentation rồi từng candidate được nhận | Integration branch xanh, có benchmark delta sau từng lần merge |
| P2 | Hoàn thành 1 giờ còn lại của B3; làm B4 trong 3 giờ | Candidate renderer hoàn chỉnh và bằng chứng stress GUI/camera |
| P3 | Hoàn thành C3 trong 4 giờ | Candidate scheduler phân tích hữu hạn, có provenance rõ ràng |

**Checkpoint:** Chạy case GUI 640×360 kết hợp. Nếu FPS thấp hơn kỳ vọng từ các cải tiến riêng, kiểm tra CPU utilization, OpenCV/OpenVINO thread count, allocation pressure và tranh chấp presentation.

### 15/09 — Ngày 5: đóng băng, kiểm định và tài liệu, 3 giờ/người

| Người | Công việc | Output cuối ngày |
| --- | --- | --- |
| P1 | Làm 3 giờ đầu A5: chạy lại P0, soak và full suite | Số liệu release candidate và bảng candidate nhận/loại |
| P2 | Hoàn thành B5 trong 3 giờ | Commit tích hợp, visual regression và bằng chứng Product/Diagnostic |
| P3 | C4 trong 2 giờ; làm 1 giờ đầu C5 | Candidate ROI và focused quality test ban đầu |

**Quy tắc freeze cuối ngày:** Sau khi đặt release candidate, chỉ được commit bản sửa P0 nhằm khôi phục một cổng đã từng pass. Mỗi bản sửa phải có focused test và chạy lại benchmark bị ảnh hưởng.

### 16/09 — Chỉ release gate và bàn giao, 2 giờ/người

| Người | Công việc | Bằng chứng bắt buộc |
| --- | --- | --- |
| P1 | Hoàn thành 1 giờ còn lại của A5; làm A6 trong 1 giờ | Báo cáo cuối, tag trỏ đúng tested commit và recovery launch thành công trong 10 phút |
| P2 | Hoàn thành B6 trên final tag | Camera tích hợp của laptop tham chiếu, Product/Diagnostic controls và visual sign-off |
| P3 | Hoàn thành 1 giờ còn lại của C5; làm C6 trong 1 giờ | Model/IR hash, fresh FPS, mask-age distribution và MediaPipe fallback sign-off |

## 10. Quản lý phiên bản, backup và rollback

### 10.1 Hệ thống branch

- `perf/fps-20260911-integration`: P1 sở hữu.
- `perf/p1-observability`: công việc metrics/harness của P1.
- `perf/p2-capture-presentation`: công việc của P2.
- `perf/p3-inference-analysis`: công việc của P3.

Không ai commit trực tiếp lên `main`. P2 và P3 không merge branch của nhau. P1 tích hợp các commit đã review theo thứ tự ở Mục 8.3.

### 10.2 Commit và checkpoint

- Mỗi commit chỉ chứa một thay đổi đã đo.
- Commit message có task ID, ví dụ `perf(C2): cache optical-flow remap grids`.
- Push mỗi commit xanh trước khi bắt đầu thay đổi rủi ro tiếp theo.
- Không force-push hoặc rebase shared branch trong sprint.
- Mỗi review phải có lệnh benchmark, metric trước/sau, quality result, memory result và cấu hình bị ảnh hưởng.
- Dùng annotated tag cho recovery/release point đã xác minh. Tài liệu Git mô tả annotated tag là đối tượng phù hợp cho release, có tagger, ngày và thông điệp đi kèm ([tài liệu Git tag](https://git-scm.com/docs/git-tag)).

Đề xuất các tag bất biến:

- `perf-v0-baseline-2026-09-11`
- `perf-v1-rc-2026-09-15`
- `perf-v1-release-2026-09-16`

Checkout hiện tại và remote ref listing không hiển thị tag nào, mặc dù tài liệu cũ có nhắc `t11-demo-v1`. Vì vậy trong Ngày 1 phải xác minh lại mốc lịch sử này và không được dựa vào nó như recovery point duy nhất.

### 10.3 Git backup được gì và không backup được gì?

| Loại tài sản | Cách backup/quản lý phiên bản |
| --- | --- |
| Mã nguồn, test, tài liệu, script, cấu hình | Git commit, branch đã push và annotated tag |
| Trạng thái dependency | Các hashed lock file hiện có cộng với bản `conda list --explicit`; không nâng package chưa pin trong sprint |
| SCHP checkpoint | Tiếp tục nằm ngoài Git; giữ hai bản tại vị trí được owner phê duyệt và kiểm tra byte count/SHA-256 trước khi dùng |
| OpenVINO IR và manifest | Tiếp tục nằm ngoài Git; giữ `.xml`, `.bin` và manifest cùng nhau; ghi checksum trong release evidence |
| Dữ liệu benchmark | Track metrics/manifest gọn nhẹ nếu an toàn riêng tư; human media thô phải local và untracked |
| Cấu hình demo | Release manifest gồm commit/tag, hash, device, camera mode thực, CLI và performance mode được nhận |

### 10.4 Quy trình rollback

1. Dừng demo và lưu log cuối; không xóa bằng chứng lỗi.
2. Dùng release manifest để xác định merge/candidate commit gây lỗi.
3. Trên worktree integration/main sạch, dùng `git revert` để tạo commit mới đảo ngược thay đổi lỗi. Tài liệu chính thức của Git mô tả revert là tạo một commit mới để đảo tác động của patch cũ, đồng thời cảnh báo reset/restore có thể làm mất thay đổi chưa commit ([tài liệu Git revert](https://git-scm.com/docs/git-revert)).
4. Chạy focused test bị ảnh hưởng, smoke test và một lượt B04.
5. Nếu chưa khôi phục ngay, chạy baseline tag hoặc release tag trước đó từ thư mục/worktree sạch cùng model/IR đã bảo toàn.
6. Ghi incident, metric bị lỗi, rollback commit và phân loại nguyên nhân: code, config, dependency, camera backend hay external asset.

Mục tiêu vận hành: có thể khôi phục demo baseline trong 10 phút mà không rewrite lịch sử Git hoặc đi tìm file chưa commit.

## 11. Cây quyết định tối ưu

Quyết định dựa trên tỷ trọng stage đã đo, không dựa vào cảm giác:

| Kết quả sau A2 | Hành động | Không được làm |
| --- | --- | --- |
| SCHP infer chiếm chủ yếu, pre/post nhỏ | Giữ async architecture; chỉnh OpenVINO theo low latency; chấp nhận trần fresh FPS thực tế | Tạo thêm hàng đợi frame cũ chỉ để tăng throughput |
| SCHP postprocess >20% chu kỳ inference | Giảm copy/allocation hoặc đổi cách restore label/confidence nhưng phải qua IoU ≥0,995 | Warp ít class làm đổi argmax semantics mà không có bằng chứng |
| Optical flow >20 ms p50 | Cache grid/buffer, reuse một flow; chỉ giảm flow scale khi qua motion-clip gate | Bỏ validation hoặc tăng mask age để che lỗi |
| Presentation >15 ms p50 | Cache static layer/font/text và bỏ conversion không cần thiết | Thu nhỏ hoặc che camera viewport nếu chưa được duyệt |
| Color/risk/recolor >30% loop | Update theo event/keyframe, bounded cache, ROI transform, báo analysis age | Dùng giá trị stale như thể vừa tính cho current frame |
| Capture age tăng dù reader capacity-one | Thử backend/driver có sẵn và kiểm tra hành vi buffer thực | Mặc định cho rằng `CAP_PROP_BUFFERSIZE=1` chắc chắn có hiệu lực |
| FPS giảm dần theo nhiệt độ | Ổn định power/thermal state, ghi vào báo cáo và benchmark lại | Gán lỗi thermal throttling cho một thay đổi code |
| Memory tăng | Tìm array/cache/native buffer không hữu hạn; loại candidate cho tới khi sửa | Dùng một mẫu RSS giảm để kết luận không leak |
| Vẫn không đạt 15 FPS sau các cải tiến an toàn | Phát hành phần tăng đã đo cùng fallback 320×240/MediaPipe; mở nghiên cứu model/hardware riêng | Tự ý bật lại INT8 hoặc SCHP 256/384 đã bị loại |

## 12. Các performance mode cần bàn giao

Nếu còn thời gian, cung cấp một selector `--performance-mode` rõ ràng và vẫn giữ các low-level flag hiện có. Nếu thêm CLI tốn hơn 4 giờ, chỉ cần tài liệu hóa các lệnh tương đương.

| Mode | Backend | Thiết lập hiển thị | Mục đích | Nhãn bắt buộc |
| --- | --- | --- | --- | --- |
| `quality` | SCHP FP32/512 async | 640×360 thực tế | Semantic garment classes và demo bình thường | Hiển thị riêng pipeline FPS và fresh SCHP FPS |
| `fast` | SCHP FP32/512 async | 320×240 | Ổn định tại địa điểm demo nhưng vẫn giữ semantic SCHP | Ghi rõ capture/display resolution thấp hơn; model vẫn 512 |
| `fallback` | MediaPipe torso | Kích thước ổn định đã đo | Khôi phục khi thiếu SCHP asset/runtime hoặc cần FPS cao hơn | Ghi rõ đây là heuristic torso mask, không tương đương garment parsing |

Không được tự động chuyển giữa SCHP và MediaPipe trong im lặng. Lỗi phải có hướng xử lý và backend đang chạy phải luôn hiển thị rõ.

## 13. Rủi ro và biện pháp kiểm soát

| Rủi ro | Xác suất / ảnh hưởng | Biện pháp | Owner |
| --- | --- | --- | --- |
| Tăng FPS nhưng đổi class/biên trang phục | Trung bình / cao | Cổng class/IoU trên 5 fixture, motion clip, commit riêng | P3 |
| Cached analysis bị hiểu là kết quả hiện tại | Trung bình / cao | `analysis_source`, `analysis_frame_id`, `analysis_age_ms`, invalidation và age cap | P1/P3 |
| OpenVINO/OpenCV thread oversubscription làm GUI chậm | Trung bình / trung bình | Configuration grid, đọc thread/stream properties và combined contention test | P1/P3 |
| Camera backend khác giữa các laptop cá nhân | Cao / trung bình | Chọn một laptop tham chiếu, ghi backend/mode thực, test automatic và có fallback command | P2 |
| Nhiệt/power gây ra cải thiện giả | Cao / trung bình | Ba lần lặp, giữ AC/power/background giống nhau, ghi nhiệt độ | P1 |
| UI cache che hoặc sửa pixel camera | Thấp / cao | Pixel-level camera-rectangle test và review snapshot render | P2 |
| Queue/cache làm memory tăng | Trung bình / cao | Capacity-one/bounded structure, soak 5 phút, cache limit rõ ràng | Cả nhóm |
| Checkpoint hoặc IR thiếu/hỏng | Trung bình / cao | External backup, kiểm tra size/SHA-256/manifest, MediaPipe fallback | P3/P1 |
| Quyền phân phối checkpoint chưa được giải quyết | Trung bình / cao | Không commit/phát tán weight hoặc derived IR ngoài phạm vi owner cho phép | P1 |
| Dùng benchmark media chưa có consent | Thấp / cao | Public fixture, synthetic clip hoặc consent đã ký; local processing; không upload raw media | Cả nhóm |
| Three-way merge làm hỏng main loop | Trung bình / trung bình | Chỉ P1 tích hợp `app.py`/`pipeline.py`, thứ tự merge cố định | P1 |

## 14. Deliverable cuối cùng

Tại release gate ngày 16/09, nhóm phải bàn giao:

1. Environment/model manifest của baseline và final.
2. Stage-timing CSV/JSON hữu hạn cho toàn bộ case P0; case P1 nào đã chạy phải được ghi riêng.
3. Báo cáo before/after dùng median của ba lượt, không chọn lần cao nhất.
4. Bảng candidate nhận/loại kèm commit hash và lý do.
5. Kết quả class/IoU trên 5 fixture và kết quả motion/occlusion temporal.
6. Báo cáo RSS/latency soak 5 phút.
7. Kết quả test tự động, dependency check và clean-diff hiện tại.
8. Baseline/release annotated tag đã xác minh trên remote.
9. Lệnh chạy chính xác cho quality, fast và MediaPipe fallback.
10. Biên bản rollback drill chứng minh khôi phục trong 10 phút.
11. Một video before/after ngắn chỉ dùng media công khai, synthetic hoặc đã có consent và được xử lý cục bộ.
12. Limitation statement tiếp tục ghi `sensor-to-photon = NOT_MEASURED`, phạm vi laptop cá nhân tham chiếu, semantics của propagated mask và giới hạn quyền phân phối model.

## 15. Checklist release

- [ ] Baseline tag và final tag trỏ đúng commit đã ghi ở local và remote.
- [ ] Model/IR/checkpoint hash khớp manifest.
- [ ] Camera backend, resolution, FPS và fourcc thực tế đã được ghi.
- [ ] Median pipeline FPS GUI 640×360 đạt ít nhất 15; nếu chưa đạt, phần thiếu và fallback decision được nêu rõ.
- [ ] Fresh SCHP FPS và mask-age p50/p95 được báo riêng với display FPS.
- [ ] Không candidate nào được nhận nếu làm mất fixture class hoặc vi phạm IoU/color/recolor gate.
- [ ] Operational stale/unavailable reason được tách khỏi analytical non-applicability.
- [ ] Soak 5 phút xác nhận queue/cache hữu hạn và không có RSS/latency tăng liên tục.
- [ ] Toàn bộ test hiện có cộng test mới pass; baseline gần nhất đã biết là 302 test.
- [ ] Product/Diagnostic mode, theme, controls, camera cover và fallback command chạy trên camera tích hợp của laptop tham chiếu.
- [ ] Không commit nhầm human media thô, checkpoint, derived IR hoặc INT8 artifact đã bị loại.
- [ ] Có consent và local processing cho mọi video người thật mới.
- [ ] Sensor-to-photon vẫn ghi chưa đo nếu không có phép đo bên ngoài.
- [ ] Rollback về baseline đã xác minh thành công trong 10 phút.

## 16. Việc cần làm ngay khi bắt đầu

Trong buổi làm việc tiếp theo:

1. Gán tên thật cho P1, P2 và P3.
2. Xác nhận phân bổ 20 giờ/người, tối đa 4 giờ/ngày và quy tắc không mở task mới ngày 16/09.
3. Chọn laptop/camera tích hợp tham chiếu; xác minh `main` tại `d876e6a`, worktree sạch và model/IR hash trên máy đó.
4. Tạo và push baseline recovery tag.
5. Chạy B01, B04 và B07 trước khi sửa performance code; B06 chỉ chạy nếu cần đối chiếu baseline cũ.
6. Khóa schema của stage timing.
7. Cho P2 bắt đầu presentation/capture và P3 bắt đầu profile từng pha SCHP song song.

Nguyên tắc chi phối cả 5 ngày: **làm sản phẩm nhanh hơn bằng số liệu thực, nhưng không được tăng tốc bằng cách che giấu kết quả cũ, thay đổi semantic mà thiếu bằng chứng hoặc làm mất khả năng quay lại bản demo đã được xác minh gần nhất.**
