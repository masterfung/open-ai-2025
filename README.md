# mighty-openai-new-york-tech-week-hackathon

## Introduction

Today's AI agents are wonderful, it can do a lot of things but right now it is having a hard time doing is doing tasks that require private data. We want to demo how we can give private data, identity, and authentication to an agent without losing security, compliance, and control. We are building on top of [Mighty](https://mightynetwork.ai/) and using our [SDK](https://pypi.org/project/mighty-sdk-core/) to handle the security complexity.

## Technical Tooling
We are using the following toolings:
- Personhood service is using World ID
- Mighty SDK
- Mighty Web Secure Data Vault Account (anyone can sign up for a secure data vault)
- Python Chainlit

## Get Started

Make sure you have Python 3.12+ or higher version running. 

### Add the environment variables through `.env` file
- Create a new `.env` file based on the `.env.example` file
- Fill in the data for those variables (Open AI key)

### Install dependencies

```bash
poetry install --no-root
```

### Start the ChainLit application

```bash
poetry run chainlit run chainlit_main.py
```
