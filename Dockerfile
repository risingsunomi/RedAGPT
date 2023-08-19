FROM python:3.8

WORKDIR /app

RUN wget -O /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.5/dumb-init_1.2.5_x86_64
RUN chmod +x /usr/local/bin/dumb-init


# Copy the requirements.txt file to the container
COPY requirements.txt .

# Install the required packages
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r unpinned_requirements.txt

# Copy the rest of your application code to the container
COPY . .

RUN chmod +x .venv/bin/activate
RUN .venv/bin/activate

# Set the entry point for your application
ENTRYPOINT ["/usr/local/bin/dumb-init", "--"]
CMD ["dumb-init", "python", "main.py" ]