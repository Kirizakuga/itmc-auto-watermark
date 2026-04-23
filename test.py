import streamlit as st
from PIL import Image
import io
import zipfile
import os

# --- ĐƯỜNG DẪN LOGO MẶC ĐỊNH TRÊN SERVER/VPS ---
# File logo này phải được đặt CÙNG THƯ MỤC với file code (test.py) trên VPS
DEFAULT_LOGO_PATH = "logo-01.png"


# ==========================================
# HÀM XỬ LÝ LÕI (CHẠY NGẦM)
# ==========================================
def process_single_image(bg_img, logo_img, config):
    """
    Hàm xử lý ghép logo lên ảnh nền. Mọi thao tác đều diễn ra trên RAM.
    """
    # Chuyển cả 2 ảnh về hệ màu có hỗ trợ nền trong suốt (RGBA)
    bg_img = bg_img.convert("RGBA")
    logo_img = logo_img.convert("RGBA")

    # Lấy kích thước gốc của ảnh nền
    bg_width, bg_height = bg_img.size

    # Đọc các thông số cấu hình từ giao diện web (thanh trượt)
    scale_ratio = config.get("logo_scale_ratio", 0.3)
    margin_ratio = config.get("top_margin_ratio", 0.1)
    y_offset = config.get("y_offset_px", -60)

    # Tính toán kích thước mới cho logo dựa trên tỷ lệ bề ngang ảnh nền
    target_logo_width = int(bg_width * scale_ratio)
    aspect_ratio = logo_img.height / logo_img.width
    target_logo_height = int(target_logo_width * aspect_ratio)

    # Thu phóng logo bằng thuật toán chất lượng cao LANCZOS
    resized_logo = logo_img.resize((target_logo_width, target_logo_height), Image.Resampling.LANCZOS)

    # Tính toán tọa độ dán (X: canh giữa, Y: canh theo lề và số pixel bù trừ)
    x_position = (bg_width - target_logo_width) // 2
    y_position = int(bg_height * margin_ratio) + y_offset

    # Tạo một lớp kính ảo (trong suốt) bằng kích thước ảnh nền
    transparent_layer = Image.new('RGBA', bg_img.size, (0, 0, 0, 0))
    # Dán logo lên lớp kính ảo đó
    transparent_layer.paste(resized_logo, (x_position, y_position), mask=resized_logo)

    # Gộp lớp kính ảo chứa logo đè lên ảnh nền gốc
    final_img = Image.alpha_composite(bg_img, transparent_layer)
    return final_img


# ==========================================
# GIAO DIỆN WEB (STREAMLIT)
# ==========================================
# Cài đặt tiêu đề tab trên trình duyệt và mở rộng hiển thị full màn hình
st.set_page_config(page_title="Auto Watermark Tool", layout="wide")

st.title("🧩 Tool Gắn Logo Tự Động")
st.markdown("Kéo thả ảnh vào đây, tinh chỉnh vị trí và tải toàn bộ kết quả về dưới dạng file ZIP.")

# Chia giao diện làm 2 cột (Cột trái nhỏ hơn cột phải)
col1, col2 = st.columns([1, 2])

# --- CỘT 1: CÁC THANH TRƯỢT ĐIỀU CHỈNH ---
with col1:
    st.header("⚙️ Tinh chỉnh thông số")
    # Tạo thanh trượt cho người dùng tự kéo. (Tên, min, max, mặc định, bước nhảy)
    scale_ratio = st.slider("📐 Kích thước Logo (scale_ratio)", min_value=0.05, max_value=1.0, value=0.3, step=0.05)
    margin_ratio = st.slider("📏 Lề trên (top_margin_ratio)", min_value=0.0, max_value=0.5, value=0.1, step=0.01)
    y_offset = st.slider("↕️ Bù trừ độ cao (y_offset_px)", min_value=-1000, max_value=1000, value=-60, step=10)

    # Gói các giá trị thanh trượt vào một biến config để truyền vào hàm xử lý
    config = {
        "logo_scale_ratio": scale_ratio,
        "top_margin_ratio": margin_ratio,
        "y_offset_px": y_offset
    }

# --- CỘT 2: KHU VỰC KÉO THẢ ẢNH ---
with col2:
    st.header("📂 Tải file lên")

    # Ô upload logo (MỚI THÊM)
    logo_upload = st.file_uploader("1. Tải lên Logo khác (Tùy chọn. Để trống sẽ dùng logo mặc định)", type=['png'])

    # Ô upload ảnh nền
    bg_files = st.file_uploader("2. Kéo thả các ảnh cần gắn Logo vào đây", type=['png', 'jpg', 'jpeg', 'webp'],
                                accept_multiple_files=True)

# ==========================================
# THỰC THI & TẠO FILE TẢI VỀ
# ==========================================
# Nếu người dùng đã upload ảnh nền lên
if bg_files:
    try:
        # --- LOGIC ƯU TIÊN LOGO ---
        # 1. Nếu có file upload lên thì xài file đó
        if logo_upload is not None:
            logo_img = Image.open(logo_upload)
        # 2. Nếu không có file upload thì rà xem có file mặc định trên server không
        elif os.path.exists(DEFAULT_LOGO_PATH):
            logo_img = Image.open(DEFAULT_LOGO_PATH)
        # 3. Nếu lỡ mất cả 2 thì báo lỗi và dừng chạy code
        else:
            st.error(f"⚠️ Lỗi: Không tìm thấy logo mặc định ({DEFAULT_LOGO_PATH}) và bạn cũng chưa tải logo nào lên!")
            st.stop()

        st.markdown("---")
        st.subheader("👀 Preview & Tải về")

        # Tạo nút bấm màu xanh (primary) để bắt đầu chạy
        if st.button("🚀 Bắt đầu xử lý ảnh", type="primary"):
            # Hiện thanh màu xanh chạy % tiến độ
            progress_text = "Đang xử lý ảnh..."
            my_bar = st.progress(0, text=progress_text)

            # Tạo một không gian bộ nhớ ảo trên RAM để chứa file ZIP
            zip_buffer = io.BytesIO()

            # Mở file ZIP ảo đó ra để chuẩn bị nhét ảnh vào
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                total_files = len(bg_files)

                # Vòng lặp duyệt qua từng ảnh nền người dùng tải lên
                for idx, bg_file in enumerate(bg_files):
                    # Mở ảnh và cho qua hàm xử lý gắn logo
                    bg_img = Image.open(bg_file)
                    final_img = process_single_image(bg_img, logo_img, config)

                    # Xác định đuôi ảnh gốc để lưu ra cho đúng chuẩn (JPG hoặc PNG)
                    ext = bg_file.name.split('.')[-1].lower()
                    fmt = "JPEG" if ext in ['jpg', 'jpeg'] else "PNG"

                    if fmt == "JPEG":
                        final_img = final_img.convert("RGB")  # JPG không hỗ trợ nền trong suốt nên phải convert

                    # Lưu ảnh với chất lượng tối đa (quality=100) và tắt tính năng nén màu (subsampling=0)
                    img_byte_arr = io.BytesIO()
                    if fmt == "JPEG":
                        final_img.save(img_byte_arr, format=fmt, quality=100, subsampling=0)
                    else:
                        final_img.save(img_byte_arr, format=fmt)  # PNG mặc định là lossless nên không bị mờ

                    img_byte_arr.seek(0)

                    # Ghi ảnh từ RAM thẳng vào trong file ZIP ảo
                    zip_file.writestr(f"done_{bg_file.name}", img_byte_arr.read())

                    # Chỉ trích xuất ảnh đầu tiên để hiện lên giao diện web (đỡ lag trình duyệt)
                    if idx == 0:
                        st.image(final_img, caption="Ảnh Preview (Ảnh đầu tiên)", width="stretch")

                    # Cập nhật thanh % tiến độ
                    my_bar.progress((idx + 1) / total_files, text=f"Đang xử lý: {idx + 1}/{total_files}")

            # Chạy xong hết vòng lặp, báo xanh và hiện nút tải file ZIP
            st.success("✅ Hoàn tất!")
            st.download_button(
                label="📥 Tải toàn bộ ảnh (File ZIP)",
                data=zip_buffer.getvalue(),  # Rút ruột toàn bộ dữ liệu file ZIP ảo để người dùng tải về máy
                file_name="watermarked_images.zip",
                mime="application/zip"
            )

    except Exception as e:
        # Bắt lỗi nếu có file hỏng hoặc lỗi không lường trước
        st.error(f"Có lỗi xảy ra: {e}")