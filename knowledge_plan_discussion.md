**![][image1]**

Model inference: đưa dữ liệu vào model đã được huấn luyện để lấy dự đoán  
Inference khác training:

* Training: model học từ dataset, tốn nhiều thời gian và phần cứng.  
* Fine-tuning: tiếp tục huấn luyện model có sẵn bằng dữ liệu riêng.  
* Inference: chỉ chạy model đã huấn luyện để dự đoán.

Mask, bounding box và contour

* Bounding box: Là một hình chữ nhật bao quanh đối tượng.  
* Mask: Là một bản đồ có kích thước tương ứng với ảnh  
* Contour: Là đường biên của mask

Latency: thời gian từ lúc camera thu frame đến khi người dùng nhìn thấy kết quả

Frame là một mảng số, thường có cấu trúc: chiều cao × chiều rộng × 3 kênh BGR

Tensor là một cấu trúc dữ liệu mảng đa chiều, dùng để lưu trữ và xử lý các con số. Nó là dạng mở rộng của số đơn (véc-tơ) và ma trận lên nhiều chiều

OpenCV  
Open Source Computer Vision Library: là thư viện xử lý ảnh và video phổ biến, có thể sử dụng bằng Python, C++ và một số ngôn ngữ khác.

OpenCV có thể thực hiện:

* Đọc camera.  
* Resize ảnh.  
* Chuyển đổi không gian màu.  
* Làm mịn ảnh.  
* Tìm contour.  
* Vẽ viền và chữ.  
* Cân bằng trắng.  
* Hiển thị video đầu ra.

Dùng OpenCV nếu mục tiêu trước mắt là:

* Demo trên laptop.  
* Viết toàn bộ pipeline bằng Python.  
* Không cần người dùng truy cập từ điện thoại qua trình duyệt.  
* Cần hoàn thành MVP nhanh.

WebRTC  
Tập hợp các API cho phép trình duyệt:

* Truy cập camera và microphone.  
* Truyền video thời gian thực.  
* Gửi dữ liệu giữa trình duyệt và server hoặc giữa các thiết bị.

WebRTC chỉ là tầng thu nhận và truyền video.  
WebRTC phù hợp nếu muốn người dùng chỉ cần mở một website trên điện thoại. Nhưng khi đó nhóm phải xử lý thêm:

* Front-end JavaScript.  
* Camera permission.  
* Truyền video.  
* Nén và giải nén video.  
* Kết nối mạng.  
* Độ trễ.  
* HTTPS.  
* Server backend.

→ **Dùng OpenCV VideoCapture trên laptop**  
**\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_**

Segmentation là bài toán phân loại từng pixel trong ảnh

* Semantic segmentation: Mỗi pixel được gán vào một nhóm  
  * Người.  
  * Quần áo (Nếu có hai chiếc áo, có thể gộp cả hai vào cùng lớp áo)  
  * Nền.  
  * Tóc.  
  * Da.  
* Instance segmentation: Không chỉ biết pixel thuộc lớp nào mà còn tách từng đối tượng riêng biệt:  
  * Áo số 1\.  
  * Áo số 2\.  
  * Quần số 1\.  
* Human parsing: Một dạng semantic segmentation chuyên biệt cho cơ thể và trang phục con người:  
  * Tóc.  
  * Mặt.  
  * Tay.  
  * Áo trên.  
  * Quần.  
  * Váy.  
  * Giày.  
  * Túi.  
    

→ **ChromaLens phù hợp với human parsing hơn segmentation tổng quát.**

SCHP-ATR

* SCHP là Self-Correction for Human Parsing. Đây là phương pháp human parsing  
  * Input của SCHP:  
    * Một frame đã được:  
      * Resize theo kích thước model yêu cầu.  
      * Chuyển BGR thành RGB.  
      * Chuẩn hóa giá trị pixel.  
      * Chuyển thành tensor.  
  * Output của SCHP  
    * Model tạo ra một tensor chứa điểm cho mỗi lớp tại từng pixel.  
    * Sau softmax và argmax, bạn nhận được:  
      * 0  → nền  
      * 1  → tóc  
      * ...  
      * lớp upper-clothes  
      * lớp pants  
      * lớp skirt  
      * ...  
    * Từ đó tạo mask:  
      * upper\_mask \= class\_map \== UPPER\_CLOTHES\_ID  
      * pants\_mask \= class\_map \== PANTS\_ID  
* ATR là dataset/model configuration mà SCHP có thể sử dụng. Model SCHP đã được huấn luyện trên ATR có thể phân biệt khoảng 18 lớp, bao gồm:  
  * Upper-clothes: áo trên.  
  * Pants: quần.  
  * Skirt: váy ngắn.  
  * Dress: váy liền.  
  * Belt.  
  * Shoes.  
  * Bag.  
  * Scarf.  
  * Các bộ phận cơ thể.

[GitHub \- GoGoDuck912/Self-Correction-Human-Parsing](https://github.com/GoGoDuck912/Self-Correction-Human-Parsing)		  
Repo chính thức cung cấp model pretrained cho ATR và LIP. Với ATR, repo báo cáo mIoU khoảng 82,29% trên tập kiểm thử; đây là kết quả benchmark của tác giả, không đảm bảo tương đương trên camera thực tế

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

Sau segmentation mới hoàn thành mask quần áo, chưa mask màu. Cần phải:

* Lấy pixel nằm trong mask áo.  
* Phân cụm màu.  
* Tạo submask cho từng cụm màu.  
* Chỉ recolor cụm có rủi ro.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
Tracking giúp hệ thống biết rằng chiếc áo trong frame hiện tại vẫn là chiếc áo ở frame trước

Optical Flow  
Optical flow ước tính pixel hoặc điểm ảnh đã di chuyển từ frame trước đến frame sau như thế nào. Từ trường chuyển động này, hệ thống có thể dịch chuyển mask cũ sang vị trí mới.  
Ưu điểm

* Không cần detector phức tạp.  
* Phù hợp với chuyển động liên tục.  
* Có thể chạy segmentation mỗi 2–3 frame rồi dùng optical flow ở giữa.

Nhược điểm

* Có thể bị drift: mask lệch dần khỏi đối tượng.  
* Khó khi camera chuyển động nhanh.  
* Khó khi đối tượng bị che khuất.  
* Khó khi quần áo và nền có texture giống nhau.

ByteTrack  
ByteTrack là một thuật toán multi-object tracking theo hướng tracking-by-detection.  
Quy trình:

1. Detector tìm các đối tượng trong mỗi frame.  
2. Mỗi đối tượng có bounding box và confidence.  
3. ByteTrack ghép box ở frame trước và frame sau.  
4. Mỗi đối tượng nhận một track\_id.

ByteTrack tận dụng các detection có confidence thấp trong bước liên kết, thay vì loại bỏ tất cả ngay từ đầu.  
Nhược điểm

* ByteTrack chủ yếu theo dõi bounding box. Nó không tự tạo mask chính xác.  
* Nếu dùng ByteTrack, cần phải:  
  * Detector/segmenter → box \+ mask  
  * ByteTrack → ID ổn định của box  
  * ID ổn định → gắn mask tương ứng

ByteTrack phù hợp hơn khi có nhiều người hoặc nhiều món đồ trong ảnh.

SAM 2 & tap-to-select  
SAM 2 là model segmentation có khả năng nhận prompt trên ảnh/video. Prompt có thể là:

* Một điểm người dùng nhấn.  
* Một bounding box.  
* Một mask ban đầu.

Trong tap-to-select:

* Người dùng chạm vào chiếc áo.  
* SAM 2 tạo mask.  
* Model duy trì mask đó qua các frame video.

SAM 2 giỏi tách đối tượng được chọn, nhưng không biết trả về nhãn “áo”, “quần” hay “váy”. Nó là promptable segmentation, không phải clothing classifier.

→ SAM 2 phù hợp với chế độ bổ sung:

* Nếu hệ thống chọn sai, người dùng chạm vào món đồ muốn theo dõi.

Không nên đặt SAM 2 làm nền tảng chính cho MVP vì:

* Model tương đối nặng.  
* Tích hợp video phức tạp hơn.  
* Cần quản lý memory state.  
* Không tự cung cấp semantic garment label.

**Tracking cho MVP:**   
Giai đoạn đầu:

* Chạy segmentation mỗi frame.  
* Làm mịn mask theo thời gian.  
* Làm mịn kết quả màu bằng exponential moving average.

Nếu vẫn chậm:

* Chạy SCHP mỗi 2–3 frame.  
* Dùng optical flow ở các frame trung gian.

Chỉ thêm ByteTrack khi cần nhiều đối tượng và chỉ thêm SAM 2 khi cần tap-to-select.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
Color constancy: Gray-world và temporal smoothing

Color constancy là nỗ lực ước tính màu vật thể tương đối độc lập với nguồn sáng.   
Nó không thể tái tạo màu thật tuyệt đối trong mọi trường hợp, nhưng có thể giảm biến thiên.

Cùng một chiếc áo có thể có màu khác nhau. Màu camera ghi nhận phụ thuộc vào:

* Màu vật thể.  
* Màu nguồn sáng.  
* Độ sáng.  
* Cân bằng trắng của camera.  
* Bóng đổ.  
* Phản xạ.  
* Camera sensor.  
* Auto exposure.  
  


Gray-world White Balance  
Gray-world dựa trên giả định: Nếu lấy trung bình đủ nhiều màu trong toàn cảnh, màu trung bình của cảnh nên gần màu xám trung tính.  
→ Nếu kênh đỏ trung bình cao hơn xanh, thuật toán suy luận nguồn sáng đang hơi đỏ/vàng và điều chỉnh các kênh.

![][image2]  
[Class cv::xphoto::GrayworldWB — OpenCV Tutorials](https://docs.opencv.org/5.0/extra_modules/classcv_1_1xphoto_1_1GrayworldWB.html)	

Gray-world có thể sai khi toàn cảnh gần như chỉ có một màu.  
Ví dụ:  
Người mặc áo đỏ đứng trước tường đỏ.  
Camera nhìn gần toàn bộ vào một chiếc áo xanh.  
Ánh sáng quá yếu.  
Nhiều pixel bị cháy sáng.  
Vì vậy nên:  
Loại pixel gần đen hoặc gần trắng bị clipping.  
Không sử dụng các pixel có saturation bất thường.  
Có thể ước tính trên toàn cảnh hoặc vùng nền đủ đa dạng.  
Ghi nhận chất lượng ánh sáng để điều chỉnh confidence.

Temporal smoothing  
Nếu tính white balance độc lập ở mỗi frame, hệ số có thể thay đổi liên tục → Video đầu ra sẽ nhấp nháy  
![][image3]  
\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
Color extraction  
CIELAB, robust median và K-means

RGB phù hợp để hiển thị trên màn hình nhưng khoảng cách số học trong RGB không phản ánh tốt mức khác biệt mà con người cảm nhận. Ví dụ hai cặp màu có cùng khoảng cách Euclidean trong RGB chưa chắc trông khác nhau ở mức tương đương.

→ CIELAB được thiết kế để khoảng cách giữa màu gần hơn với khác biệt cảm nhận của con người.  
CIELAB  
Một màu Lab có ba thành phần:

* L∗: độ sáng, từ tối đến sáng.  
* a∗: trục xanh lá ↔ đỏ.  
* b∗: trục xanh dương ↔ vàng.

Lấy pixel bên trong mask. Không nên lấy toàn bộ mask ngay lập tức. Biên mask thường chứa pixel pha trộn giữa áo và nền. Do đó nên erosion mask trước.   
Sau đó loại bỏ:

* Pixel quá tối.  
* Pixel bị cháy sáng.  
* Pixel phản xạ mạnh.  
* Pixel có độ tin cậy mask thấp.

Với áo trơn, có thể lấy median Lab của toàn bộ pixel hợp lệ  
Ưu điểm

* Đơn giản.  
* Nhanh.  
* Ổn định.  
* Phù hợp áo một màu.  
* Ít nhạy với bóng nhỏ hoặc phản xạ.

Nhược điểm

* Không mô tả được áo có nhiều màu hoặc họa tiết.

K-means  
K-means chia pixel thành K nhóm màu  
Chọn K cho MVP:

* Áo trơn: dùng median hoặc K=1.  
* Áo đơn giản: K=2.  
* Áo nhiều họa tiết: K=3.

Không nên dùng K quá lớn vì:

* Dễ tách bóng thành một “màu mới”.  
* Chậm hơn.  
* Nhãn màu trở nên rối.  
* Các vùng rất nhỏ không có giá trị với người dùng (Một quy tắc hữu ích là bỏ cluster chiếm dưới 5–10% diện tích, trừ khi nó tạo thành một vùng quan trọng)

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
Color naming: Van de Weijer 11 màu  
Color naming là bước ánh xạ một giá trị màu liên tục sang từ ngữ

Phương pháp của Van de Weijer ánh xạ màu sRGB vào 11 tên màu cơ bản:  
Black, Blue, Brown.  
Grey, Green, Orange.  
Pink, Purple, Red.  
White, Yellow.

Sau đó bạn dịch sang tiếng Việt:  
Đen, Xanh dương, Nâu.  
Xám, Xanh lá, Cam.  
Hồng, Tím, Đỏ.  
Trắng, Vàng.

Có thể tính color confidence theo:

* Xác suất từ color-name mapping.  
* Khoảng cách đến prototype màu.  
* Khoảng cách giữa lựa chọn tốt nhất và thứ hai.


\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
CVD simulation: Machado, Brettel, LMS và DaltonLens  
Không nên để hệ thống tự “chẩn đoán” loại CVD của người dùng. Profile nên do người dùng lựa chọn dựa trên thông tin họ đã biết hoặc qua một bước calibration mang tính hỗ trợ, không phải chẩn đoán y khoa.

LMS là không gian biểu diễn phản ứng tương đối của ba loại tế bào nón:

* L: Long-wavelength cone.  
* M: Medium-wavelength cone.  
* S: Short-wavelength cone.

Quy trình mô phỏng thường là:  
![][image4]  
Việc “bỏ gamma” rất quan trọng vì các phép biến đổi vật lý/matrix nên được thực hiện trên linear RGB, không trực tiếp trên giá trị sRGB đã mã hóa gamma.

Machado  
Mô hình Machado sử dụng các phép biến đổi được xác định theo loại CVD và mức độ severity  
Severity thường nằm trong khoảng 0–1:

* 0: thị giác màu thông thường.  
* 1: mô phỏng mức thiếu hụt mạnh.  
* Giá trị giữa: mức trung gian.

Ưu điểm của Machado:

* Có mức severity.  
* Tương đối dễ sử dụng.  
* Phù hợp cho UI có thanh điều chỉnh.

DaltonLens  
Là thư viện mã nguồn mở cung cấp:

* Chuyển đổi sRGB ↔ linear RGB ↔ LMS.  
* Mô phỏng Machado.  
* Mô phỏng Brettel.  
* Mô phỏng Viénot.  
* Các profile protan, deutan, tritan.  
* Một số hàm daltonization.

Đây là hai bước khác nhau:

* Simulation: “Người bị deutan có thể nhìn cảnh này như thế nào?”  
* Recolor/daltonization: “Nên đổi màu thế nào để người deutan phân biệt tốt hơn?”

→ Ảnh simulation chủ yếu dùng nội bộ để tính rủi ro. Không nên hiển thị nó làm kết quả hỗ trợ, vì nó chỉ làm màu khó phân biệt hơn giống trải nghiệm CVD.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
Risk detection bằng ΔE00

Người có CVD thường không hoàn toàn không thấy một pixel. Vấn đề là hai màu khác nhau có thể trở nên quá giống nhau. Ví dụ:

* Áo đỏ so với quần xanh lá.  
* Họa tiết đỏ trên nền nâu.  
* Tag màu tím trên nền xanh.  
* Vùng áo và background có màu bị nhập lại.

→ Rủi ro phải được đánh giá theo cặp màu hoặc cặp vùng, không chỉ từng pixel độc lập.

Delta E đo khoảng cách giữa hai màu trong không gian màu cảm nhận.

ΔE=khoảng cách cảm nhận giữa màu c1​ và c2​

ΔE00 hay CIEDE2000 là công thức cải tiến, điều chỉnh khác biệt về:

* Lightness.  
* Chroma.  
* Hue.

Trực giác:

* ΔE00 nhỏ: hai màu giống nhau.  
* ΔE00 lớn: hai màu khác nhau hơn.

Không nên xem các ngưỡng ΔE là chân lý tuyệt đối vì chúng còn phụ thuộc màn hình, ánh sáng và người quan sát.

![][image5]

→ ChromaLens nên so sánh:

* Các cluster màu bên trong cùng một chiếc áo.  
* Màu áo và màu quần.  
* Màu quần áo và vùng nền sát biên.  
* Màu chữ/tag và nền giao diện.  
* Các món đồ nằm gần nhau.

Đối với MVP, có thể giới hạn:

* Các màu chủ đạo của áo.  
* Áo so với quần.  
* Quần áo so với một vành background quanh contour.

Điều này có tính thuyết phục hơn việc tự động đổi tất cả màu đỏ thành tím.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

Recolor: LUT và LMS daltonization

LMS daltonization  
Một cách tiếp cận phổ biến:

* Mô phỏng ảnh dưới CVD.  
* Tính phần thông tin màu bị mất: error=original−simulated  
* Chuyển phần thông tin bị mất sang các kênh mà người dùng có khả năng phân biệt tốt hơn.  
* Cộng phần hiệu chỉnh vào ảnh gốc.  
* Giới hạn RGB về miền hiển thị hợp lệ.

Quy trình khái niệm:  
Màu gốc  
   ↓ CVD simulation  
Màu người dùng có thể cảm nhận  
   ↓  
Sai khác/thông tin bị mất  
   ↓ redistribution  
Màu hỗ trợ

LMS daltonization dễ làm phiên bản nghiên cứu ban đầu hơn một hệ thống tối ưu hóa LUT hoàn chỉnh.

Recolor có chọn lọc:

* Mask áo bao toàn bộ chiếc áo.  
* K-means phát hiện cluster đỏ.  
* Risk detector xác định chỉ cluster đỏ gây vấn đề.

![][image6]  
→ Chỉ recolor khung hình hiển thị. Màu dùng cho nhận dạng và phối đồ phải tiếp tục là màu gốc đã được hiệu chỉnh ánh sáng.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

Outline: contour và morphological gradient

Contour: OpenCV có thể lấy contour từ binary mask

Morphological operation: Morphology là các phép toán trên hình dạng mask.

Erosion  
Làm mask nhỏ lại. Hữu ích để loại pixel không chắc chắn ở biên.

Dilation  
Làm mask lớn ra. Hữu ích để mở rộng vùng.

Morphological gradient  
Hiệu giữa mask đã dilation và mask đã erosion: Gradient=Dilation(M)−Erosion(M)  
→ Kết quả là một vành bao quanh đối tượng.

Thiết kế outline cho người CVD:

* Viền đôi trắng–đen. (nên làm viền đôi trắng đen)   
* Viền có độ tương phản cao.  
* Nét liền/nét đứt để biểu thị loại rủi ro.  
* Pattern hoặc ký hiệu nếu cần.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
Confidence:

1. Mask confidence: Độ chắc chắn rằng pixel thuộc quần áo. Có thể tính trung bình confidence map trên vùng mask: Cmask=mean(P(garment)∣M)

2. Color confidence. Để phản ánh:  
* Color-name probability.  
* Margin giữa màu tốt nhất và thứ hai.  
* Mức phân tán pixel trong cluster.  
* Tỷ lệ cluster trong trang phục.

→ Cluster càng đồng nhất thì confidence càng cao

3. Lighting quality. Có thể đánh giá bằng:  
* Tỷ lệ pixel quá tối.  
* Tỷ lệ pixel cháy sáng.  
* White-balance gains có quá cực đoan không.  
* Gains có dao động mạnh qua video không.  
* Mức noise.  
* Độ bão hòa bất thường.

UI có thể hiển thị:  
Ánh sáng: Tốt  
Ánh sáng: Trung bình  
Ánh sáng: Kém – hãy di chuyển tới nơi sáng hơn

4. Temporal stability. Nếu màu được dự đoán giống nhau qua nhiều frame thì độ ổn định cao.  
* Ví dụ trong 10 frame: Đỏ, đỏ, đỏ, đỏ, cam, đỏ, đỏ, đỏ, đỏ, đỏ →Khá ổn định.  
* Ngược lại: Đỏ, cam, nâu, đỏ, tím, cam… → Hệ thống đang không ổn định.

Hai khái niệm khác nhau:

* Confidence: hệ thống chắc đến đâu về dự đoán.  
* Risk: màu có khả năng gây nhầm lẫn CVD đến đâu.

Một kết quả có thể là:

* Tên màu: đỏ  
* Color confidence: 91%  
* CVD risk: cao, 0,84  
* Ánh sáng: tốt

Hoặc:

* Tên màu: đỏ/cam  
* Color confidence: 51%  
* CVD risk: cao, 0,81  
* Ánh sáng: kém

Không nên nhân trực tiếp tất cả confidence. Ví dụ: c=c(mask)×c(color)×c(light)  
Công thức này có thể dùng như heuristic nội bộ, nhưng kết quả không phải xác suất đã được hiệu chuẩn.

**Cho MVP, nên hiển thị riêng:**

* Tên màu \+ confidence.  
* CVD risk: thấp/vừa/cao.  
* Chất lượng ánh sáng.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
Matching: CIELCH và suggestions.csv  
Matching phải dùng màu gốc đã được color constancy hiệu chỉnh.

CIELCH  
CIELCH là cách biểu diễn hình trụ của CIELAB.  
![][image7]  
Trong đó:

* L∗: độ sáng.  
* C∗: chroma, mức độ rực/rõ màu.  
* h∘: góc hue, loại màu.

→ CIELCH thuận tiện cho các quy tắc phối màu vì hue được biểu diễn bằng một góc.

Ví dụ khái niệm:

* Hue gần nhau: analogous.  
* Hue đối diện: complementary.  
* Chroma thấp: neutral/muted.  
* Lightness tương tự: tone-on-tone.

Rule-based matching. Gợi ý phối đồ không nhất thiết cần model AI. Một rule engine có thể xét:

* Áo đỏ \+ quần đen     → tương phản an toàn  
* Áo xanh \+ quần trắng → phối trung tính  
* Áo nhiều màu          → quần lấy màu trung tính

Thông tin đầu vào:

* Loại trang phục.  
* Màu gốc.  
* Tỷ lệ từng màu.  
* Lightness.  
* Chroma.  
* Hue.  
* Có họa tiết hay không.  
* Profile CVD của người dùng.

Kết quả nên kèm lý do:

* Gợi ý: quần đen hoặc xám đậm.  
* Lý do: màu trung tính giúp áo đỏ nổi bật và giảm nguy cơ nhầm màu.

suggestions.csv  
Đây là bảng dữ liệu do coding Agent xây dựng hoặc mở rộng.  
Ví dụ:

* upper\_color,bottom\_color,harmony,score,reason\_vi  
* red,black,neutral,0.92,Quần đen tạo tương phản rõ với áo đỏ  
* blue,white,neutral,0.90,Trắng là màu trung tính và dễ phối với xanh  
* purple,gray,neutral,0.84,Xám giảm cạnh tranh với sắc tím

Ở giai đoạn sau có thể bổ sung:

* Dịp sử dụng.  
* Phong cách.  
* Mùa.  
* Mức formal.  
* Profile CVD.  
* CVD contrast score.  
* Nguồn của quy tắc.

Một nghiên cứu thời trang gần đây sử dụng mask trang phục và đặc trưng CIELCH để đánh giá color harmony, cho thấy hướng rule-based hoặc học từ đặc trưng CIELCH là phù hợp để tham khảo [Establishing colour harmony evaluation and recommendation model for clothing colour matching based on machine learning and deep learning | Fashion and Textiles | Springer Nature Link](https://link.springer.com/article/10.1186/s40691-025-00433-y)

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
ONNX và OpenVINO

Khi tải SCHP, bạn có thể nhận file như model.pth. File này thường chứa trọng số PyTorch. Muốn chạy model, cần:

* Kiến trúc model trong Python.  
* PyTorch.  
* Code preprocessing.  
* Code postprocessing.

ONNX \- Open Neural Network Exchange \- là định dạng trung gian để biểu diễn graph của model.  
Quy trình:  
PyTorch model  
    ↓ export  
model.onnx  
→ ONNX giúp model ít phụ thuộc hơn vào framework ban đầu và có thể chạy bằng nhiều runtime khác nhau.

OpenVINO là runtime chạy model. Nó là bộ công cụ/runtime của Intel để tối ưu và chạy inference trên phần cứng Intel, bao gồm:

* CPU.  
* GPU tích hợp/rời tương thích.  
* NPU trên các nền tảng hỗ trợ.

Quy trình triển khai:  
SCHP trong PyTorch  
    ↓ export  
ONNX  
    ↓ OpenVINO compile/optimize  
Inference trên Intel CPU/GPU/NPU  
    ↓  
Mask quần áo

FP32, FP16 và INT8. Đây là độ chính xác số học dùng trong inference.

* FP32: số thực 32-bit, chính xác hơn nhưng thường chậm và nặng hơn.  
* FP16: số thực 16-bit, nhẹ và thường nhanh hơn.  
* INT8: số nguyên 8-bit, rất nhẹ nhưng cần quantization và kiểm tra suy giảm chất lượng.

Đối với MVP:

* Chạy FP32 trước.  
* Nếu model chậm, thử FP16.  
* Chỉ thử INT8 khi có thời gian benchmark mask accuracy.

Các phần có thể chuyển sang ONNX/OpenVINO:

* SCHP.  
* Detector.  
* Một số model segmentation/tracking.

Các phần thông thường không cần ONNX:

* Gray-world.  
* CIELAB.  
* K-means.  
* Robust median.  
* ΔE00.  
* Contour.  
* CSV matching.  
* LUT đơn giản.  
* Vẽ tag.

Những phần này vẫn chạy bằng OpenCV, NumPy hoặc thư viện khoa học màu.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
Mô phỏng luồng chạy (minh họa)

Giả sử người dùng chọn:

* Profile: deutan  
* Severity: 0,8

Bước 1: Camera  
OpenCV đọc frame kích thước 1280 × 720\.

Bước 2: Segmentation  
Frame được resize và đưa vào SCHP.  
Output:

* upper-clothes mask  
* pants mask

→ Mỗi mask được resize trở lại 1280 × 720\.

Bước 3: Tracking  
Hệ thống xác định:

* track\_id 7 → upper-clothes  
* track\_id 8 → pants

Mask được làm mịn với frame trước để giảm rung.

Bước 4: Color constancy  
Gray-world ước tính hệ số cân bằng trắng. Hệ số được làm mịn theo thời gian.  
Output là white\_balanced\_frame.

Bước 5: Color extraction  
Hệ thống erosion mask áo, lấy pixel Lab và chạy K-means với K=2.  
Kết quả giả định:

* Cluster A: đỏ, 72%  
* Cluster B: trắng, 28%

Quần có màu xanh lá chiếm 85%.

Bước 6: Color naming  
Color mapping trả về:

* Cluster A:  
  *   red \= 0,87  
  *   orange \= 0,09  
  *   brown \= 0,04

→ Tag tạm thời: Áo: đỏ – 87%

Bước 7: CVD simulation  
Machado mô phỏng cluster đỏ và xanh lá theo deutan severity=0.8.

Bước 8: Risk detection  
Ví dụ:  
ΔE00 gốc \= 35  
ΔE00 dưới mô phỏng deutan \= 4  
→ Risk được đánh giá cao.

Bước 9: Recolor  
Hệ thống thử các màu ứng viên hoặc sử dụng LUT/daltonization để tìm màu hiển thị dễ phân biệt hơn.  
Chỉ submask đỏ của áo được recolor. Phần màu trắng vẫn giữ nguyên.

Bước 10: Outline và tag  
Giao diện vẽ:

* Viền đôi trắng–đen quanh áo.  
* Viền quanh vùng màu đang được hỗ trợ.  
* Tag màu gốc.  
* Confidence.  
* Mức risk.

Ví dụ:  
ÁO  
Màu gốc: đỏ – 87%  
Hỗ trợ CVD: đang bật  
Rủi ro với quần xanh: cao

Bước 11: Matching  
Matching engine dùng màu đỏ gốc, không dùng màu hỗ trợ, để gợi ý:  
Gợi ý: phối với quần đen hoặc xám đậm.

Bước 12: Hiển thị  
Frame cuối được hiển thị bằng OpenCV hoặc gửi về browser bằng WebRTC.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
Cấu trúc dữ liệu chung giữa các module  
Để các thành phần không phụ thuộc chặt vào nhau, nên chuẩn hóa dữ liệu.

Ví dụ khái niệm:  
FramePacket:

*     frame\_id  
*     timestamp  
*     original\_bgr  
*     corrected\_rgb  
*     cvd\_profile  
*     severity  
*     garments

Garment:

*     track\_id  
*     class\_name  
*     mask  
*     mask\_confidence  
*     color\_clusters  
*     lighting\_quality

ColorCluster:

*     lab  
*     rgb  
*     ratio  
*     submask  
*     original\_name  
*     color\_confidence  
*     risk\_score  
*     display\_rgb


Lợi ích:

* Có thể đổi MediaPipe thành SCHP mà không sửa color extraction.  
* Có thể đổi Machado thành Brettel mà không sửa segmentation.  
* Có thể đổi OpenCV camera thành WebRTC mà không sửa risk detector.  
* Dễ lưu kết quả từng bước để debug.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
Tránh latency tích lũy  
Không nên để một vòng lặp duy nhất lưu mọi frame nếu model chạy chậm hơn camera.

Nên dùng ba luồng logic:  
Capture thread  
    ↓ chỉ giữ frame mới nhất  
Inference thread  
    ↓ mask, màu, risk  
Render thread  
    ↓ video đầu ra

Điểm quan trọng là hàng đợi chỉ giữ một hoặc rất ít frame:  
latest\_frame\_queue(maxsize=1)

Nếu camera đưa 30 frame/giây nhưng model chỉ xử lý 10 frame/giây:

* Bỏ frame cũ.  
* Xử lý frame mới nhất.  
* Không để video chậm dần 1–2 giây so với thực tế.

Trong các frame chưa có kết quả segmentation mới, có thể tái sử dụng:

* Track hiện tại.  
* Mask đã warp bằng optical flow.  
* Màu đã làm mịn.  
* LUT hiện tại.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
Stack MVP đề xuất

| Module | MVP nên dùng | Lý do |
| ----- | ----- | ----- |
| Ngôn ngữ | Python 3.10/3.11 | Dễ tích hợp OpenCV, PyTorch và thư viện màu |
| Camera | OpenCV VideoCapture | Ít thành phần nhất, dễ demo |
|  |  |  |
| Segmentation | SCHP-ATR | Phân biệt áo, quần, váy |
| Tracking ban đầu | Làm mịn mask và màu | Chưa cần ByteTrack |
| Tracking nâng cấp | Optical flow | Truyền mask giữa các frame |
| Color constancy | GrayworldWB \+ EMA | Đơn giản và giải thích được |
| Color extraction | Lab median; K-means (K=2) nếu cần | Ổn định, dễ triển khai |
| Color naming | Van de Weijer 11 màu | Phù hợp mục tiêu tên màu cơ bản |
| CVD simulation | Machado qua DaltonLens | Có profile và severity |
| Risk | ΔE00 rule-based | Minh bạch và không cần training |
| Recolor | LMS daltonization/selective transform | Dễ làm bản đầu |
| Outline | OpenCV contour \+ viền đôi | Dễ nhìn, không dựa riêng vào màu |
| Matching | CIELCH \+ CSV rule-based | Không cần model nặng |
| UI MVP | Cửa sổ OpenCV | Tránh phát triển web quá sớm |
| Optimization | ONNX/OpenVINO sau cùng | Chỉ tối ưu khi pipeline đã đúng |

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
Cấu trúc Source Code

chromalens/  
├── app.py  
├── config.py  
├── camera.py  
├── segmentation.py  
├── tracking.py  
├── white\_balance.py  
├── color\_extraction.py  
├── color\_naming.py  
├── cvd\_simulation.py  
├── risk\_detection.py  
├── recolor.py  
├── matching.py  
├── renderer.py  
├── models/  
│   └── model.onnx  
├── assets/  
│   ├── color\_names.npy  
│   └── suggestions.csv  
└── tests/  
    ├── test\_colors.py  
    ├── test\_risk.py  
    └── sample\_images/

Ý nghĩa:

* camera.py: chỉ chịu trách nhiệm đọc frame.  
* segmentation.py: frame → mask.  
* white\_balance.py: frame → ảnh đã hiệu chỉnh.  
* color\_extraction.py: ảnh \+ mask → cluster màu.  
* cvd\_simulation.py: màu \+ profile → màu mô phỏng.  
* risk\_detection.py: các màu → risk score.  
* recolor.py: frame \+ risk mask → frame hỗ trợ.  
* renderer.py: vẽ outline, text và confidence.  
* matching.py: màu gốc → gợi ý phối đồ.

Những điểm cần kiểm chứng khi demo.  
Trong lúc phát triển, giao diện debug nên hiển thị đồng thời:

* Ảnh camera gốc.  
* Ảnh sau white balance.  
* Mask quần áo.  
* Các cluster màu.  
* Ảnh mô phỏng CVD.  
* Risk mask.  
* Ảnh sau recolor.  
* Kết quả cuối cùng.

Nếu chỉ nhìn ảnh cuối, khi kết quả sai bạn sẽ không biết lỗi nằm ở:

* Segmenter.  
* White balance.  
* K-means.  
* Color naming.  
* CVD simulation.  
* Risk detector.  
* Recolor.  
* Renderer.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
Sản phẩm nên được mô tả:  
ChromaLens AI là một hệ thống hỗ trợ thị giác màu theo thời gian thực, sử dụng human parsing để định vị trang phục, color constancy để giảm ảnh hưởng của nguồn sáng, mô hình mô phỏng CVD được cá nhân hóa để phát hiện các quan hệ màu có nguy cơ nhầm lẫn, sau đó chỉ recolor những vùng cần thiết và bổ sung tín hiệu phi màu như outline, tên màu và độ tin cậy.

Điểm nghiên cứu chính nằm ở sự kết hợp giữa:

* Segmentation theo pixel.  
* Màu gốc đã hiệu chỉnh ánh sáng.  
* Profile CVD cá nhân.  
* Đánh giá rủi ro theo quan hệ màu bằng ΔE00.  
* Recolor có chọn lọc và ổn định theo thời gian.  
* Tín hiệu hỗ trợ không chỉ dựa vào màu.  
* Gợi ý phối đồ dựa trên màu gốc.

Đó cũng là lý do pipeline module hóa phù hợp hơn việc cố huấn luyện một model end-to-end từ camera đến ảnh recolor.

[image1]: <data:image/png;base64,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J2lsFJQ66pRul4bj8kEp3eSolNZjDoMy3ywoQVlPBGUNuL/sRUsOSbfsH7LR61J2bVSmZx7atZBLXLdIBCWAcVUpKCehM7UnP6ydzGyuNGFAUNYTQVkD7i974frPYNNnxulayK59QfPk8qXWU4ZAUAIYV12Cci0RlPVEUNaA+8seK4ISwLgIyuIRlPVEUNaA+8seK4ISwLgIyuIRlPVEUNaA+8seK4ISwLjKFJSPHz+OAkFZTwRlDbjhFSuCEsC4yhKUeW3evNkbG8evv/7qjQFFIChrwA2vWBGUAMZVlaDctGmTN7YaP/30kzcGFIGgrIELFy6smc8//3z4vg57uJeHRFACGFfZg/Lrr782d+7c8cZXixlKhEJQAgBqq4xBee3aNbNz505vvAhPnz71xoAiEJQo1MGDB70xACirMgWlTszRUR53vEjMUCIUghKFe/36tfnggw/M8+fPzS+//OJdDgBlMa2g1N/H7du3r/kZ0QQlQiEoEdSOHTvMoUOHvHEAKIO1DMovv/zSnlzz1VdfeZetFYISoRCUCEoLyrMf68SZEydOmE6nY9cJudsDwFoKEZS9Xs/s3bvXHr6+d++ed/k0EZQIhaBEUBcvXvTGsn788Uf7rH3Dhg3m8OHD5tGjR942ABDKpCe/KNCOHz9uNm7caM6dO1f6v2EEJUIhKBHUZ5995o2N4+7du+bs2bP2xXz37NljDxWxLhNAUfLMUF69etV88skn9siKorHKUVblrx3lRlAiqFDrJ3XoXLOfWqOphe06tKT4dLcDgLfJBuXPP/9svvjiCzvb+PHHH5tbt26Zly9fetepMoISoRCUCErB546tpZs3b9q1mvv377cPEgpchej9+/e9bQHES4eiL126ZD788EP7JFT/DOHBgwe5ZihjQlAiFIISQSni3LGy0MzD9evXzenTp2346qWO9BIemqHgsDpQTTdu3DAnT560f3u63a49XK212u52KYISKAZBiaDKHJTjevbsmX1wUnRu3brV7N69277/zTff8P9xgcC0pEVHGnQSjWYYz58/X8gyF4ISKAZBiaD0mmvuWKyePHliZ0eOHj1qY3Pbtm32zHUdcv/++++97QGM6IiBAlFnTOvkF9H73377bdB1jAQlUAyCEkHp7Gx3DCOPHz82V65csRGqWc8tW7bY9zX2tsN0GNGssWarqkazbe6+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>

[image2]: <data:image/png;base64,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>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnAAAAFwCAYAAAA4+0Y+AAAw9klEQVR4Xu3dv2skR/7/8c8/MIEDZRsqMHjhAg8KBA4sUGJxwXfBgRcOPKDACAfHOjg2OoThg7lADA5u+QRm+QRfUHCwDgTtyE4O9oLDn0DoEwjmwIGCCxQYFDgQ1Kerq6u76l3v7vmhaa1q9Awe7E51df3o0bpfruoZ/cft7a0BAABAPv5DFgAAAOBhI8ABAABkhgAHAACQGQIcAABAZghwAAAAmSHAAQAAZIYABwAAkBkCHAAAQGYIcAAAAJnZ/AB3OTXj0ciMDov0GAAAQIY2P8BVCjMZTUyRlAMAAORnmAB3NjEju+pVm5wpdeqVMfVYj9nJ2Ix2pmamHEvqVe3PzHRnwRW4akwy6C1xPhbi3puxmV6mx2I2eC//MzKExccMAMDw1h7gikMb2iZtWRmKJiczUW/BFTEbBEVYWyjA2fOqwLVgP54a4Bzb7ziZB+ZzAXi1EPZwAhwAAA/JWgPcQuHKupzNr2OtGOBml2HQKkyxaADoCXBVu2dFb7/QEOAAAFi3NQa4BW+2/kMFXkcYcyt5gXoLswlw4TZt1Ea95akeU5TjcXXHZnoWBzg1LEahclatyoVjTVbpovm2fSTjCNsP5t1cT7HlXPVZjcPNV45D2/IN243H6d+7+NpF72XXuDr69+1H77XfgqzaCoOyeM+aY3N+pnw74djKeXfOIWgz7cu1F4f3oP9ozOmcF33fu/7nIP55D7Zqk2vVjqs9rs/X//wW9eMEfoxtX+mWsPwZsq/DucXjjK+d1h4AYBjrC3BzVq8qyn/k2yDSUV9bgatvLq7M3czcTaa9sUbtK2GmUt9k3WsfIpYLcNFNU84vec6v7SMZS3N+cA2r89v2/Hjia92Gn6SfYN72OrTzCK9Z+zocu7vO7Vi6x6X0H10HZQVOmWe4zd6+Z4sEuGCe4nrLOcjjaZ0iHad/r5UAF8550fdd//dR9hu8V/HPnXIN6nFp1zH5eYne57gv+fOd/Fusr294fvgzFZ0v+gYADGt9AU4JW7E0XDn2BtXxH36lzeSm7Mv8DU2OoSdYJuFO1JU3uHRMMxEO47CStB/0Icciz/XiFRBXRytL+glv7vXNNTkuQkJyow9CWPe4tP7DuSjzksFD8gFFCy+ynmjHjqutE/9sqe+HGJ8Mvc010QJcUHfR971zzj11ZXt+XMl1DY7Zv2v/Vjr76Qhg0TUo68Rt9fzbBQAMar0Bru9m0Xkz1m9ETZtagOsq86tzCe0mowTKFQJcHHrCNpX2gz7isVh+FUwRhoHkmvT3U82lfm86j6vvTVhWpGNqxqX1n16HuQGuKgvaXnuA08bZnuPLo9W48OdGCXBhW3K+ST/zAlx1PLy+Qd2o73Zc835e1J/fuq+kH+VaWmmITfvrfH8AAINZX4Dr+D/4Vtf/rSs3eC8JK/pNKQpw2g1LpfQ7QIBL5jUnwCX1JXvzXSXAVYGo47jadxzgusel9T/nOoiwUK0wycAyUIDT2gpDSlNf/uwtGeCSfnoCnPsfD7kFG9YN5hGMq/fa+Ha1fyt+NVb5GZH/dmSA08YPALh/6wtwt+lWTyy96Tldwe5Wval03pTsDV+5ofdJxivPn9t/X4BT2g/6kGOR5+pcnTggdJwXjr0O153H1aAUlsl5hrT+lwlwyvs/SIDreD/E+HxgsX92jzmd86Lvu/azmVyfJMDp45JjkNJ/K+K9CPtR/wdMzLOso/47BQDcu7UGOH/DjVZ7LoMH1KubWHyTUG92nnLTS29KQYCrbzhxe0X0gHjavg829djD/qqbmrzhufktEuDS+bZ9JGNR69u5TZrXelCt56z0E4YCe53bayaPy9dpWfe40jCjBbjouDL+9nj4M6SNK6D8fPQFuOT9vFV+nmydnXESoPrHLMJU8j4qP1uB+N+Afz9FXW1cST/6z0v4b6XtS/aT/ttxq3XxPJNAeBj/TwIBDwDux5oDHOZqVpeUYytJwwQeoPp9l1uUD5tYsQMAPBgEuHvlVmLWG7YIcA/fEO/78NwKnL5qCAB4twhwQ6q2uOw2VWv9qxkEuAfnXt73dfNbqoHsVgwB4PEgwAEAAGSGAAcAAJAZAhwAAEBmCHAAAACZIcABAABkhgAHAACQGQIcAABAZghwAAAAmSHAAQAAZIYABwAAkBkCHAAAQGYIcAAAAJkhwAEAAGSGAAcAAJAZAhwAAEBmCHAAAACZIcABAABkhgAHAACQGQIcAABAZghwAJCda/P2+7fmOil/iGamOM1lrEA+CHAAkJVrU3yxa47OrpVjD9P12ZHZ/aIgxAFrRIADgIxcnz4z21+9Tcpvf70wb754ava+naXHHoC3X22bZ6f5hE7goSPAAcA7cPPPH83Pv6blvX4tzGRrz7z6JS7f3t42T3efmq3RyIxPHmaAu/3lldnbmphi2TkDUBHgAOAdmJ1MzPQyLe9z9dc9M/r01Nwox24vp2b8kAPc7Y05/XRk9v56pRwDsCwCHAC8A8sHuCvz+pOROfiuIwA9+ABXBtDvDszok9dJOYDlEeAALOzNl3tm/OFTs/3hc/Pqhzfm+OvCXCn17sVv1+btXyfm4MOx2X7/qXm6PzGn/6vUs25mD2vstysEuN/emMlo2xz/UzlmvYMAd3P5xrz8f7tm/MG2efrBrjn4+sf+Dyr889hsjyZJuW3naH9ctTP+7JUp/nZsjs86giqACgEOwGKuC7N7cuH+/tuP5sXWyIw+/MZcyHodbv4+NUdfHi1s+vebpI12LG/N8Ucjs/vn9usp7MP9I/+MVRlmnv3557puYY62R3ca+xCWDnBVQDswr6+UY83x+wtwV6fPzZMnz82pfx7vt5/N8Qdt/8VheUw+7/avqdkdjaMy+wnV7fd2zdSH759euGf5/lK/XwBUBDgA850fm6flTbV5ffXaHJSvn536kHVjTj8bmcmZcu661WNJn6UqzMTe+P9cBsXPXrvVtbpuFGqSsQ/sl1NztL9n9oTd95+Y7Y9E+Ren3auCZxMzGpUBVZZ7ywS4jjElOsdzU4blF+bH3+Ly2cm4GuP05MC8+Ls8x3LvkX998fXTsv44CrLVNuvoWRD+LspgGNeZ5+1f9szBp8/NwfY9/UwC7wABDsBc7qa61ZZ9b8PErpn+y9cpzFHf6pD12425vroyVwu6vlHauPUhYWy+SbZLXTiw4/LH/LijMJGM/d1YegVunQHuzgoz+vxNUu7em5F5cvimYys1DHDumT4bBN8Gdd58XpZ9NDUzX2ZX7USdxczMdIcAh81FgAMw1+zb3WpVxL9++9WWGW0fm5/Lv//83ZE5+sOu2XpvbJ5/+cKcnqfnW+vaQvWrPGmQqQNcECz8uMOtvGTsn+6al6dvzes/H5mDj5+Zl/WzV9f/eFXOy86tLPvelv1sXvvx/edr8/o//d8Lc/U/r+txL/6A/tIB7kFtoRZqP93huhZtoZYB66OR+FTt22p7e7va/r4yhb3Gv39avl975bX9Jm2vFwEOm40AB2C+aityr/r79T+Oy5tweeP9omiO25WuLe3LZYfw9xfmyUh8F5r9QMPXB+bJe+W4Dgu32nd904zb19XGXq34fHbqVoyqgHFUhcPdD8uQZ7cIq2e7fBvl37f9BwkuzDcf+rByY958OTFvrpXxdlg6wD2oDzFcma0//hiV3Vy+NpPfbTVbojfX1+ZGbLHKDzFUW6gfv6q3acv38M82cI/M0Q/tOTZwd37ythcBDpuNAAdgIRffPTe7n+yayVeTKihEz799Wt4ov0/PGYYNa3tm63fPzfT/vzLHXz43B58cmdfnN+bqvw/M6MmBOTo8MC9+cOOz4366vdsxdvuwfRh67CqeW90b7b80b/72pvJyvw0CNnRUK0S/nprJVn3ubz+a46+XC7BLB7h6xUoLM9vvb5tt+8GMagt5y73+Uxyw1u15GWT3/vTKnJ68NJNPD8yzrwtzffPWvLQfGPnDkTn47FW7DVpLvkbktwvz+rPyeu7umoOPJubF53YFL1wxtYG5XdHrX8V9aU6j60mAw2YjwAFYTvUsVriVZ7e9erb2hnJz7Z6VE590vLlOyxrJ2HsCnF3Jk+dbdlVv64UpTo/N9KdXZu+DY/PzT9+YadfKWIflA9ycL/J9B27+bZ9XvI7HUz3rKMoqLuhrAdSz74UNeM0HJ+wHTlZ6/s0iwGGzEeAA9Lv+0Rx/OjGv61WQH/+4ZUY7wUPmdlus/kqO2bfH6VdHvEPhuK1k7LfdAW6rDGbN14z88sa8aQKaDQZb5kn1Sdcr8+rjp2b3D9Olv5Lk5n9/NhfLXqtfT81zuX2ci+pXabWfXL3+6dg8O3xtLvw2a/31LuEW8I39apjqmcYbU3w9TdvsRYDDZiPAAejlPgjwpPok58V/PzdP3ttrv7PL+uW1OfhgYl59+9Ic//Cwflm5H7ddFdLG/vN3E7P3ZGS2dp+bb34ozOvP98yT8py9z8tgcXJgxp+VgfRvr8zLPwZB49Y9rO+/xsRuCz79+v6+s8z2p/4y+wcu/mX29QcYnrwwb+11/dVupT4xo4+n0XWunnfcf2lOv35pXnV9MEJx9cM35ujLZ9VXyDz5eFJ90ETWAXJHgAPQ72ZmipOX1XNGx//1o5lpX+9xc935tR/vkh9379j7+A9DKOXNA/r278u2eyfXpvhi1xydPayw3Md+We/uF0X01SI3l4WZ/sk/v3ZsXv00U7ZdS78qH4YAQIADgPxcm7fft7+F4mHLaaxAPghwAAAAmSHAAQAAZIYABwAAkBkCHAAAQGYIcAAAAJkhwAEAAGSGAAcAAJAZAhwAAEBmCHAAAACZIcABAABkhgAHAACQGQIcAABAZghwAAAAmSHAAQAAZIYABwAAkBkCHAAAQGYIcAAAAJkhwAEAAGSGAAcAAJAZAhwAAEBmCHAAAACZIcDdh38X5uVH22b8yTNz8OHYPD95m9aZ68Zc/TQ1B9tHyjEAAPCYrC3AFYcjMzoskvLbs4kZjSamaMpmZrrTUVdpc3wyS8qz8ttb8+LJlpl8f12XXZs3n2+l9Tr9aF6+v222t3fN+INRdS3TOgAA4DFZW4BLg5ojg519PTlTzldsQoC7+uteeV2O4uvyw5F5fZXWnae6lgQ4AAAevfUFuNvCTEYynMmymZldyvO65R/gbszpp2Xo2pmaWVh+OTWT72Xd+QhwAADAWmOAS1fb5Krc7GSchhlhNLIhxbUTBbgy9IxHYzONAqANiLJM+Pdb8+rwwIw/3DbbHzw1e4en5uI3pd4gLsw3H+oBbpVgqgW4qky2DwAANtpaA5wMbDLQzQtwtn5zrGrrbgHu+h/HZve9XXP8j/b5M7sitlWO6ebWjueZOf5nep5dKTz905E5+nIBfzrtnI9fgUzmXM5l9MX8ZwAlLcDNu6YAAGDzrDfARVumabjqDRt1QAvL7rQCd31qnpVjefr1RVR+c/qsDEEH5vXVhTn+/bG5kOf5etdX5uqq3/Wv6XmxngC3wIc4JC3AAQCAx2fNAS5YdbMraCK49Aa4evVOtrVqgLv4+mnZ3p559YvWz9gcnxyZ599dJeet11vzYksPcOO/xMFyEQQ4AABgrT3ANduoygcQ5ga48lhYtnqAq7+q5MNv0hW2emt29NE3vc/CLbICV/n3TXJuNI6P9AC3++16noEDAACPz/oDnN9GVYJVb4BLtlBdCGtDoBLW1FDXnqtuU9YBrv9ToOt6Bu7WvP1qy4y2Xpi3YfkPR9GzdzfX1+amJ0x6BDgAAGANEOC6g1pXueNCV1Q3/BBDEsrq12qAs8HpiRl9/MpcheX/fmuOf//EBTj7nN6v1+b6Jj13rc6PzVOxlWu3d5tr8Msrs1etCHZdl5YW4PqvKQAA2ESDBLiur8mYHzZmbnuzDm7JNmy14uaOu+CmrMp512VY+3jLPP3D1Jz+17E5+sOBOfjitbm4uTKvfz8yT35/ZCafvDDF3A8i3N3Ft3tm63dH5vU/L8zP/31kxu8/a49fnZpn79n52A9WpOc2v4nhfRc8re3y/Ff/csfnX1MAALBphglwD4h7lk1uUd6Y66RsWDfXF+bHv70xb366UPt9+9XEnN5DmAQAAPnb+ACXg4uTZ+boh74PQwAAALQIcO/ctbn4n6G/zgQAAGwSAhwAAEBmCHAAAACZIcABAABkhgAHAACQGQIcAABAZghwAAAAmSHAAQAAZIYABwAAkBkCHAAAQGYIcAAAAJkhwAEAAGSGAAcAAJCZDQlwMzPdGSXlxeHIjEa1namZBcdmJ+PmWFh+ezZJ6s5lzxlNTCHLHwg310lSfifVnMdmeqkcC0zK6zs5S8uHYt/z8L1zPwMP970BAGAV2Qe4MIgl5UEQq27kh4U7fjk14+CmPj6Z1ecVZeCYH0p8YGyCyUMJcHZefo6eHVtdVhwuMjdJCce2nwVD7n0GOPueu/fSjvkBvB8AAAwk7wDXBCcZMpQgVoW2uiwINZYPcG0AUPqKPNAAJ+ZlzS7b+Ux31hXgZguFN+teA1wzV/v+P4D3AwCAgeQd4BoiZIgVtrBOFSbECpJW1qlqu92abQKh7S86JvuPt3T7jll9oacJosmYwnIbYuI243Anjmtzj+bj23bn+fE1K53VNUjbcnXdtV9kbr69ol5ZdYE6HKsSQsV70p6XrsQCALAJBg9w5+fnZn9/v7qp2j/ta1nn7kSAU59ji1fN4q1XsaI2l7YCFwaXOrAEgSnawi311fWBpGs8eoALypTz7Xzb0OgCUbjaWJzI6+XJFTglwNm5N+OP23bBqx2bfx5PBljPt1ed34TC9vzqOobvrfIsXnicAAcA2ESDBzgf3jz7Wta5u8UDnLpFqmw99tMCnAhV4baqsiLYbPF2bL9WwaNjTPMCnAyLziwOXcnxLosEuHj8YfsyKMrzpThwKe9ZdC2V41WfIjAmPwsAAORt8AAXhrd2xSutdzeLBzgtODTPS4XbgEqo6mxLC2FhWdRuy57fGTDUOTj9AU4PNdV5zQP++nHdAgFOjDMsS8Pa8gEuqhsFOL2t8BxtfAAA5G7wAPdOVuCUFS81DNTa56zEyk3nKtUqAU6OZ04/dwxw3fPsPq576AEufSaOAAcA2HSDB7h38gycdmNXQ50rr27u9nh4o7evtWAV9LdwgJPPqHXVC3QGu9t4i7Cy5BaqfryLdm37A9L9BTh9NTEJ4gQ4AMCGGTzA3Q8ZMtKH3e1reaN3543rv6crcGn9uL/muBbCRJkcz/QwDinphxg6Ap89N6pfnx/Wr86Pg4+dTxROxfE7fYjhnQW42/o6x9cqvJZRe3OuKwAAudjYAGdFX82hrDglK1Hhs2rzVm3qulUYWCDAtUHLiQNMfEwGkkQdwJq6Z0owieq4+XS3oV+fRhSSHliAs8L3bRT/HBDgAACbaEMCHAAAwONBgAMAAMgMAQ4AACAzBDgAAIDMEOAAAAAyQ4ADAADIDAEOAAAgMwQ4AACAzBDgAAAAMkOAAwAAyAwBDgAAIDMEOAAAgMwQ4AAAADKTeYCbmenOyIxGjjxeHLbHRjtTMwuOzU7GzbGw/PZsktRdlut3YoqkbGQmZ+Xry2lyTm6q67fQdSrMpJz3+GQWnzsam+mlrDuff99ce+X7f7jIGAAA2CxZB7gqFB0W9etZ8Pc0YER1ywA1DgJWGy5s2FgtWPSy/VV9+8A5NlVfHQGoGnswl4dAXhd5fbtMd9Z5PdvA5gNxGAwBAHgs8g1wIoRZ7WsliFX16zK7yhYEJB8CbCi5t0Bgx9MRgDYpwM3WFt4AAICXb4BTtjqbkKGEO7/65bcww/Cklc1V9eFW06ZncX9xuHFbiFUfzflFu50atRtvCUdbhTv270X1ZzvHoG4U+HyfPVvM9vo155djV65nZ93bYI7hMXl+cCwKxlW5fH+Ecn7x3LTrGLyn8nwAADbY4AHu/Pzc7O/vVzdi+6d9LeusRAlpzQ1eDSPxzT58Bk4em6sOT66+D0nLBbi+vtIVuHbr1a+CzU4mwYqY7MO9juuP22tVBahwRa2un1yzlroC14Srto0wqBWHE/f3cPWz6b8nwNXX170u535CgAMAIDR4gPPhzbOvZZ3V1KEmCDq2/XkBTt0iFVuq88TP3t0mYXKwANczRjum+Fk+OdeiDlAd10G9Zi09wMUhrHtbVQStOQEunounXUcCHADgcco4wKUmPhQoq3N9N3sXFuLn5tIQ1dPOPQU4GdDCOlqA0/uM59lYJcCJ+lGZXEVbOMB1jE+dk/JeAADwCAwe4AbbQlXE23nahxiU0HAZBI4wkNjXaoBTVuBEIInDjRYy7hjglLC1eICTYTDoc40BLp7DMgFOH1/SRkWbJwAAm2/wAHdvzsJnwuqQFQQMfVvOhgL7lR727+kKXFq/7at9hqxeDesMcPpY+kKHPD8JNeozZYsGOGX7038gojfAxe2lYxRldUhr+1s0wPnj/n2Z1c/A6dcxbNf3n7QHAMCGyTrA+Ru4Uz8w33VcWU3TV9Lq+j1hJq5bBpHeLVTLhzwfOPpX4ML6LpSlq1I+FPm5Lb4Cp5xvx6qs6oXa+m6e6RzTMn/9/adnFw5wTZ3wGthyeR3jVTkCHADgscg6wD0Yc8JPDuItTwAA8JAR4O7MrQp1brcOyq1A3Tl4RV+LAgAAHjoC3CrCrdYMg0+0fVrRPvUJAAAeKgIcAABAZghwAAAAmSHAAQAAZIYABwAAkBkCHAAAQGYIcAAAAJkhwAEAAGSGAAcAAJAZAhwAAEBmCHAAAACZIcABAABkhgAHAACQGQIcAABAZghwAAAAmSHAZW9mpjsjMxpNTJEcy5Wb0+bMBwCA9XrnAa44LMPHztTMlGNDqfrcqMDj5jQ5S8tztmnzAQBgXdYa4GyIGJ/Mmtezk3EZlMZmehnWK8xkVAaow8Lcnk3cn0pbQ7NjWy4guHEvd86a2OskQ+7l1Izr6+iucx1I6/LwfZjPzW25c6Q1tCHmtLaAHV2/4OdP1lNU11Ze+07v8GcEAPCoDBfg7E0zCW92a8yVVTfG6Cbqts1km4NQxxZLx3f/N2e3UhiIQogLbHaci4cmd4275pCs4tlAlQSd5dpIz++y6py6dV+/xd1PgLPXdLNWhAEAwxoswI21gHRZmEKWNe4xwC3gIQS4hlyBu5xFgWJ2uWjY6Q9fSVvqCulybaTnd1h5TguQ128J9xPg2vCaHgMAIDVQgCv0m5jfIqs1qyxRuRL81PPLemf2dXvjS2608sYt+tfDhf9QgBynvznHx7vPa8dVrQSJvsJxJ6oVwqAdMQ+3ZSrH58/vDhHR3P11rq6JuObNdeoqX7yNzvdS6J6Tft21+TV6r59rp6/9sO0mwIVtyp+zRtqWbK+SXMd2PMv1BwB4rAYIcIW+kpbc5GXQmLMCV9/0ZP0wKCU3uiT4THr6j3WtwIWhJnpOqxzfJAhSUWirbsZxYJOBrpFs79b9BvOI5+mOp4FEaVtbPUvel46yFdtIz0+lH2Rxcwj/Lq+7vJ6h/uunBzh/jmy7CZbN+yWvd2iBsSbvb/x+LtcfAOCxWnuA86se2jF5E4pDUn+A01axXEhYPMBJ2pi8rgCXrHapQelWfXA+DJ/6eTJcKG2Vc06CVW9fafuLhq+knxXaSM8XtHOtck7hfJLrrp1TmfVfv+Qay/bjtpMA5svUnyvZVlvmrpfs21moP/mzDwB41NYe4NzNaaZ+QEHeuGJ9AU4JDdZSAa5eHQnGtUqAi8fQBjgXXsVKSzgeO9b6ta0r+2v7UIJJ2FYTbALRddDG6SnXUQtQWtmKbaTnC/I6Bed3z0cra48l414gwLVtxa+1sKaVaeemZfr7G15PrW2tDADwuA0U4OyqQhyO1BW0SF+A6zhfbE3Km1x041OCwvoCnHJjTvqz87N1XF3ZX1snHVM0j3WvwGlj1wLZim2k5wtdfYkVuLQ/WealK3BxAJLXWLY1ZICTfTvJCtzC/QEAHqvBApy7Maevo5tbeZNuX/cHOBfWwhu9uzGGAS5qv+4vDD5RUKjaS2+mXnrT7Lg5qzfmemzKjXi849qV/UX9hit5ch63MqjKccnXITnOtkxuZcvntGT9Rduwr9MwHFvkGbjkuidlrf7rJ8cv2xoywN0qP8fx85Ba2zLAq4EXAPCoDBfgbn0YCcrq0NT56Trl5haJzi9v0tXNTHng3LctVsGi4+VNU4435gOir9Nxc5aB0Y8tWYFr63QFD2/ePNpnDZ1kTElZoLmGwXWOxj6uP927yPswvw0/3u7r7HTPSZuPVtbqv37vOMBZ4t9BMva+/ghwAIDbNQe4eycC3IOX23jXwm8dy3IAALAqAty9kduMj0VhJupq1buTbtkCAJAXAtw9aLYHH114AwAAQ8g7wAEAADxCBDgAAIDMEOAAAAAyQ4ADAADIDAEOAAAgMwQ4AACAzBDgAAAAMkOAAwAAyAwBDgAAIDMEOAAAgMwQ4AAAADJDgAMAAMgMAQ4AACAzBDgAAIDMEOAAAAAyQ4ADAADIDAEOAAAgMwQ4AACAzBDgAAAAMkOAAwAAyAwBDgAAIDMEOAAAgMwQ4AAAADJzbwFudjI2o9HEFMoxAAAALG6YAHc2KcPaqDE5C8oPi+Z4U76Kqo04EMrX74ILqmMzvUyPAQAArMPaA1xxaEPbpC27nJrJyax9bYPXztTMbmdmunOHoKMEONvXuGpbqQ8AALAh1hrgqtWnpQLUzBRnQbhbhhbgrMvZEv0DAADkZ40BrjCTuduidtWt3VqNA5g7Pzze25YMcJfTtl27TSvanZy5P8N+3XanrC8teb4YVxNqw23l8nVb9w6rkAAA4FFaX4Cz25faipioE26nVtutTfipA1wdZuZ+6CEJSn7bVgZJH7x83SBE1n2Po/rSnPOreYvn/GSAi0Kea6/6e3UuAQ4AACxnfQGuebZNOdYlOicINs3rnnAjV+ACNhiOm6AoA116blxfWvJ8NcDF47RlaT8AAACLWW+A6whUaT2/Fem2E7sDXM/KmNJf2O7cABeEzZUCXNf5WoATwdaWLRV0AQAAAusLcAtsB/pPqDaha+4K3KIBLj53oRW4rgCWWPJ8AhwAABjY+gLcrXymTVK2RNcV4Op2wnEQ4AAAwKZaa4DzYScMU+0HF9zD/zJYrSXA1at/bXnaz8IBLLHk+csEuAVWLQEAAKQ1BzjHbZV6wZZp/YnNpnxdK3C38ac9s1mBI8ABAIAVDBLgAAAAMBwC3LrJ74UDAABYMwIcAABAZghwAAAAmSHAAQAAZIYABwAAkBkCHAAAQGYIcAAAAJkhwAEAAGSGAAcAAJAZAhwAAEBmCHAAAACZIcABAABkhgAHAACQGQIcAABAZghwAAAAmSHAAQAAZIYABwAAkBkCHAAAQGYIcAAAAJkhwAEAAGSGAAcAAJAZAhwAAEBmCHAAAACZIcABAABkhgAHAACQmWwDXHE4MqPDIi3bmZpZZ92Zme6MzPhklrRnzU7GZjQam+llemx1/X3OdTYpxzQxhSzP0DDXFwCAxyfbAKcFGxuU0oDgAtTkrP37wmHK9qEEwuUs2aekzBMAADxu+Qa4y6kZi7BmX4+bsKbVWzJMEeAAAMADlG+AU4KR3SZNtlajENaeU9UbOVHdOiyFxytBm+Gx+cFqTp9Nv+2xKOzJAFcGUm1Mt7eFmYxseHX9+TppmJ0/p3mBMapbX/N0zPPmol+XsH44j7sHaQAANsfgAe78/Nzs7+9XN2H7p30t66yqeqYqCCHVzV+smsWBrg03TbAp6zereDIsKStwMiDK4ymlz7IsDk9xQItWFsWYZieT+jwf2Hyb7nW4heyeOWvPteEtHMP0xI1Bzqk6r2NeyXOGdVgLg1c4n+65KNelOt7Wj67RiT4eAAAeo8EDnA9vnn0t66wsCgRFfeO3QSbeMo1Ciw0N0crVrA0f8wJcFa7i1am2ry5an7dxP0r9ONTodeOVLxfg4q3a8FrUAVe2o8xJnhfXTcuTFbhA91y06xLPvatNAAAeu7wD3G0bHuyqkS9rVuZkAFO2XZcKcPL4QrQ+7cpU3U69rdke7wtwLqT5NrQAF22ZRmU+4ArLzElej1o0DjGf7rlo1yUtc6uIMugBAPC4DR7ghtxCtdx238RMdtJn2SbJylAaEJYKcB0rUP20PtutV7kN3Bvg6vH4ussFuGCeoWXmpNaN5yfn0zkX9bpoZVbHiiAAAI/U4AFucM2D+e0KnPY8mKMFhDkBTqxOyWfApofpilSs3iqMxlJ0hJp2xUk9XgeotnyZAGe3bcMxzOJn4ORKpTqvei7yeblwHGI+nXPpeC/asllHcNbmCQDA45J/gPOhIliZstwnG+XWoB4ausJHG77C0BKULRQkfJ9FdF5YJ/4Upqunh554S3G5FTjfVtiXPzeeU/+84rq2DfkMXDif7rno70VY1o5HhN/e8QEAsPk2IMDh3XKhi0AFAMD9IcDhTuRXlQAAgOER4LCEdKtV+1QqAAAYFgEOAAAgMwQ4AACAzBDgAAAAMkOAAwAAyAwBDgAAIDMEOAAAgMwQ4AAAADJDgAMAAMgMAQ4AACAzBLh3xP0KqvCXtAMAACwm6wBXHNpf59Qdgtxx8Xs6L6dmPBrwl6+fTdI+O9gQNz6ZJeXzjBdsHwAAbKYNCHClwyI55oOaHqbs7/TsDn53smiAq+otNwa3aud/D+kCfQAAgI2UfYAbH07UFakq7JQhTTvmzMxsifC0sEUD3B10zwkAADwG+Qe4k8JMd+yf4VZkYSZ2devMrsKFYceuvPkVrHAVy9aX26qubv9Wa9G2tTM1M1vmA1yzAihXy1xfS/UTtZWG0mYlsj4uV/XClbtVtmwBAMDDMniAOz8/N/v7+1V4sH/a17LOqlyAm7nQVAao5lj9elYFnyDslK8nQYCpgk+1/bpKgIuDWHESBrgg0PnQ2GzzLhngkmf2ZmkgDLaQ3cqj77ueY/Pa9U2IAwAgb4MHOB/ePPta1llVE+DqEOTKg0AkA5zUBL/lA1wVlLRn77Rn26Jt1eUCXBsy27LeOYVzrv6ujCUIeAAAID+DB7gwvHmyzqraAOcCVVWeBBgRdvwKmbdSgHPH1JUs7Rm4lQOc3k8yp2iL1aqPa2PRrgkAAMjK4AHuflbg7OuiWmmKykRYSb5WZOUVuJ5jWmi6Y4CTx8I5Jd8nF85ZW20jwAEAkL3BA9y9PANXvx6fTN2HF7Qw4z/YoGwn6kFJC3Vx33Jrs2lTBqSoLNzuXa0f2VZ0brICqc+ZLVQAAPI1eIAbUhLg7CpfGHaiACe3I11w8h9+iB/2bz/Z2RWs/LZlM5boQwx9Ac61vXA/1blhCLOffBWris2c3RyT4+JDDE1fWsADAAAP3kYFuOTLeeV2YfSsWFnerMDZ43Wgq03OlNUtqWyv2R72IWqBAOdC2BL9VOe34463QMNxa1+d0obEJCgS4AAAyFLWAQ4AAOAxIsABAABkhgAHAACQGQIcAABAZghwAAAAmSHAAQAAZIYABwAAkBkCHAAAQGYIcAAAAJkhwAEAAGSGAAcAAJAZAhwAAEBmNiPARb/sfc4vhl9a+8vixyez+hfDi19W31jgF9MDAADcUfYBLglUl1MzKYOWrLcaF8hscEuPaQhwAABgeFkHuNnJ2Ix2pmamHFuPZQPZsvUBAACWl3GAc1ubc8PS5dSMg+3VOPC5wOVW8dpt0rD9dmt2bKaXaWi057fnFmmAE/037VfbvhNTRMfTrdmqv+B817Ybtz4nAACw6QYPcPv7+1EAsa9lnZXYANQbXLq2P20wc2HM15HntAFMvhYB7kwGrri+DYay/+r8w6IOcH4ctWhO4ThjybyrECjHAgAANtXgAS4Mb56ssxK/giXLG10rdGHI0gNcG7r6A5z9exwg07bl3P2KmTr+sEw7Xkvaq+hhDwAAbJ7BA9xgK3DVqlNfaOlawUpDljy2TICb17ZcgWtoAU0GOLnSVusqBwAAj8PgAe78/LwJcfZP+1rWWVX17JrdjlSOdQeo+Vuoiwa4dAs1XvXrHd+8ANcTUJPzAADAozJ4gBtW/UGDcEUq/BoR5TmzOFTdMcCV/YcB0X8Yoqlff0Ah2sYtx1S9nhfgfHtibtOz+oMTUTAsr4N/3RP8AADAZsg8wDnhp0j1UBQcj4LPXQPcbfRJ1clZWj/pP1i908cal8Vz88FM/4RsdQ4BDgCAjbcRAQ4AAOAxIcABAABkhgAHAACQGQIcAABAZghwAAAAmSHAAQAAZIYABwAAkBkCHAAAQGYIcAAAAJkhwAEAAGSGAAcAAJAZAhwAAEBmsg5w7he9d//idndc/ML4JclfXt/N/SL78clMOba44rAdb3HYPTcAAPB4bUCAKx0WybHby6kZ22OZBbh23Gtoa93OJgteCwAAMKTsA9z4cFIGnjSkueA1Vo8t494D3ENGgAMA4EHIP8CdFEpwKszEbq2e2dWsMMC5kFWt2snVORtOmvKRmZy5chngqtfB8VYb4JqVQXUVzY5N6X/e+Gpt2/3bq+EYwrpxuZhHdQ3KPoNVQD8GeV606hnVH0XXy841vlZujk2Z79Nff201FQAARAYPcOfn52Z/f7+6Ods/7WtZZ1UuwM2alaHmmF8pqoJFEILK15MgUFWhxAaGql4QiMrXUy3AVSGjKzi14SsOJ3G7NuhE4XCR8YWv/TzLcKqPo63XrJTVdavxKcErHm94bj0nf462AifnKPpfLMAR3AAAWMbgAc6HN8++lnVW1QS4OhS48iAgyAAn+eDXU68JcDLsJETYCcr8KpwMZEmYkcLA1DPGSE89bUWvml8Y0GRADcNxEuC6to3rFdDLRQNcVygGAACawQNctO1Wk3VW1QY4F0Sq8jDAaGHGr/h4VThpV89kGGmfpZNBRNLCTFimHY/n0DU+G5jkVm6XvnpqeRjKqr616zVJ61bcdnB6XdqQlh7XAlwaLAEAQLfBA9z9rMDZ10W1ihOViQDnnuMKwkK4ulS34Z5Pa1eE3DZnGeCS1TVJC2hpgJNhJxxv1/iaANfbv9NXTy2/c4DTVs8IcAAADGnwAHcvz8DVr8cn0zhQRAFOCRtJgHPCENSuaLlwJ1fQWvMC3Lwt1O7xdYYrTU89rTzdQl0mwGlzttq5pKFVrNppfQIAgF6DB7ghJQHOrp4lD+n7cCDDRr3aZgNcGSLCkBEGrWhLsn4OLg0sWvtKmfYhhiYQyfPb8YXH27DV9SEGUS+om5RX4wlCoxamZIBTjysfYqj7kR+ocKuMcwJcPa7mNQAAiGxUgJvuiBUs+QxcHaDcdu7EfXWFDXBReRxykmfKqsAhV9IsGcA6ysK+otWs7vHJFa/meNR/OpZ26zoOsW25suIn2w0DXHh+FBDra6Jcv/hrU2xwC1cdO/okwAEA0CvrALepkq8XAQAACBDgAAAAMkOAAwAAyAwBDgAAIDMEOAAAgMwQ4AAAADJDgAMAAMgMAQ4AACAzBDgAAIDMEOAAAAAyQ4ADAADIDAEOAAAgMwQ4AACAzGQd4IrDkRmNWuOTWVJn/WZmunNffQEAAKSyD3BhkJrcS4gjwIVmJ2MzOiyScgAAMJyNCnBJmLicmnHfCl14vOe80c7UzJrzZIArquDYrgROTBH2cTZxZdWfop/g/MmZa7drrOFq4/SyLa/mXI6vsH8G58Wrk+P6HD/2IuirPubHl8zXSecXjzcec3AsasvP1V+zuq2w7+p43DcAAIgNHuDOz8/N/v5+dWO2f9rXss6qZIAbN0Hltg5hwesmPITH/esycJzUwaoKE+F5dRhqgkgc4No2nCpQhSGuM7jF44r7dGVRSAzOD0OR608Gvri+D3ltsGr7aoJe06bs29WRbUX9R3OLr0/VfnNcBDdLvk/l6ykBDgCAXoMHOB/ePPta1lmVfAYuXDWS4c4Kw4Z2XIaPlg0echXL1UmDmTvehDolEKZtp33KoBQaBwEoCYyaKiRNjBx7eyweXxTKmnP98fBaKAHOzjccd32+G58y1+g4AABYxOABLgxYnqyzqiiElUGgXQlLt/caVbgQq3GNrvIwlIUhaJYEr2RcfgtV1JnbpxqE/DxEgNOCntwG7g1w8fiiUCa2Nz0/Xhng/IpgzAc+ba7te6VdSwAAkBo8wA29Ahfe9OXzWd2BIF5Fml/eHeCS4HW7/gDnQlE7rmQFTgQ4WX/+Cty8ABeuwMXUAKcFykrHXINj/auVAADAGjzA3eczcN3PXklKkOktv+sW6vIBrg1Gor3beQEurX+nAFdvsYZjC8kA1z9ffa697QEAgMTgAW5IMsBFz5vVW4hRWCiPx8EqCGXzPsTQhIo4BMk+kkDVG2gsv/IU1BHPpcn+522hyvpui3LFAFe3FwXEQ/EhBiVAtucXwQcqlAAXvid1X/5cghwAALrNCnA+PPhAIZ/fklt7wfE0CAbnRUFChCD5rJnax/wA1361hhOvUoXHxnNW4NL607M7rMBVbGicP7a2XdF/E4aVACevX9AvAQ4AAF3WAW4zKKEGAACgBwHunSPAAQCA5RDg3jkCHAAAWA4BDgAAIDMEOAAAgMwQ4AAAADJDgAMAAMgMAQ4AACAzBDgAAIDMEOAAAAAyQ4ADAADIDAEOAAAgMwQ4AACAzBDgAAAAMkOAAwAAyAwBDgAAIDMEOAAAgMwQ4AAAADJDgAMAAMgMAQ4AACAzBDgAAIDMEOAAAAAyQ4ADAADIDAEOAAAgMwQ4AACAzBDgAAAAMkOAAwAAyAwBDgAAIDMEOAAAgMz8HyI4OZgW/cs6AAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,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>

[image5]: <data:image/png;base64,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>

[image6]: <data:image/png;base64,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>

[image7]: <data:image/png;base64,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>