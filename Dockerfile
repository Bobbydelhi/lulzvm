FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    qemu-system-x86 qemu-utils lxc bridge-utils iproute2 ovmf procps curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create necessary directories
RUN mkdir -p /etc/lulzvm /run/lulzvm /var/log/lulzvm /var/lib/lulzvm/images /var/lib/lxc

EXPOSE 8006

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8006"]
