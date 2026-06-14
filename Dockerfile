FROM public.ecr.aws/lambda/python:3.8

COPY requirements.txt ./
RUN pip install -r requirements.txt -t .

COPY lambda_function.py ./
COPY db.py ./
COPY config.py ./
COPY scrapers/ ./scrapers/

CMD ["lambda_function.lambda_handler"]