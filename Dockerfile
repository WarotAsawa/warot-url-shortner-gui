FROM python:3.9-slim
    
WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    xclip \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip3 install -r requirements.txt

COPY . .

EXPOSE 80

ENTRYPOINT ["streamlit", "run", "shortener-gui.py", "--server.port=80", "--server.address=0.0.0.0"]
