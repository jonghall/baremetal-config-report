FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

COPY . .

CMD gunicorn -w 4 -b 0.0.0.0:5000 baremetal-config-report:app
