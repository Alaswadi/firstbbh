FROM python:3.9-slim

# Install system dependencies for the tools
# Note: Many bug bounty tools are Go-based or require specific binaries.
# We will install some common ones, but for a full setup, we might need to copy binaries 
# or install Go. For this basic version, we assume python dependencies + basic tools.
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Go (needed for subfinder, httpx, etc. if we install them from source)
# Or we can download pre-built binaries. 
# For simplicity, let's assume the user will mount their tools or we install a few key ones.
# Here is a basic setup installing tools from ProjectDiscovery (example)
RUN go_version=1.21.0 && \
    wget https://go.dev/dl/go$go_version.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go$go_version.linux-amd64.tar.gz && \
    rm go$go_version.linux-amd64.tar.gz

ENV PATH=$PATH:/usr/local/go/bin:/root/go/bin

# Install Subfinder, HTTPX, Naabu, Katana, Nuclei, GAU
RUN go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
RUN go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
RUN go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
RUN go install -v github.com/projectdiscovery/katana/cmd/katana@latest
RUN go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest
RUN go install -v github.com/lc/gau/v2/cmd/gau@latest
RUN go install -v github.com/owasp-amass/amass/v3/...@master

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose the port
EXPOSE 5050

# Run the application
CMD ["python", "app.py"]
