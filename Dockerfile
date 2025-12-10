FROM ubuntu:jammy-20220101

# Set environment variables
ARG TZ=America/Cuiaba
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV TZ=$TZ
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Set the working directory in the container
WORKDIR /code

# Install dependencies
COPY requirements.txt /code/

RUN apt-get update && \
    apt-get install -y python3-pip tzdata && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install pyperclip pytz && \
    playwright install chromium --with-deps

# Run the application
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8001"]
