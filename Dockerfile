FROM python:3.9-slim

# Set environment variables to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive \
    DEBCONF_NONINTERACTIVE_SEEN=true \
    TZ=UTC

# Install system dependencies for the tools
# Note: Many bug bounty tools are Go-based or require specific binaries.
# We will install some common ones, but for a full setup, we might need to copy binaries 
# or install Go. For this basic version, we assume python dependencies + basic tools.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    git \
    unzip \
    build-essential \
    libpcap-dev \
    gcc \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Go (needed for subfinder, httpx, etc. if we install them from source)
# Or we can download pre-built binaries. 
# For simplicity, let's assume the user will mount their tools or we install a few key ones.
# Here is a basic setup installing tools from ProjectDiscovery (example)
RUN go_version=1.21.5 && \
    wget https://go.dev/dl/go$go_version.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go$go_version.linux-amd64.tar.gz && \
    rm go$go_version.linux-amd64.tar.gz

ENV PATH=$PATH:/usr/local/go/bin:/root/go/bin
ENV CGO_ENABLED=1

# Install Subfinder, HTTPX, Naabu, Katana, Nuclei, GAU
RUN go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
RUN go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
# Naabu installation - may fail on some systems, so we make it optional
RUN go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest || echo "Naabu installation failed, skipping..."
RUN go install -v github.com/projectdiscovery/katana/cmd/katana@latest
RUN go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
RUN go install -v github.com/lc/gau/v2/cmd/gau@latest
RUN go install -v github.com/owasp-amass/amass/v4/...@master

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose the port
EXPOSE 5050

# Run the application with gunicorn for production
# --bind 0.0.0.0:5050 - Listen on all interfaces on port 5050
# --workers 2 - Use 2 worker processes
# --timeout 120 - Set timeout to 120 seconds for long-running scans
# --access-logfile - - Log access to stdout
CMD ["gunicorn", "--bind", "0.0.0.0:5050", "--workers", "2", "--timeout", "120", "--access-logfile", "-", "app:app"]
