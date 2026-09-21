FROM python:3.11-slim

WORKDIR /app
COPY infra/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY apps ./apps
COPY packages ./packages
COPY examples ./examples

CMD ["python", "apps/cli/main.py"]
