FROM jupyterhub/jupyterhub:4.0

USER root

RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    dockerspawner==12.1.0 \
    psycopg2-binary==2.9.9 \
    sqlalchemy==2.0.23 \
    bcrypt==4.1.2 \
    python-jose[cryptography]==3.3.0

# Set working directory first
WORKDIR /srv/jupyterhub

# Cache buster - change this number to force rebuild
ARG CACHEBUST=1000

# Copy files (relative to build context which is ./jupyterhub/)
COPY jupyterhub_config.py /srv/jupyterhub/
COPY custom_authenticator.py /srv/jupyterhub/
COPY templates/ /srv/jupyterhub/templates/

CMD ["jupyterhub", "-f", "/srv/jupyterhub/jupyterhub_config.py"]
