import streamlit as st
import subprocess
import os
import shutil
import tempfile
import zipfile
import gc
from pathlib import Path

# --- ĐƯỜNG DẪN LOGO MẶC ĐỊNH ---
DEFAULT_LOGO_PATH = str(Path(__file__).resolve().parent / "logo-01.png")

# ponytail: presets hardcoded in dict, upgrade to enum/config if preset count > 10.
POSITION_PRESETS = {
    "Top-Center (Mặc định)": {"x": 0.5, "y": 0.05, "x_off": 0, "y_off": 0},
    "Top-Left":              {"x": 0.05, "y": 0.05, "x_off": 0, "y_off": 0},
    "Top-Right":             {"x": 0.95, "y": 0.05, "x_off": 0, "y_off": 0},
    "Center":                {"x": 0.5, "y": 0.5, "x_off": 0, "y_off": 0},
    "Bottom-Left":           {"x": 0.05, "y": 0.95, "x_off": 0, "y_off": 0},
    "Bottom-Center":         {"x": 0.5, "y": 0.95, "x_off": 0, "y_off": 0},
    "Bottom-Right":          {"x": 0.95, "y": 0.95, "x_off": 0, "y_off": 0},
    "Tùy chỉnh":             None,
}

# ==========================================
# HÀM XỬ LÝ LÕI (FFMPEG)
# ==========================================

def get_ffmpeg_filter(config):
    """
    Tạo chuỗi filter_complex cho FFmpeg dựa trên cấu hình.
    [1:v] là logo, [0:v] là ảnh nền/video.
    """
    scale_ratio = config.get("logo_scale_ratio", 0.3)
    x_ratio = config.get("x_ratio", 0.5)
    x_offset = config.get("x_offset_px", 0)

    if "y_ratio" in config:
        y_ratio = config.get("y_ratio", 0.05)
        y_offset = config.get("y_offset_px", 0)
        filter_str = (
            f"[1:v]scale=trunc(iw*{scale_ratio}/2)*2:-2[logo];"
            f"[0:v][logo]overlay=(W-w)*{x_ratio}{x_offset:+d}:(H-h)*{y_ratio}{y_offset:+d}"
        )
    else:
        margin_ratio = config.get("top_margin_ratio", 0.1)
        y_offset = config.get("y_offset_px", -60)
        filter_str = (
            f"[1:v]scale=trunc(iw*{scale_ratio}/2)*2:-2[logo];"
            f"[0:v][logo]overlay=(W-w)/2:H*{margin_ratio}+{y_offset}"
        )
    return filter_str

def process_image_to_file(image_path, output_path, logo_path, config):
    """
    Xử lý ảnh từ file đĩa ra file đĩa qua FFmpeg.
    Không giữ dữ liệu uncompressed trong RAM.
    -q:v 2 đảm bảo chất lượng hình ảnh đạt ~98% (near-lossless JPEG).
    """
    filter_complex = get_ffmpeg_filter(config)

    cmd = [
        'ffmpeg', '-y',
        '-nostdin',
        '-loglevel', 'error',
        '-i', image_path,
        '-i', logo_path,
        '-filter_complex', filter_complex,
        '-q:v', '2',
        output_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise Exception(f"FFmpeg Error: {result.stderr}")

    return output_path

def process_video_to_file(input_path, output_path, logo_path, config):
    """
    Xử lý video từ file đĩa ra file đĩa.
    CRF 20 tối ưu dung lượng, yuv420p + faststart tương thích mọi thiết bị.
    """
    filter_complex = get_ffmpeg_filter(config)

    cmd = [
        'ffmpeg', '-y',
        '-nostdin',
        '-loglevel', 'error',
        '-i', input_path,
        '-i', logo_path,
        '-filter_complex', filter_complex,
        '-vcodec', 'libx264',
        '-preset', 'fast',
        '-crf', '20',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        '-acodec', 'copy',
        output_path
    ]

    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise Exception(f"FFmpeg Error: {result.stderr}")

    return output_path

def extract_frame_fast_seek(video_path, timestamp, logo_path, config):
    """
    Trích xuất 1 frame từ video tại timestamp cụ thể (Fast Seek).
    Dùng để Live Preview cực nhanh.
    """
    filter_complex = get_ffmpeg_filter(config)

    cmd = [
        'ffmpeg', '-y',
        '-nostdin',
        '-loglevel', 'error',
        '-ss', str(timestamp),
        '-i', video_path,
        '-i', logo_path,
        '-filter_complex', filter_complex,
        '-frames:v', '1',
        '-f', 'image2pipe',
        '-vcodec', 'png',
        'pipe:1'
    ]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        raise Exception(f"FFmpeg Error: {stderr.decode()}")

    return stdout

def preview_image_pipe(image_path, logo_path, config):
    """
    Tạo preview nhanh cho 1 ảnh duy nhất từ đường dẫn tạm.
    """
    filter_complex = get_ffmpeg_filter(config)

    cmd = [
        'ffmpeg', '-y',
        '-nostdin',
        '-loglevel', 'error',
        '-i', image_path,
        '-i', logo_path,
        '-filter_complex', filter_complex,
        '-f', 'image2pipe',
        '-vcodec', 'png',
        'pipe:1'
    ]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        raise Exception(f"FFmpeg Error: {stderr.decode()}")

    return stdout

# ==========================================
# GIAO DIỆN WEB (STREAMLIT)
# ==========================================
st.set_page_config(page_title="Auto Watermark Tool", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* Premium Typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Clean up Streamlit UI */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* High-End Brutalist/Minimalist Form Styling */
    .stButton>button {
        background-color: #111111;
        color: #FFFFFF;
        border: 1px solid #222222;
        border-radius: 4px;
        padding: 0.5rem 2rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #333333;
        border-color: #444444;
        color: #FFFFFF;
    }
    
    /* Typography improvements */
    h1 {
        letter-spacing: -0.03em;
        font-weight: 600;
    }
    h2, h3 {
        letter-spacing: -0.02em;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

st.title("Auto Watermark Tool")
st.markdown("<p style='color: #666; font-size: 1.1rem; margin-top: -1rem; margin-bottom: 2rem;'>Professional media watermarking powered by FFmpeg engine.</p>", unsafe_allow_html=True)

col1, col2 = st.columns([1, 2])

with col1:
    st.header("⚙️ Tinh chỉnh thông số")
    scale_ratio = st.slider("📐 Kích thước Logo", 0.05, 1.0, 0.3, 0.05)

    if "pos_x" not in st.session_state:
        st.session_state.pos_x = 0.5
        st.session_state.pos_y = 0.05
        st.session_state.off_x = 0
        st.session_state.off_y = 0

    def apply_preset():
        choice = st.session_state.preset_choice
        preset = POSITION_PRESETS.get(choice)
        if preset:
            st.session_state.pos_x = preset["x"]
            st.session_state.pos_y = preset["y"]
            st.session_state.off_x = preset["x_off"]
            st.session_state.off_y = preset["y_off"]

    st.selectbox(
        "📍 Vị trí định sẵn",
        list(POSITION_PRESETS.keys()),
        index=0,
        key="preset_choice",
        on_change=apply_preset,
    )

    x_ratio = st.slider("↔️ Vị trí ngang (X ratio)", 0.0, 1.0, step=0.01, key="pos_x")
    x_offset = st.slider("↔️ Bù trừ ngang (px)", -1000, 1000, step=5, key="off_x")
    y_ratio = st.slider("↕️ Vị trí dọc (Y ratio)", 0.0, 1.0, step=0.01, key="pos_y")
    y_offset = st.slider("↕️ Bù trừ dọc (px)", -1000, 1000, step=5, key="off_y")

    config = {
        "logo_scale_ratio": scale_ratio,
        "x_ratio": x_ratio,
        "x_offset_px": x_offset,
        "y_ratio": y_ratio,
        "y_offset_px": y_offset,
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
        def is_video_file(file_obj):
            file_type = getattr(file_obj, "type", "") or ""
            if file_type.startswith("video"):
                return True
            return Path(file_obj.name).suffix.lower() in [".mp4", ".mov", ".avi", ".mkv", ".webm"]

        first_file = bg_files[0]
        is_video = is_video_file(first_file)
        preview_container = st.container()
        first_ext = Path(first_file.name).suffix or ('.mp4' if is_video else '.png')

        if is_video:
            preview_ts = st.slider("🕒 Xem trước tại giây thứ:", 0, 60, 0)
            if st.button("🔄 Cập nhật Preview Video"):
                with st.spinner("Đang trích xuất frame..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=first_ext) as tmp_prev:
                        shutil.copyfileobj(first_file, tmp_prev)
                        tmp_prev_path = tmp_prev.name
                    first_file.seek(0)
                    try:
                        frame_bytes = extract_frame_fast_seek(tmp_prev_path, preview_ts, temp_logo_path, config)
                        st.image(frame_bytes, caption=f"Preview tại {preview_ts}s")
                    finally:
                        if os.path.exists(tmp_prev_path):
                            os.remove(tmp_prev_path)
        else:
            with st.spinner("Đang tạo preview..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=first_ext) as tmp_prev:
                    shutil.copyfileobj(first_file, tmp_prev)
                    tmp_prev_path = tmp_prev.name
                first_file.seek(0)
                try:
                    preview_bytes = preview_image_pipe(tmp_prev_path, temp_logo_path, config)
                    st.image(preview_bytes, caption="Ảnh Preview (Ảnh đầu tiên)")
                finally:
                    if os.path.exists(tmp_prev_path):
                        os.remove(tmp_prev_path)

        # --- NÚT BẮT ĐẦU XỬ LÝ BATCH (DISK STREAMING, ZERO-RAM) ---
        if st.button("🚀 Bắt đầu xử lý toàn bộ", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()

            with tempfile.TemporaryDirectory() as batch_dir:
                zip_path = os.path.join(batch_dir, "watermarked_media.zip")
                seen_names = {}

                with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zip_f:
                    total_files = len(bg_files)

                    for idx, f in enumerate(bg_files):
                        f_is_video = is_video_file(f)
                        ext = Path(f.name).suffix or ('.mp4' if f_is_video else '.png')
                        out_ext = ".mp4" if f_is_video else ext

                        # Tên file tạm an toàn bằng index, tránh lỗi ký tự đặc biệt
                        in_path = os.path.join(batch_dir, f"in_{idx}{ext}")
                        out_path = os.path.join(batch_dir, f"out_{idx}{out_ext}")

                        # 1. Ghi stream trực tiếp xuống đĩa
                        with open(in_path, 'wb') as in_f:
                            shutil.copyfileobj(f, in_f)

                        # 2. Giải phóng ngay buffer upload trong RAM của Streamlit
                        f.close()

                        # 3. Tính tên file lưu trong file ZIP (chống trùng lặp)
                        base_name = Path(f.name).stem + out_ext if f_is_video else f.name
                        count = seen_names.get(base_name, 0)
                        seen_names[base_name] = count + 1
                        if count > 0:
                            arc_stem = Path(base_name).stem
                            arc_name = f"watermarked_{arc_stem}_{count}{out_ext}"
                        else:
                            arc_name = f"watermarked_{base_name}"

                        # 4. Thực thi xử lý tuần tự (FFmpeg tự tối ưu đa luồng)
                        try:
                            if f_is_video:
                                process_video_to_file(in_path, out_path, temp_logo_path, config)
                            else:
                                process_image_to_file(in_path, out_path, temp_logo_path, config)

                            zip_f.write(out_path, arcname=arc_name)
                        except Exception as e:
                            st.error(f"Lỗi khi xử lý {f.name}: {e}")
                        finally:
                            # 5. Dọn dẹp file tạm ngay lập tức
                            if os.path.exists(in_path):
                                os.remove(in_path)
                            if os.path.exists(out_path):
                                os.remove(out_path)
                            gc.collect()

                        prog = (idx + 1) / total_files
                        progress_bar.progress(prog)
                        status_text.text(f"Đã xử lý: {f.name} ({idx + 1}/{total_files})")

                st.success("✅ Tất cả đã hoàn thành!")
                with open(zip_path, "rb") as zf:
                    st.download_button(
                        label="📥 Tải về File ZIP",
                        data=zf,
                        file_name="watermarked_media.zip",
                        mime="application/zip"
                    )

    finally:
        # Dọn dẹp logo tạm nếu có
        if logo_upload is not None and temp_logo_path and os.path.exists(temp_logo_path):
            os.remove(temp_logo_path)