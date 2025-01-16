

[![Python 3.9](https://img.shields.io/badge/Python-3.9-blue.svg)](https://www.python.org/downloads/release/python-390/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A containerized web scraping application built with Python.

## 🚀 Quick Start

```bash
# Build the Docker image
docker build -t web-scraper .

# Run the container
docker run web-scraper
```

## 🔧 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BASE_URL` | Base URL to start scraping from | Required |
| `SCRAPER_LANGUAGE` | Language setting for the scraper | None |

## 📦 Dependencies

The project uses the following main dependencies (see `requirements.txt` for complete list):
- Python 3.9
- Additional dependencies as specified in requirements.txt

## 🐳 Docker Configuration

The application is containerized using Docker with the following specifications:
- Base Image: `python:3.9-slim`
- Working Directory: `/app`
- System Dependencies:
  - wget
  - gnupg
  - curl
  - unzip

## 🛠️ Development

1. Clone the repository
```bash
git clone <repository-url>
```

2. Build the Docker image
```bash
docker build -t web-scraper .
```

3. Run the container
```bash
docker run web-scraper
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

