FROM ubuntu:20.04

# Set timezone to avoid tzdata interactive prompt
ENV TZ=America/New_York
RUN ln -fs /usr/share/zoneinfo/$TZ /etc/localtime

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    # Dependencies for installing Selenium
    curl \
    apt-utils \
    build-essential \
    unzip \
    wget

# Dependencies to unpack google-chrome.deb
RUN apt-get install -y libgconf-2-4 \
    libnss3 \
    libxss1 \
    dialog \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libdrm2 \
    libgbm1 \
    libx11-xcb1 \
    xdg-utils

# Update SSL Certificates for HTTPS requests
RUN apt-get install -y ca-certificates

# Install ChromeDriver for Selenium
RUN CHROMEDRIVER_VERSION=`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE` && \
    wget https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip
RUN unzip chromedriver_linux64.zip -d /usr/bin
RUN chmod +x /usr/bin/chromedriver

# Install Chrome for Selenium
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN dpkg -i google-chrome*.deb
RUN apt-get install -y -f