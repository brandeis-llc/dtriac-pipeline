FROM python:3

RUN apt-get update 
RUN apt-get install -y python3-pip 
RUN pip install flask elasticsearch future

ADD site /site
RUN chmod +x /site/run.sh

EXPOSE 4000/tcp
WORKDIR /site

CMD /site/run.sh
