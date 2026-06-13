import json
import boto3
import re
import uuid
from datetime import datetime, timezone
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb', region_name='eu-north-1')
table = dynamodb.Table('rowad-inquiries')
ses_client = boto3.client('ses', region_name='eu-north-1')

RATE_LIMIT = 5  # max submissions per hour per IP

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_rate_limited(ip):
    try:
        response = table.get_item(Key={'id': f'ratelimit_{ip}'})
        if 'Item' in response:
            count = response['Item'].get('count', 0)
            return count >= RATE_LIMIT
        return False
    except Exception as e:
        print("Rate limit check error:", str(e))
        return False

def update_rate_limit(ip): #This function increments the submission counter for an IP, or creates it if it doesn't exist yet.
    try:
        table.update_item(
            Key={'id': f'ratelimit_{ip}'},
            UpdateExpression='SET #count = if_not_exists(#count, :zero) + :one, expiry = :expiry', #similar to mysql syntax, if_not_exists is used to initialize the count if it doesn't exist
            ExpressionAttributeNames={'#count': 'count'},
            ExpressionAttributeValues={
                ':zero': 0,
                ':one': 1,
                ':expiry': int(datetime.now(timezone.utc).timestamp()) + 3600 #needs to connect to dynamodb ttl
            }
        )
    except Exception as e:
        print("Rate limit update error:", str(e))

def log_inquiry(inquiry_id, ip, body): #This function writes the full inquiry as a permanent record in DynamoDB.
    try:
        table.put_item(Item={
            'id': inquiry_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'ip': ip,
            'name': body.get('name'),
            'email': body.get('email'),
            'phone': body.get('phone'),
            'company': body.get('company'),
            'category': body.get('category'),
            'message': body.get('message')
        })
    except Exception as e:
        print("DynamoDB logging error:", str(e))

def lambda_handler(event, context):
    print("Event received:", json.dumps(event))

    ip = event.get('requestContext', {}).get('http', {}).get('sourceIp', 'unknown')

    try:
        body = json.loads(event['body'])
    except Exception as e:
        return {'statusCode': 400, 'body': json.dumps({'error': 'Invalid request body'})}

    # Input validation
    name = body.get('name', '').strip()
    email = body.get('email', '').strip()
    phone = body.get('phone', '').strip()
    company = body.get('company', 'Not provided').strip()
    category = body.get('category', '').strip()
    message = body.get('message', '').strip()

    if not name or not email or not category or not message:
        return {'statusCode': 400, 'body': json.dumps({'error': 'Name, email, category and message are required'})}

    if not is_valid_email(email):
        return {'statusCode': 400, 'body': json.dumps({'error': 'Invalid email format'})}

    if len(message) < 10:
        return {'statusCode': 400, 'body': json.dumps({'error': 'Message too short'})}

    # Rate limiting
    if is_rate_limited(ip):
        return {'statusCode': 429, 'body': json.dumps({'error': 'Too many requests. Please try again later.'})}

    update_rate_limit(ip)

    # Log to DynamoDB
    inquiry_id = str(uuid.uuid4())
    log_inquiry(inquiry_id, ip, body)

    # Send email
    subject = f"[ROWAD Inquiry] {category} - {name}"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="background-color: #1a2e5a; padding: 20px;">
            <h1 style="color: white;">New Inquiry - ROWAD Training Center</h1>
        </div>
        <div style="padding: 20px;">
            <p><strong>Inquiry ID:</strong> {inquiry_id}</p>
            <p><strong>Name:</strong> {name}</p>
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Phone:</strong> {phone}</p>
            <p><strong>Company:</strong> {company}</p>
            <p><strong>Category:</strong> {category}</p>
            <div style="background-color: #f5a623; padding: 15px; border-radius: 5px;">
                <p><strong>Message:</strong></p>
                <p>{message}</p>
            </div>
        </div>
    </body>
    </html>
    """

    try:
        response = ses_client.send_email(
            Source='aliferas130@gmail.com',
            Destination={'ToAddresses': ['aliferas130@gmail.com']},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {'Html': {'Data': html_body, 'Charset': 'UTF-8'}}
            },
            ReplyToAddresses=[email]
        )

        print("Email sent:", response['MessageId'])

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({'message': 'Inquiry sent successfully', 'id': inquiry_id})
        }

    except ClientError as e:
        print("SES error:", e.response['Error']['Message'])
        return {'statusCode': 500, 'body': json.dumps({'error': 'Failed to send email'})}