# DocCompare – Công cụ So sánh Hợp đồng Word (.docx/.doc) ↔ PDF (WeSign)

**DocCompare** là ứng dụng chuyên dụng đối soát hợp đồng pháp lý, giúp người kiểm tra phát hiện chính xác mọi thay đổi về số liệu, ngày tháng, nội dung điều khoản giữa bản Word đã phê duyệt nội bộ và bản PDF đã ký số qua WeSign, đồng thời tự động triệt tiêu các loại nhiễu do dàn trang và convert.

---

## 1. Yêu cầu hệ thống (Prerequisites)

### ⚠️ Bắt buộc: Cài đặt LibreOffice
Để đảm bảo chuyển đổi tài liệu Word sang PDF tạm thời độc lập và chính xác, máy tính cần cài đặt **LibreOffice**:
- **Link tải chính thức:** [https://www.libreoffice.org/download/download/](https://www.libreoffice.org/download/download/) (Khuyến nghị bản ổn định: LibreOffice 24.x hoặc 25.x, bản 64-bit Windows MSI).
- **Đường dẫn mặc định trên Windows:** `C:\Program Files\LibreOffice\program\soffice.exe` (tool sẽ tự động nhận diện mà không cần cấu hình thêm).

---

## 2. Hướng dẫn triển khai cho máy Windows của User

Có 2 cách triển khai cho máy Windows:

### 🌟 Cách 1: Tải file `.exe` đã đóng gói (Dành cho User không rành kỹ thuật)
*User KHÔNG CẦN cài Python, KHÔNG CẦN gõ lệnh Terminal.*

#### Cách A: Tự động tải từ GitHub Actions (Khuyến nghị - Không cần máy Windows để build)
Dự án đã tích hợp sẵn GitHub Actions workflow tự động build trên máy ảo Windows của GitHub:
1. Truy cập repo của anh trên GitHub: **[khoavudl/DocCompare](https://github.com/khoavudl/DocCompare)**.
2. Vào tab **Actions** $\rightarrow$ chọn workflow **"Build Windows Application (.exe)"** ở cột trái.
3. Bấm nút **Run workflow** $\rightarrow$ chọn branch `main` $\rightarrow$ bấm **Run workflow**.
4. Chờ khoảng 2–3 phút cho GitHub build xong $\rightarrow$ click vào lượt chạy đó và cuộn xuống mục **Artifacts** $\rightarrow$ tải file **`DocCompare-windows-x64.zip`** về.
5. Giải nén trên máy Windows của User, mở file **`DocCompare.exe`** là chạy ngay!
*(Lưu ý: Máy user chỉ cần cài LibreOffice từ [libreoffice.org](https://www.libreoffice.org/download/download/) là xong)*.

#### Cách B: Tự build thủ công trên máy Windows
Nếu muốn tự build trên máy Windows cục bộ có Python:
```bash
pip install pyinstaller
pyinstaller --noconfirm --onedir --windowed ^
  --name "DocCompare" ^
  --add-data "config/filters.yaml;config" ^
  --add-data "report/template.html.j2;report" ^
  --add-data "Logo-fes.png;." ^
  app.py
```
*(Thư mục sau khi build nằm tại `dist/DocCompare/`, copy sang máy user và chạy `DocCompare.exe`)*.


---

### 💻 Cách 2: Chạy trực tiếp từ mã nguồn (Dành cho Developer / IT)
1. Cài đặt **Python 3.10+** (tích hợp sẵn pip).
2. Cài đặt **LibreOffice**.
3. Tải hoặc clone mã nguồn:
   ```bash
   git clone https://github.com/khoavudl/DocCompare.git
   cd DocCompare
   ```
4. Cài đặt thư viện:
   ```bash
   pip install -r requirements.txt
   ```
5. Khởi chạy giao diện:
   ```bash
   python app.py
   ```

---

## 3. Hướng dẫn sử dụng Giao diện Desktop

```text
┌────────────────────────────────────────────────────────┐
│ [Logo FES]    So sánh hợp đồng Word ↔ PDF              │
├────────────────────────────────────────────────────────┤
│ File Word (đã duyệt):  [ D:\HopDong\approved.docx ]    │
│ File PDF (WeSign):     [ C:\Users\Downloads\signed.pdf]│
│                                                        │
│ [ ] Phân biệt chữ hoa/thường                           │
│                                                        │
│                    [   So sánh   ]                     │
│ [██████████████████████████] 100% Hoàn tất!            │
├────────────────────────────────────────────────────────┤
│ Kết quả:                                               │
│ 🔴 4 điểm khác biệt                                    │
│ 🟡 0 có thể là nhiễu    ⚪ 44 đã lọc                   │
│ ⚠️ File Word có 2 comment                              │
│                                                        │
│ [ Mở báo cáo chi tiết ]      [ Mở thư mục ]            │
└────────────────────────────────────────────────────────┘
```

1. **Chọn file:**
   - **File Word (đã duyệt):** Bấm `Chọn…` chọn file `.docx` hoặc `.doc`.
   - **File PDF (WeSign):** Bấm `Chọn…` chọn file `.pdf`.
   *(Hai file có thể ở 2 thư mục hoàn toàn khác nhau)*.
2. **Tùy chọn:** Bật ô *"Phân biệt chữ hoa/thường"* nếu cần kiểm tra thay đổi viết hoa/thường.
3. **So sánh:** Bấm nút **[ So sánh ]** và chờ vài giây.
4. **Xem kết quả:**
   - Cụm Badge hiển thị tổng quan: 🔴 Sai khác thật, 🟡 Nghi ngờ nhiễu, ⚪ Token đã lọc.
   - Bấm **[ Mở báo cáo chi tiết ]** để xem toàn bộ bảng đối chiếu trực quan trên trình duyệt (có highlight từng ký tự thay đổi).
   - Bấm **[ Mở thư mục ]** để mở thư mục lưu file báo cáo (tự động lưu cùng thư mục với file PDF đã chọn).

---

## 4. Sử dụng dòng lệnh (CLI)

Ngoài giao diện đồ họa, có thể chạy so sánh tự động qua dòng lệnh:
```bash
# So sánh và in tóm tắt ra console:
python cli.py path/to/approved.docx path/to/signed.pdf

# Xuất báo cáo HTML:
python cli.py path/to/approved.docx path/to/signed.pdf -o report.html

# Xuất kết quả dạng JSON để tích hợp hệ thống:
python cli.py path/to/approved.docx path/to/signed.pdf --json
```

---

## 5. Tùy biến bộ lọc nhiễu (`config/filters.yaml`)

File cấu hình [config/filters.yaml](file:///Users/tindn/Documents/Code/DocCompare/config/filters.yaml) cho phép tùy chỉnh các tham số lọc:
- **`N2_page_number`:** Lọc số trang độc lập (ví dụ: `Trang 1/5`, `1`).
- **`N3_signature`:** Bỏ qua các khối chữ ký số và ký hiệu WeSign.
- **`N4_header_footer`:** Tự động phát hiện và loại bỏ header/footer lặp lại trên $\ge 60\%$ số trang.
- **`N5_unicode`:** Chuẩn hoá Unicode NFC và hợp nhất dấu thanh tổ hợp tiếng Việt.
- **`N6_whitespace`:** Nối từ bị ngắt dòng có dấu nối hyphen.
- **`N8_char_map`:** Chuẩn hoá ngoặc kép cong, dấu gạch nối dài, và bullet point (`\uf0b7` $\rightarrow$ `-`).
- **`N10_reorder`:** Phát hiện nội dung giữ nguyên nhưng bị xáo trộn thứ tự đọc do dàn trang.
