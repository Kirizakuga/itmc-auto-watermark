
FROM python:3.11-alpine

# Thiết lập thư mục làm việc bên trong container
WORKDIR /app

# Cài đặt các gói thư viện lõi của Linux để build được Pillow và Streamlit trên Alpine
# Không có mấy cái gcc, jpeg-dev này là lúc cài Pillow sẽ báo lỗi tung tóe
RUN apk add --no-cache \
    gcc \
    musl-dev \
    jpeg-dev \
    zlib-dev \
    libffi-dev \
    g++ \
    linux-headers

# Copy file requirements vào trước để tận dụng bộ nhớ đệm (cache) của Docker, giúp build nhanh hơn ở các lần sau
COPY requirements.txt .

# Cài đặt các thư viện Python (Streamlit, Pillow)
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code và logo vào trong container
COPY test.py .
COPY logo-01.png .

# Mở port 8501 để Streamlit giao tiếp với bên ngoài
EXPOSE 8501

# Lệnh khởi chạy tool khi container được bật lên
CMD ["streamlit", "run", "test.py", "--server.port=8501", "--server.address=0.0.0.0"]