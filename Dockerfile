FROM thelabdc/python-ubuntu

# Install LaTeX

RUN apt-get update && apt-get install -y \
    texlive-fonts-extra \
    texlive-fonts-recommended \
    texlive-generic-recommended \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-xetex

# Install MS ODBC Drivers
ENV ACCEPT_EULA=Y
RUN apt-get update && apt-get install -y apt-transport-https curl && \
    apt-get install -y libc6 libstdc++6 && \
    sh -c 'curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -' && \
    sh -c 'curl https://packages.microsoft.com/config/ubuntu/16.04/prod.list > /etc/apt/sources.list.d/mssql-release.list' && \
    apt-get update && \
    apt-get install -y msodbcsql mssql-tools unixodbc-dev && \
    rm -rf /var/lib/apt/lists/*

COPY . /suso/
WORKDIR /suso

RUN pip install -r requirements.txt && pip install -e .
