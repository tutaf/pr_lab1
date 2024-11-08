FROM python:3.11.6-slim

# set the working directory
WORKDIR /app

COPY requirements.txt wait-for-it.sh ./

# install the dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    chmod +x wait-for-it.sh

# copy the application code
COPY . .

ENV FLASK_APP=lab2.py
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# expose the port for the flask app
EXPOSE 5000
EXPOSE 5001

CMD ["./wait-for-it.sh", "db:5432", "--", "python", "lab2.py"]
