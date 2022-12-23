FROM python:3.7-slim

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --upgrade pip

RUN pip3 install -r requirements.txt --no-cache-dir

COPY . .

CMD ["waitress-serve", "foodgram.wsgi:application", "--listen", "=*:8000" ] 
