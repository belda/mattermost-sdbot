FROM python:3.9-slim

WORKDIR /app
RUN mkdir /app/data

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./sdbot.py" ]
