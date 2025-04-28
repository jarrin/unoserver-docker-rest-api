FROM --platform=$BUILDPLATFORM eclipse-temurin:24_36-jdk-alpine

ARG BUILD_CONTEXT="build-context"

ARG UID=worker
ARG GID=worker
# renovate: pypi: unoserver
ARG VERSION_UNOSERVER=3.2

ARG ADD_REST_API=false

LABEL org.opencontainers.image.title="unoserver-docker"
LABEL org.opencontainers.image.description="Container image that contains unoserver and libreoffice including large set of fonts for file format conversions"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.documentation="https://github.com/unoconv/unoserver-docker/blob/main/README.adoc"
LABEL org.opencontainers.image.source="https://github.com/unoconv/unoserver-docker"
LABEL org.opencontainers.image.url="https://github.com/unoconv/unoserver-docker"

WORKDIR /

RUN addgroup -S ${GID} && adduser -S ${UID} -G ${GID}

RUN apk add --no-cache \
    bash curl \
    py3-pip \
    libreoffice \
    supervisor

# fonts - https://wiki.alpinelinux.org/wiki/Fonts
RUN apk add --no-cache \
    font-noto font-noto-cjk font-noto-extra \
    terminus-font \
    ttf-font-awesome \
    ttf-dejavu \
    ttf-freefont \
    ttf-hack \
    ttf-inconsolata \
    ttf-liberation \
    ttf-mononoki  \
    ttf-opensans   \
    fontconfig && \
    fc-cache -f

RUN rm -rf /var/cache/apk/* /tmp/*

# https://github.com/unoconv/unoserver/
RUN pip install --break-system-packages -U unoserver==${VERSION_UNOSERVER}

# setup supervisor
COPY --chown=${UID}:${GID} ${BUILD_CONTEXT} /
RUN chmod +x entrypoint.sh && \
    #    mkdir -p /var/log/supervisor && \
    #    chown ${UID}:${GID} /var/log/supervisor && \
    #    mkdir -p /var/run && \
    chown -R ${UID}:0 /run && \
    chmod -R g=u /run

RUN if [ "true" = "$ADD_REST_API" ] ; then  pip install --break-system-packages -U flask gunicorn ; else echo "remove" && rm -rf /rest-service ; fi
ENV START_REST_API=${ADD_REST_API}

USER ${UID}
WORKDIR /home/worker
ENV HOME="/home/worker"

VOLUME ["/data"]
EXPOSE 2003
ENTRYPOINT ["/entrypoint.sh"]
