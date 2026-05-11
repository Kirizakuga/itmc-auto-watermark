FROM python:3.11-slim

# Thiết lập thư mục làm việc bên trong container
WORKDIR /app

# Cài đặt ffmpeg và các gói cần thiết
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy file requirements vào trước để tận dụng bộ nhớ đệm (cache) của Docker
COPY requirements.txt .

# Cài đặt các thư viện Python (Streamlit)
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code và logo vào trong container
COPY test.py .
COPY logo-01.png .

# Mở port 8501 để Streamlit giao tiếp với bên ngoài
EXPOSE 8501

# Lệnh khởi chạy tool khi container được bật lên
CMD ["streamlit", "run", "test.py", "--server.port=8501", "--server.address=0.0.0.0"]