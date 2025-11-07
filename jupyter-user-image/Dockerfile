FROM jupyter/scipy-notebook:python-3.11

USER root
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

USER jovyan

RUN pip install --no-cache-dir \
    pandas==2.1.3 \
    numpy==1.26.2 \
    matplotlib==3.8.2 \
    seaborn==0.13.0 \
    psycopg2-binary==2.9.9 \
    sqlalchemy==2.0.23

COPY --chown=jovyan:users shaparak_db_proxy.py /opt/conda/lib/python3.11/site-packages/
COPY --chown=jovyan:users ipython_config.py /home/jovyan/.ipython/profile_default/
RUN mkdir -p /home/jovyan/.ipython/extensions
COPY --chown=jovyan:users shaparak_audit_logger.py /home/jovyan/.ipython/extensions/
COPY --chown=jovyan:users shaparak_export_blocker.py /opt/conda/lib/python3.11/site-packages/

USER root
RUN mv /opt/conda/bin/pip /opt/conda/bin/pip.disabled && \
    echo '#!/bin/bash\necho "❌ نصب پکیج مجاز نیست!"\nexit 1' > /opt/conda/bin/pip && \
    chmod +x /opt/conda/bin/pip

# Block network download tools
RUN mv /usr/bin/curl /usr/bin/curl.disabled 2>/dev/null || true && \
    echo '#!/bin/bash\necho "❌ دسترسی به اینترنت مجاز نیست!"\nexit 1' > /usr/bin/curl && \
    chmod +x /usr/bin/curl && \
    mv /usr/bin/wget /usr/bin/wget.disabled 2>/dev/null || true && \
    echo '#!/bin/bash\necho "❌ دسترسی به اینترنت مجاز نیست!"\nexit 1' > /usr/bin/wget && \
    chmod +x /usr/bin/wget

USER jovyan

RUN mkdir -p /home/jovyan/.ipython/profile_default/startup && \
    echo 'print("محیط شاپرک - تمام کدها ثبت می شوند")' > /home/jovyan/.ipython/profile_default/startup/00-welcome.py