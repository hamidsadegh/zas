# ================================
# ZAS Dockerfile
# ================================
FROM registry.access.redhat.com/ubi8/python-311

# Prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /code

# Temporarily switch to root to install packages
USER root

# Install system dependencies needed for mysqlclient
RUN yum install -y \
    gcc \
    python3-devel \
    mariadb-connector-c-devel \
    pkgconf-pkg-config \
    cronie \
    && yum clean all

# Ensure directories exist
RUN mkdir -p /code/logs /code/celerybeat /code/staticfiles && chown -R 1001:0 /code/celerybeat /code/staticfiles

# Switch back to the default non-root user provided by the base image
USER 1001

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy full project
COPY . .

# Copy and execute entrypoint script
COPY entrypoint.sh /entrypoint.sh
USER root
RUN chmod +x /entrypoint.sh
USER 1001
CMD ["/entrypoint.sh"]