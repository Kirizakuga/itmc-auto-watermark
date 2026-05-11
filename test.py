import streamlit as st
import subprocess
import io
import zipfile
import os
import tempfile
import concurrent.futures
from pathlib import Path

# --- ĐƯỜNG DẪN LOGO MẶC ĐỊNH ---
DEFAULT_LOGO_PATH = "logo-01.png"

# ==========================================
# HÀM XỬ LÝ LÕI (FFMPEG)
# ==========================================

def get_ffmpeg_filter(config):
    """
    Tạo chuỗi filter_complex cho FFmpeg dựa trên cấu hình.
    [1:v] là logo, [0:v] là ảnh nền/video.
    """
    scale_ratio = config.get("logo_scale_ratio", 0.3)
    margin_ratio = config.get("top_margin_ratio", 0.1)
    y_offset = config.get("y_offset_px", -60)
    
    # Filter: 
    # 1. Thu phóng logo dựa trên bề ngang ảnh nền (main_w)
    # 2. Ghi đè (overlay) lên ảnh nền tại vị trí tính toán
    filter_str = (
        f"[1:v]scale=iw*{scale_ratio}:-1[logo];"
        f"[0:v][logo]overlay=(W-w)/2:H*{margin_ratio}+{y_offset}"
    )
    return filter_str

def process_image_pipe(image_bytes, logo_path, config):
    """
    Xử lý ảnh tĩnh hoàn toàn trên RAM qua Pipe để đạt tốc độ cao nhất.
    Sử dụng .communicate() để tránh Deadlock.
    """
    filter_complex = get_ffmpeg_filter(config)
    
    cmd = [
        'ffmpeg', '-y',
        '-i', 'pipe:0',              # Nhận ảnh từ stdin
        '-i', logo_path,             # File logo
        '-filter_complex', filter_complex,
        '-f', 'image2pipe',          # Xuất định dạng pipe
        '-vcodec', 'png',            # Giữ chất lượng PNG
        'pipe:1'                     # Đẩy kết quả ra stdout
    ]
    
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate(input=image_bytes)
    
    if process.returncode != 0:
        raise Exception(f"FFmpeg Error: {stderr.decode()}")
    
    return stdout

def extract_frame_fast_seek(video_bytes, timestamp, logo_path, config):
    """
    Trích xuất 1 frame từ video tại timestamp cụ thể (Fast Seek).
    Dùng để Live Preview cực nhanh.
    """
    filter_complex = get_ffmpeg_filter(config)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
        tmp_video.write(video_bytes)
        tmp_video_path = tmp_video.name

    try:
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(timestamp),       # Fast Seek (đặt trước -i)
            '-i', tmp_video_path,
            '-i', logo_path,
            '-filter_complex', filter_complex,
            '-frames:v', '1',            # Chỉ lấy 1 frame
            '-f', 'image2pipe',
            '-vcodec', 'png',
            'pipe:1'
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"FFmpeg Error: {stderr.decode()}")
        
        return stdout
    finally:
        if os.path.exists(tmp_video_path):
            os.remove(tmp_video_path)

def process_video_full(video_bytes, video_name, logo_path, config):
    """
    Xử lý toàn bộ video. Ghi file tạm và dọn dẹp sạch sẽ.
    """
    filter_complex = get_ffmpeg_filter(config)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        input_path = os.path.join(tmp_dir, "input_" + video_name)
        output_path = os.path.join(tmp_dir, "output_" + video_name)
        
        with open(input_path, 'wb') as f:
            f.write(video_bytes)
            
        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-i', logo_path,
            '-filter_complex', filter_complex,
            '-vcodec', 'libx264',
            '-preset', 'medium',        # Cân bằng giữa tốc độ và dung lượng
            '-crf', '23',               # Chất lượng tiêu chuẩn
            '-acodec', 'copy',          # Giữ nguyên âm thanh
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"FFmpeg Error: {result.stderr}")
            
        with open(output_path, 'rb') as f:
            return f.read()

# ==========================================
# GIAO DIỆN WEB (STREAMLIT)
# ==========================================
st.set_page_config(page_title="Auto Watermark Tool (FFmpeg)", layout="wide")

st.title("🧩 Tool Gắn Logo Tự Động (Pro)")
st.markdown("Hỗ trợ cả **Ảnh** và **Video**. Sử dụng engine FFmpeg cho hiệu suất tối đa.")

col1, col2 = st.columns([1, 2])

with col1:
    st.header("⚙️ Tinh chỉnh thông số")
    scale_ratio = st.slider("📐 Kích thước Logo", 0.05, 1.0, 0.3, 0.05)
    margin_ratio = st.slider("📏 Lề trên (Y ratio)", 0.0, 0.5, 0.1, 0.01)
    y_offset = st.slider("↕️ Bù trừ độ cao (px)", -1000, 1000, -60, 10)
    
    config = {
        "logo_scale_ratio": scale_ratio,
        "top_margin_ratio": margin_ratio,
        "y_offset_px": y_offset
    }

with col2:
    st.header("📂 Tải file lên")
    logo_upload = st.file_uploader("1. Tải lên Logo (Tùy chọn)", type=['png'])
    
    # Hỗ trợ cả ảnh và video
    bg_files = st.file_uploader("2. Kéo thả Ảnh hoặc Video vào đây", 
                                type=['png', 'jpg', 'jpeg', 'webp', 'mp4', 'mov', 'avi'],
                                accept_multiple_files=True)

if bg_files:
    # --- QUẢN LÝ LOGO ---
    temp_logo_path = None
    try:
        if logo_upload is not None:
            # Lưu logo tạm để FFmpeg đọc
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(logo_upload.getvalue())
                temp_logo_path = tmp.name
        elif os.path.exists(DEFAULT_LOGO_PATH):
            temp_logo_path = DEFAULT_LOGO_PATH
        else:
            st.error("⚠️ Không tìm thấy logo!")
            st.stop()

        st.markdown("---")
        st.subheader("👀 Preview & Thực thi")

        # --- XỬ LÝ PREVIEW (Ảnh/Video đầu tiên) ---
        first_file = bg_files[0]
        is_video = first_file.type.startswith('video')
        
        preview_container = st.container()
        
        if is_video:
            # Nếu là video, thêm thanh trượt chọn thời điểm preview
            preview_ts = st.slider("🕒 Xem trước tại giây thứ:", 0, 60, 0) # Giới hạn 60s đầu để demo
            if st.button("🔄 Cập nhật Preview Video"):
                with st.spinner("Đang trích xuất frame..."):
                    frame_bytes = extract_frame_fast_seek(first_file.getvalue(), preview_ts, temp_logo_path, config)
                    st.image(frame_bytes, caption=f"Preview tại {preview_ts}s")
        else:
            # Nếu là ảnh, preview tức thì
            with st.spinner("Đang tạo preview..."):
                preview_bytes = process_image_pipe(first_file.getvalue(), temp_logo_path, config)
                st.image(preview_bytes, caption="Ảnh Preview (Ảnh đầu tiên)")

        # --- NÚT BẮT ĐẦU XỬ LÝ BATCH ---
        if st.button("🚀 Bắt đầu xử lý toàn bộ", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, "w") as zip_f:
                # Giới hạn số worker để tránh sập CPU
                max_workers = min(os.cpu_count() or 2, 4)
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {}
                    for f in bg_files:
                        f_bytes = f.getvalue()
                        if f.type.startswith('video'):
                            futures[executor.submit(process_video_full, f_bytes, f.name, temp_logo_path, config)] = f.name
                        else:
                            futures[executor.submit(process_image_pipe, f_bytes, temp_logo_path, config)] = f.name
                    
                    for i, future in enumerate(concurrent.futures.as_completed(futures)):
                        f_name = futures[future]
                        try:
                            result_bytes = future.result()
                            zip_f.writestr(f"watermarked_{f_name}", result_bytes)
                            
                            prog = (i + 1) / len(bg_files)
                            progress_bar.progress(prog)
                            status_text.text(f"Đã xong: {f_name} ({i+1}/{len(bg_files)})")
                        except Exception as e:
                            st.error(f"Lỗi khi xử lý {f_name}: {e}")

            st.success("✅ Tất cả đã hoàn thành!")
            st.download_button(
                label="📥 Tải về File ZIP",
                data=zip_buffer.getvalue(),
                file_name="watermarked_media.zip",
                mime="application/zip"
            )

    finally:
        # Dọn dẹp logo tạm nếu có
        if logo_upload is not None and temp_logo_path and os.path.exists(temp_logo_path):
            os.remove(temp_logo_path)