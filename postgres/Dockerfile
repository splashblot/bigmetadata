# No explicit tag for 9.5-2.2 yet, but that's what we use
FROM kartoza/postgis:latest

RUN apt-get update --fix-missing
RUN apt-get install -yq make wget build-essential postgresql-server-dev-9.5 \
                             libxml2-dev libgdal-dev libproj-dev libjson0-dev \
                             ruby python-pip postgresql-9.5-plproxy \
                             postgresql-plpython-9.5 python2.7-dev

RUN wget http://download.osgeo.org/geos/geos-3.6.1.tar.bz2 && \
    tar xjpf geos-3.6.1.tar.bz2 && \
    cd geos-3.6.1 && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    rm -rf ../geos-3.6.1*

RUN apt-get install -yq libprotoc-dev libprotobuf-dev protobuf-compiler \
                        automake autoconf libtool git

RUN export PKG_CONFIG_PATH=/usr/lib/x86_64-linux-gnu/pkgconfig/ && \
    git clone https://github.com/protobuf-c/protobuf-c.git && \
    cd protobuf-c && \
    ./autogen.sh && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    rm -rf ../protobuf-c

RUN export PKG_CONFIG_PATH=/usr/lib/x86_64-linux-gnu/pkgconfig/ && \
    wget http://postgis.net/stuff/postgis-2.4.0dev.tar.gz && \
    tar xzf postgis-2.4.0dev.tar.gz && \
    cd postgis-2.4.0dev && \
    ./configure --prefix=/usr --with-protobufdir=/usr/lib/x86_64-linux-gnu/ && \
    make &&  \
    make install && \
    rm -rf ../postgis-2.4.0*
