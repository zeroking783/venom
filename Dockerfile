FROM python:latest

WORKDIR /home/master_node

COPY requirements.txt .

RUN python -m venv .venv \
    && . .venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -r requirements.txt

COPY master_node.py .

CMD ["/home/master_node/.venv/bin/python", "master_node.py"]