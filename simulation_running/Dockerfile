FROM public.ecr.aws/lambda/python:3.9

# Install system dependencies required for building psutil
RUN yum update -y && \
    yum install -y gcc python3-devel && \
    yum clean all

COPY requirements.txt /tmp/

# Install Python dependencies for function
RUN pip install --upgrade pip -q
RUN pip install -r /tmp/requirements.txt -q

COPY lambda_function.py helper.py model.py /var/task/
CMD [ "lambda_function.lambda_handler" ] 
