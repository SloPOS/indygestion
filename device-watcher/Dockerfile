FROM python:3.12-slim

# NOTE:
# This container needs host device/event access to detect and mount USB/SD devices.
# Typical runtime flags:
#   --privileged
#   -v /run/udev:/run/udev:ro
#   -v /dev:/dev

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    rsync \
    exfat-fuse \
    exfatprogs \
    ntfs-3g \
    hfsplus \
    hfsprogs \
    udev \
    util-linux \
    dosfstools \
    e2fsprogs \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY udev ./udev

EXPOSE 8100

CMD ["python", "-m", "app.main"]
