# Dockerfile for vlan converter
FROM python:3.12
WORKDIR /opt/vlan_converter
COPY requirements.txt ./
COPY vlan_converter.py ./
RUN pip install -r requirements.txt
CMD ["python", "./vlan_converter.py"]
EXPOSE 5000/tcp 
