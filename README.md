# Rowad Serverless Inquiry System

A serverless email inquiry backend built on AWS, developed during my internship at Rowad Training Center (RAK, UAE).

## The Problem

The existing contact form used Node.js and nodemailer with SMTP credentials stored in environment variables. This created a security risk: exposed credentials could allow unauthorized use of the mail server. Additionally, there was no persistent record of inquiries and no protection against form abuse.

## The Solution

A fully serverless backend using AWS services that eliminates credential storage entirely. IAM roles handle all permissions. Every inquiry is logged permanently. Rate limiting prevents abuse.

## Architecture

**API Gateway** receives POST requests from the contact form and triggers the Lambda function.

**AWS Lambda** (Python 3.12) handles validation, rate limiting, logging, and email sending.

**AWS SES** sends branded HTML emails without storing any SMTP credentials.

**AWS DynamoDB** stores every inquiry permanently and tracks rate limit counters per IP with automatic TTL expiry.

## Project Context

This was built as a personal learning project during my internship at Rowad Training Center. 
The existing system used nodemailer with SMTP credentials, which I identified as a security 
weakness. I designed and built this AWS alternative to learn serverless architecture hands-on 
and to demonstrate how the backend could be improved.

The system is fully functional and tested but was not deployed to production, as that would 
require Rowad to maintain an AWS account after the internship ended.

## Security Decisions

**No stored credentials:** SES sends emails via IAM role permissions attached to the Lambda 
function. No passwords or API keys anywhere in the code.

**Least privilege IAM:** The Lambda execution role has only AmazonSESFullAccess and 
AWSLambdaBasicExecutionRole. It cannot access any other AWS service.

**Input validation:** All fields are validated before touching any AWS service. Invalid 
requests are rejected at the Lambda level with appropriate HTTP status codes.

**Rate limiting:** Submissions are tracked per IP in DynamoDB with a limit of 5 per hour. 
Records expire automatically via DynamoDB TTL.

## Known Limitations

- Rate limiting is IP based and can be bypassed with a VPN
- Emails may land in spam without domain verification and SPF/DKIM records
- SES account is in sandbox mode, meaning only verified email addresses can receive emails
- Stockholm region was used instead of UAE region due to activation delays during development

## Tech Stack

- AWS Lambda (Python 3.12)
- AWS API Gateway (HTTP API)
- AWS SES
- AWS DynamoDB
- boto3

## What I Learned

- Serverless architecture and how Lambda, API Gateway, SES, and DynamoDB connect
- IAM roles and least privilege access control
- NoSQL data modeling with single table design for mixed record types
- DynamoDB TTL for automatic record expiry
- HTTP status codes and REST API design
- Why credential storage in environment variables is a security risk and how to eliminate it