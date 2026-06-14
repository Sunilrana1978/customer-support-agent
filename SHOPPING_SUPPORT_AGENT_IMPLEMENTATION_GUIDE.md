# AWS Bedrock Shopping Support Agent - Implementation Guide

**Spec-Driven Development Approach**

---

## Executive Summary

Build a **Customer Support Agent for E-Commerce** (like Amazon) using AWS Bedrock Agents that:
- Leverages **Memory** (DynamoDB) to remember customer history and conversation context
- Uses **Identity** (IAM/Cognito) to personalize responses based on customer profile
- Exposes via **Agent Gateway** (API Gateway) for web, mobile, Slack integration
- Implements **Evaluation** (CloudWatch metrics) to track performance and ROI

**Key Capabilities:**
- Check order status and tracking information
- Process refunds and returns
- Update shipping addresses
- Provide VIP customer prioritization
- Multi-channel access (web chat, Slack, SMS, mobile)
- Conversation memory for context awareness

**Technology Stack:**
- AWS Bedrock (Claude model)
- DynamoDB (memory & customer data)
- Lambda (tool execution)
- API Gateway (HTTP endpoint)
- CloudWatch (evaluation & monitoring)
- Python 3.11+

---

## Phase 1: Foundation & Setup (Days 1-3)

### Spec 1.1: AWS Account & Permissions

**Objective:** Set up AWS environment with proper IAM roles and permissions

**Acceptance Criteria:**
- [ ] AWS account has Bedrock access enabled
- [ ] Bedrock Agent creation IAM role created
- [ ] Lambda execution role with DynamoDB/CloudWatch permissions
- [ ] API Gateway service role configured
- [ ] All roles follow principle of least privilege

**Implementation:**

```bash
# Create IAM roles
aws iam create-role --role-name bedrock-agent-execution \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "bedrock.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam attach-role-policy --role-name bedrock-agent-execution \
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

aws iam attach-role-policy --role-name bedrock-agent-execution \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess

# Create Lambda execution role
aws iam create-role --role-name lambda-shopping-tools \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam attach-role-policy --role-name lambda-shopping-tools \
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
```

**Definition of Done:**
- [ ] Roles created and verified via AWS Console
- [ ] Permissions tested (can create Bedrock agent, Lambda)
- [ ] Documentation with role ARNs saved

---

### Spec 1.2: Project Structure & Repository

**Objective:** Organize codebase for maintainability and testing

**Acceptance Criteria:**
- [ ] Git repository initialized
- [ ] Directory structure follows Python best practices
- [ ] README with setup instructions
- [ ] Requirements.txt with dependencies pinned
- [ ] .gitignore configured

**Directory Structure:**

```
shopping-support-agent/
├── README.md
├── requirements.txt
├── .gitignore
├── setup.py
│
├── infrastructure/
│   ├── dynamodb_tables.py      # DynamoDB schema specs
│   ├── cloudformation.yaml     # IaC template
│   └── iam_roles.py            # IAM role definitions
│
├── src/
│   ├── __init__.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── client.py           # Main agent class
│   │   └── config.py           # Agent configuration
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── customer_tools.py   # Customer profile tool
│   │   ├── order_tools.py      # Order management tools
│   │   ├── refund_tools.py     # Refund processing tools
│   │   └── shipping_tools.py   # Shipping/tracking tools
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── customer.py         # Customer data model
│   │   ├── order.py            # Order data model
│   │   └── session.py          # Session memory model
│   │
│   ├── evaluations/
│   │   ├── __init__.py
│   │   ├── metrics.py          # Metric collection
│   │   └── analytics.py        # Performance analysis
│   │
│   └── integrations/
│       ├── __init__.py
│       ├── dynamodb.py         # DynamoDB client
│       └── bedrock.py          # Bedrock API wrapper
│
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_customer_tools.py
│   │   ├── test_order_tools.py
│   │   └── test_refund_tools.py
│   ├── integration/
│   │   ├── test_agent_flow.py
│   │   └── test_dynamodb.py
│   └── e2e/
│       └── test_full_conversation.py
│
├── deployment/
│   ├── deploy.sh
│   ├── lambda_package.sh
│   └── cleanup.sh
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API_SPEC.md
│   ├── DEVELOPMENT.md
│   └── TROUBLESHOOTING.md
│
└── examples/
    ├── customer_scenarios.py
    └── sample_interactions.md
```

**Implementation:**

```bash
git init shopping-support-agent
cd shopping-support-agent

# Create directories
mkdir -p infrastructure src/agent src/tools src/models src/evaluations src/integrations
mkdir -p tests/unit tests/integration tests/e2e
mkdir -p deployment docs examples

# Create requirements.txt
cat > requirements.txt << 'EOF'
boto3==1.34.0
botocore==1.34.0
pydantic==2.5.0
python-dotenv==1.0.0
pytest==7.4.3
pytest-cov==4.1.0
pytest-asyncio==0.21.1
moto==4.2.0
UUID==1.30
EOF

# Create setup.py
cat > setup.py << 'EOF'
from setuptools import setup, find_packages

setup(
    name="shopping-support-agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "boto3>=1.34.0",
        "pydantic>=2.5.0",
        "python-dotenv>=1.0.0",
    ],
    python_requires=">=3.11",
)
EOF

git add .
git commit -m "Initialize project structure"
```

**Definition of Done:**
- [ ] Repository created with proper structure
- [ ] All requirements pinned to specific versions
- [ ] README explains setup process
- [ ] First commit merged to main

---

## Phase 2: Data Layer (Days 4-6)

### Spec 2.1: DynamoDB Schema

**Objective:** Define and implement database schema for customer, order, and session data

**Acceptance Criteria:**
- [ ] All 4 DynamoDB tables created with proper keys
- [ ] TTL configured for session cleanup
- [ ] GSI created for common queries
- [ ] Tables in production-ready state (PAY_PER_REQUEST)
- [ ] Backup strategy documented

**Tables to Create:**

1. **shopping-customers**
   - PK: customer_id
   - Attributes: name, email, vip_status, lifetime_spent, created_at, preferred_contact
   - GSI: email-index

2. **shopping-orders**
   - PK: customer_id (HASH), order_id (RANGE)
   - Attributes: order_date, status, items, total_amount, shipping_address, tracking_number
   - GSI: date-index (for recent orders)

3. **shopping-returns**
   - PK: return_id
   - Attributes: order_id, reason, amount, status, created_at
   - GSI: order-index
   - TTL: 90 days

4. **shopping-agent-sessions**
   - PK: session_id (HASH), timestamp (RANGE)
   - Attributes: customer_id, conversation, metadata
   - TTL: 90 days

**Implementation:**

```python
# infrastructure/dynamodb_tables.py

import boto3
from typing import Dict

dynamodb = boto3.resource('dynamodb')

class DynamoDBSetup:
    
    @staticmethod
    def create_customers_table() -> Dict:
        """Create customers table"""
        table = dynamodb.create_table(
            TableName='shopping-customers',
            KeySchema=[
                {'AttributeName': 'customer_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'customer_id', 'AttributeType': 'S'},
                {'AttributeName': 'email', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[{
                'IndexName': 'email-index',
                'KeySchema': [{'AttributeName': 'email', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
                'BillingMode': 'PAY_PER_REQUEST'
            }],
            BillingMode='PAY_PER_REQUEST'
        )
        table.wait_until_exists()
        return {'table_name': 'shopping-customers', 'status': 'created'}
    
    @staticmethod
    def create_orders_table() -> Dict:
        """Create orders table"""
        table = dynamodb.create_table(
            TableName='shopping-orders',
            KeySchema=[
                {'AttributeName': 'customer_id', 'KeyType': 'HASH'},
                {'AttributeName': 'order_id', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'customer_id', 'AttributeType': 'S'},
                {'AttributeName': 'order_id', 'AttributeType': 'S'},
                {'AttributeName': 'order_date', 'AttributeType': 'N'}
            ],
            GlobalSecondaryIndexes=[{
                'IndexName': 'date-index',
                'KeySchema': [
                    {'AttributeName': 'customer_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'order_date', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
                'BillingMode': 'PAY_PER_REQUEST'
            }],
            BillingMode='PAY_PER_REQUEST'
        )
        table.wait_until_exists()
        return {'table_name': 'shopping-orders', 'status': 'created'}
    
    @staticmethod
    def create_returns_table() -> Dict:
        """Create returns table"""
        table = dynamodb.create_table(
            TableName='shopping-returns',
            KeySchema=[
                {'AttributeName': 'return_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'return_id', 'AttributeType': 'S'},
                {'AttributeName': 'order_id', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[{
                'IndexName': 'order-index',
                'KeySchema': [{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
                'BillingMode': 'PAY_PER_REQUEST'
            }],
            BillingMode='PAY_PER_REQUEST'
        )
        # Enable TTL
        table.meta.client.update_time_to_live(
            TableName='shopping-returns',
            TimeToLiveSpecification={'AttributeName': 'ttl', 'Enabled': True}
        )
        table.wait_until_exists()
        return {'table_name': 'shopping-returns', 'status': 'created'}
    
    @staticmethod
    def create_sessions_table() -> Dict:
        """Create agent sessions table"""
        table = dynamodb.create_table(
            TableName='shopping-agent-sessions',
            KeySchema=[
                {'AttributeName': 'session_id', 'KeyType': 'HASH'},
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'session_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'N'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        # Enable TTL
        table.meta.client.update_time_to_live(
            TableName='shopping-agent-sessions',
            TimeToLiveSpecification={'AttributeName': 'ttl', 'Enabled': True}
        )
        table.wait_until_exists()
        return {'table_name': 'shopping-agent-sessions', 'status': 'created'}
    
    @staticmethod
    def setup_all() -> Dict:
        """Create all tables"""
        results = {
            'customers': DynamoDBSetup.create_customers_table(),
            'orders': DynamoDBSetup.create_orders_table(),
            'returns': DynamoDBSetup.create_returns_table(),
            'sessions': DynamoDBSetup.create_sessions_table(),
        }
        return results

if __name__ == '__main__':
    results = DynamoDBSetup.setup_all()
    for table, result in results.items():
        print(f"✅ {result['table_name']}: {result['status']}")
```

**Test Spec 2.1:**

```python
# tests/integration/test_dynamodb.py

import pytest
import boto3
from moto import mock_dynamodb

@mock_dynamodb
def test_create_customers_table():
    """Test customers table creation"""
    from infrastructure.dynamodb_tables import DynamoDBSetup
    
    result = DynamoDBSetup.create_customers_table()
    assert result['table_name'] == 'shopping-customers'
    assert result['status'] == 'created'
    
    # Verify table exists
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('shopping-customers')
    assert table.table_status == 'ACTIVE'

@mock_dynamodb
def test_create_orders_table():
    """Test orders table creation"""
    from infrastructure.dynamodb_tables import DynamoDBSetup
    
    result = DynamoDBSetup.create_orders_table()
    assert result['table_name'] == 'shopping-orders'
    
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('shopping-orders')
    assert table.table_status == 'ACTIVE'
    assert len(table.global_secondary_indexes) == 1
```

**Definition of Done:**
- [ ] All 4 tables created successfully
- [ ] TTL configured for sessions and returns
- [ ] GSI tested and queryable
- [ ] Backup enabled
- [ ] Cost estimate documented

---

### Spec 2.2: Data Models (Pydantic)

**Objective:** Define type-safe data models using Pydantic

**Acceptance Criteria:**
- [ ] Customer model with validation
- [ ] Order model with status enum
- [ ] Return model with reason enum
- [ ] Session model for memory
- [ ] All models have serialization methods
- [ ] Unit tests for all models

**Implementation:**

```python
# src/models/customer.py

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class VIPStatus(str, Enum):
    REGULAR = "Regular"
    SILVER = "Silver"
    GOLD = "Gold"
    PLATINUM = "Platinum"

class ContactPreference(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PHONE = "phone"

class Customer(BaseModel):
    customer_id: str = Field(..., description="Unique customer ID")
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    vip_status: VIPStatus = VIPStatus.REGULAR
    lifetime_spent: float = Field(default=0, ge=0)
    total_orders: int = Field(default=0, ge=0)
    return_rate: float = Field(default=0, ge=0, le=100)
    preferred_contact: ContactPreference = ContactPreference.EMAIL
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    def to_dynamo(self) -> dict:
        """Convert to DynamoDB format"""
        data = self.dict()
        data['created_at'] = int(self.created_at.timestamp())
        if self.updated_at:
            data['updated_at'] = int(self.updated_at.timestamp())
        return data
    
    @classmethod
    def from_dynamo(cls, data: dict) -> 'Customer':
        """Convert from DynamoDB format"""
        if 'created_at' in data and isinstance(data['created_at'], (int, float)):
            data['created_at'] = datetime.fromtimestamp(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], (int, float)):
            data['updated_at'] = datetime.fromtimestamp(data['updated_at'])
        return cls(**data)

# src/models/order.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    SHIPPED = "Shipped"
    IN_TRANSIT = "In Transit"
    OUT_FOR_DELIVERY = "Out for Delivery"
    DELIVERED = "Delivered"
    CANCELLED = "Cancelled"

class OrderItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int = Field(gt=0)
    price: float = Field(gt=0)

class Order(BaseModel):
    order_id: str
    customer_id: str
    order_date: datetime
    status: OrderStatus = OrderStatus.PENDING
    items: List[OrderItem]
    total_amount: float = Field(gt=0)
    shipping_address: dict = Field(...)
    tracking_number: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    
    def to_dynamo(self) -> dict:
        """Convert to DynamoDB format"""
        data = self.dict()
        data['order_date'] = int(self.order_date.timestamp())
        if self.estimated_delivery:
            data['estimated_delivery'] = int(self.estimated_delivery.timestamp())
        data['items'] = [item.dict() for item in self.items]
        return data

# src/models/session.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Optional

class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str
    type: str = Field(default="text")
    timestamp: datetime = Field(default_factory=datetime.now)
    tools_used: Optional[List[str]] = None

class Session(BaseModel):
    session_id: str
    customer_id: str
    messages: List[Message] = []
    metadata: Dict = {}
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def to_dynamo(self) -> dict:
        """Convert to DynamoDB format"""
        return {
            'session_id': self.session_id,
            'customer_id': self.customer_id,
            'timestamp': int(datetime.now().timestamp()),
            'conversation': [msg.dict() for msg in self.messages],
            'metadata': self.metadata,
            'ttl': int((datetime.now().timestamp())) + (90 * 24 * 3600)
        }
```

**Test Spec 2.2:**

```python
# tests/unit/test_models.py

import pytest
from datetime import datetime
from src.models.customer import Customer, VIPStatus
from src.models.order import Order, OrderStatus, OrderItem

def test_customer_creation():
    """Test customer model creation"""
    customer = Customer(
        customer_id="cust-123",
        name="John Doe",
        email="john@example.com",
        vip_status=VIPStatus.GOLD
    )
    assert customer.customer_id == "cust-123"
    assert customer.vip_status == VIPStatus.GOLD

def test_customer_serialization():
    """Test customer to/from DynamoDB"""
    original = Customer(
        customer_id="cust-123",
        name="John Doe",
        email="john@example.com"
    )
    dynamo_data = original.to_dynamo()
    restored = Customer.from_dynamo(dynamo_data)
    assert restored.customer_id == original.customer_id

def test_order_creation():
    """Test order model creation"""
    order = Order(
        order_id="ord-456",
        customer_id="cust-123",
        order_date=datetime.now(),
        items=[OrderItem(product_id="prod-1", product_name="Laptop", quantity=1, price=999.99)],
        total_amount=999.99,
        shipping_address={"street": "123 Main St", "city": "NYC"}
    )
    assert order.order_id == "ord-456"
    assert len(order.items) == 1
```

**Definition of Done:**
- [ ] All 4 Pydantic models implemented
- [ ] Serialization/deserialization methods work
- [ ] Unit tests pass (100% coverage)
- [ ] Type hints complete
- [ ] Documentation in docstrings

---

## Phase 3: Tool Implementation (Days 7-9)

### Spec 3.1: Customer Tools

**Objective:** Implement Lambda functions to retrieve customer data

**Acceptance Criteria:**
- [ ] get_customer_profile returns complete profile
- [ ] Validates customer exists before returning
- [ ] Returns VIP status and lifetime value
- [ ] Unit tests with mocked DynamoDB
- [ ] Lambda deployment package working

**Implementation:**

```python
# src/tools/customer_tools.py

import boto3
from typing import Dict
from datetime import datetime
from src.models.customer import Customer

dynamodb = boto3.resource('dynamodb')
customers_table = dynamodb.Table('shopping-customers')

class CustomerTools:
    
    @staticmethod
    def get_customer_profile(customer_id: str) -> Dict:
        """
        Get customer profile
        
        Args:
            customer_id: Unique customer ID
            
        Returns:
            Dict with customer info or error
        """
        try:
            response = customers_table.get_item(Key={'customer_id': customer_id})
            
            if 'Item' not in response:
                return {
                    'success': False,
                    'error': f'Customer {customer_id} not found'
                }
            
            item = response['Item']
            customer = Customer.from_dynamo(item)
            
            return {
                'success': True,
                'customer_id': customer.customer_id,
                'name': customer.name,
                'email': customer.email,
                'vip_status': customer.vip_status.value,
                'lifetime_spent': customer.lifetime_spent,
                'total_orders': customer.total_orders,
                'return_rate': customer.return_rate,
                'preferred_contact': customer.preferred_contact.value,
                'account_age_days': (datetime.now() - customer.created_at).days
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def update_customer_vip_status(customer_id: str, new_status: str) -> Dict:
        """Update customer VIP status based on lifetime value"""
        try:
            customers_table.update_item(
                Key={'customer_id': customer_id},
                UpdateExpression='SET vip_status = :status, updated_at = :now',
                ExpressionAttributeValues={
                    ':status': new_status,
                    ':now': int(datetime.now().timestamp())
                }
            )
            return {'success': True, 'message': f'VIP status updated to {new_status}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
```

**Lambda Handler (Bedrock Action Group Contract):**

When Bedrock invokes this Lambda as an action group, it sends a structured event and expects a specific response format:

```python
# src/tools/customer_tools.py  (append below CustomerTools class)

def lambda_handler(event: dict, context) -> dict:
    """
    Entry point for Bedrock Agent action group invocations.
    
    Bedrock sends:
      event['actionGroup']  - action group name
      event['apiPath']      - e.g. '/get_customer_profile'
      event['httpMethod']   - e.g. 'GET'
      event['parameters']   - list of {name, type, value} dicts
      event['sessionAttributes'] - dict of session-level attributes
    
    Must return the Bedrock action group response envelope.
    """
    action_group = event.get("actionGroup", "")
    api_path = event.get("apiPath", "")
    http_method = event.get("httpMethod", "GET")
    parameters = {p["name"]: p["value"] for p in event.get("parameters", [])}
    session_attrs = event.get("sessionAttributes", {})

    # Route to the correct tool
    if api_path == "/get_customer_profile":
        customer_id = parameters.get("customer_id") or session_attrs.get("customer_id")
        result = CustomerTools.get_customer_profile(customer_id)
    elif api_path == "/update_customer_vip_status":
        result = CustomerTools.update_customer_vip_status(
            parameters["customer_id"], parameters["new_status"]
        )
    else:
        result = {"success": False, "error": f"Unknown apiPath: {api_path}"}

    http_status = 200 if result.get("success") else 400

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "apiPath": api_path,
            "httpMethod": http_method,
            "httpStatusCode": http_status,
            "responseBody": {
                "application/json": {
                    "body": json.dumps(result)
                }
            }
        }
    }
```

**Test Spec 3.1:**

```python
# tests/unit/test_customer_tools.py

import pytest
from moto import mock_dynamodb
import boto3
from src.tools.customer_tools import CustomerTools
from src.models.customer import Customer, VIPStatus

@mock_dynamodb
def test_get_customer_profile():
    """Test getting customer profile"""
    # Setup
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.create_table(
        TableName='shopping-customers',
        KeySchema=[{'AttributeName': 'customer_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'customer_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )
    
    customer = Customer(
        customer_id="cust-123",
        name="John Doe",
        email="john@example.com",
        vip_status=VIPStatus.GOLD,
        lifetime_spent=5000.0
    )
    table.put_item(Item=customer.to_dynamo())
    
    # Test
    result = CustomerTools.get_customer_profile("cust-123")
    assert result['success'] == True
    assert result['name'] == "John Doe"
    assert result['vip_status'] == "Gold"

@mock_dynamodb
def test_get_customer_not_found():
    """Test getting non-existent customer"""
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    dynamodb.create_table(
        TableName='shopping-customers',
        KeySchema=[{'AttributeName': 'customer_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'customer_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )
    
    result = CustomerTools.get_customer_profile("cust-999")
    assert result['success'] == False
    assert 'not found' in result['error']
```

**Definition of Done:**
- [ ] get_customer_profile implemented and tested
- [ ] update_customer_vip_status implemented
- [ ] All unit tests passing
- [ ] Error handling comprehensive
- [ ] Docstrings complete

---

### Spec 3.2: Order Tools

**Objective:** Implement tools for order lookup and status checking

**Acceptance Criteria:**
- [ ] get_order_status returns order details
- [ ] get_recent_orders returns last N orders
- [ ] Tracking information integrated
- [ ] Handles missing orders gracefully
- [ ] Unit tests passing

**Implementation:**

```python
# src/tools/order_tools.py

import boto3
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from src.models.order import Order

dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table('shopping-orders')

class OrderTools:
    
    @staticmethod
    def get_order_status(customer_id: str, order_id: str) -> Dict:
        """
        Get specific order status and tracking
        
        Args:
            customer_id: Customer ID
            order_id: Order ID
            
        Returns:
            Order details with tracking
        """
        try:
            response = orders_table.get_item(
                Key={'customer_id': customer_id, 'order_id': order_id}
            )
            
            if 'Item' not in response:
                return {'success': False, 'error': 'Order not found'}
            
            item = response['Item']
            order = Order(**item)
            
            # Mock tracking info
            tracking = {
                'tracking_number': item.get('tracking_number', 'N/A'),
                'status': item.get('status', 'Unknown'),
                'estimated_delivery': item.get('estimated_delivery', 'N/A'),
                'last_update': datetime.now().isoformat()
            }
            
            return {
                'success': True,
                'order_id': order.order_id,
                'order_date': order.order_date.isoformat(),
                'status': order.status.value,
                'items': [
                    {
                        'product_name': item.product_name,
                        'quantity': item.quantity,
                        'price': item.price
                    }
                    for item in order.items
                ],
                'total_amount': order.total_amount,
                'shipping_address': order.shipping_address,
                'tracking': tracking
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_recent_orders(customer_id: str, limit: int = 5) -> Dict:
        """Get customer's recent orders"""
        try:
            response = orders_table.query(
                KeyConditionExpression='customer_id = :cid',
                ExpressionAttributeValues={':cid': customer_id},
                ScanIndexForward=False,
                Limit=limit
            )
            
            orders = response.get('Items', [])
            return {
                'success': True,
                'customer_id': customer_id,
                'total_orders': len(orders),
                'orders': [
                    {
                        'order_id': o.get('order_id'),
                        'order_date': datetime.fromtimestamp(o.get('order_date', 0)).isoformat(),
                        'status': o.get('status'),
                        'total_amount': o.get('total_amount')
                    }
                    for o in orders
                ]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
```

**Definition of Done:**
- [ ] get_order_status working
- [ ] get_recent_orders working
- [ ] Tracking integration tested
- [ ] All unit tests passing
- [ ] Error handling robust

---

### Spec 3.3: Refund Tools

**Objective:** Implement refund processing with policy validation

**Acceptance Criteria:**
- [ ] check_return_policy validates eligibility
- [ ] process_refund creates return record
- [ ] Handles edge cases (damaged, expired)
- [ ] Generates return ID
- [ ] Records saved to DynamoDB

**Implementation:**

```python
# src/tools/refund_tools.py

import boto3
import uuid
from typing import Dict
from datetime import datetime, timedelta
from src.models.customer import Customer

dynamodb = boto3.resource('dynamodb')
returns_table = dynamodb.Table('shopping-returns')
customers_table = dynamodb.Table('shopping-customers')

class RefundTools:
    
    @staticmethod
    def check_return_policy(days_since_order: int, customer_vip_status: str = 'Regular') -> Dict:
        """
        Check if customer is eligible for return
        
        Args:
            days_since_order: Days since order placed
            customer_vip_status: VIP status
            
        Returns:
            Eligibility details
        """
        # Base policy: 30 days for regular, 60 days for VIP
        max_days = 60 if customer_vip_status != 'Regular' else 30
        
        is_eligible = days_since_order <= max_days
        days_remaining = max(0, max_days - days_since_order)
        
        return {
            'eligible': is_eligible,
            'days_remaining': days_remaining,
            'max_return_days': max_days,
            'refund_type': 'Full refund' if is_eligible else 'Not eligible',
            'restocking_fee': 0 if is_eligible else 15,
            'message': f'Return window closes in {days_remaining} days' if is_eligible else 'Return period expired'
        }
    
    @staticmethod
    def process_refund(order_id: str, customer_id: str, reason: str, amount: float) -> Dict:
        """
        Process refund request
        
        Args:
            order_id: Order to refund
            customer_id: Customer ID
            reason: Return reason
            amount: Refund amount
            
        Returns:
            Return record with ID and status
        """
        try:
            return_id = f"RET-{uuid.uuid4().hex[:8].upper()}"
            
            # Create return record
            return_record = {
                'return_id': return_id,
                'order_id': order_id,
                'customer_id': customer_id,
                'reason': reason,
                'amount': amount,
                'status': 'INITIATED',
                'created_at': int(datetime.now().timestamp()),
                'ttl': int((datetime.now() + timedelta(days=90)).timestamp())
            }
            
            returns_table.put_item(Item=return_record)
            
            # Update customer return rate
            RefundTools._update_customer_return_rate(customer_id)
            
            return {
                'success': True,
                'return_id': return_id,
                'status': 'INITIATED',
                'message': f'Return initiated. Return ID: {return_id}',
                'next_steps': 'Please print the return label and ship within 15 days'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _update_customer_return_rate(customer_id: str):
        """Update customer return rate"""
        try:
            customers_table.update_item(
                Key={'customer_id': customer_id},
                UpdateExpression='ADD return_count :inc',
                ExpressionAttributeValues={':inc': 1}
            )
        except:
            pass
```

**Definition of Done:**
- [ ] check_return_policy working for all scenarios
- [ ] process_refund creates DynamoDB records
- [ ] Return ID generation unique
- [ ] TTL configured
- [ ] Unit tests at 95%+ coverage

---

## Phase 4: Agent Layer (Days 10-12)

### Spec 4.1: Bedrock Agent Client

**Objective:** Implement main agent class with memory and identity integration

**Acceptance Criteria:**
- [ ] invoke_agent method works end-to-end
- [ ] Memory retrieval from DynamoDB
- [ ] Customer identity injected as context
- [ ] Tools called correctly
- [ ] Response formatted and returned
- [ ] Integration tests passing

**Implementation:**

```python
# src/agent/client.py

import boto3
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from src.models.customer import Customer
from src.tools.customer_tools import CustomerTools
from src.tools.order_tools import OrderTools
from src.tools.refund_tools import RefundTools

bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name='us-west-2')
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
cloudwatch = boto3.client('cloudwatch', region_name='us-west-2')

sessions_table = dynamodb.Table('shopping-agent-sessions')
customers_table = dynamodb.Table('shopping-customers')

class ShoppingCustomerSupportAgent:
    
    def __init__(self, agent_id: str, agent_alias_id: str):
        """Initialize agent with Bedrock IDs"""
        self.agent_id = agent_id
        self.agent_alias_id = agent_alias_id
    
    # ===== IDENTITY =====
    def _get_customer_identity(self, customer_id: str) -> Dict:
        """Get customer identity and context"""
        result = CustomerTools.get_customer_profile(customer_id)
        if result['success']:
            return result
        return {'customer_id': customer_id, 'vip_status': 'Regular'}
    
    # ===== MEMORY =====
    def _save_session_memory(self, session_id: str, customer_id: str, messages: List[Dict]):
        """Save conversation to memory"""
        try:
            sessions_table.put_item(Item={
                'session_id': session_id,
                'timestamp': int(datetime.now().timestamp()),
                'customer_id': customer_id,
                'conversation': messages,
                'ttl': int((datetime.now() + timedelta(days=90)).timestamp())
            })
        except Exception as e:
            print(f"⚠️  Memory save failed: {e}")
    
    def _get_session_memory(self, session_id: str) -> List[Dict]:
        """Retrieve previous conversation"""
        try:
            response = sessions_table.get_item(Key={'session_id': session_id})
            return response.get('Item', {}).get('conversation', [])
        except:
            return []
    
    # ===== MAIN INVOCATION =====
    def invoke_agent(self, session_id: str, customer_id: str, user_message: str) -> Dict:
        """
        Main agent invocation
        
        Args:
            session_id: Conversation session ID
            customer_id: Customer ID
            user_message: User input
            
        Returns:
            Response with agent reply and metadata
        """
        
        # Step 1: Get customer identity
        identity = self._get_customer_identity(customer_id)
        print(f"👤 Customer: {identity.get('name', 'Unknown')} ({identity.get('vip_status', 'Regular')})")
        
        # Step 2: Retrieve conversation memory
        previous_messages = self._get_session_memory(session_id)
        print(f"📝 Retrieved {len(previous_messages)} messages from memory")
        
        # Step 3: Build context
        system_context = f"""You are a helpful shopping customer support agent.
Current customer: {identity.get('name', 'Customer')} ({identity.get('vip_status', 'Regular')})
Account age: {identity.get('account_age_days', 0)} days
Lifetime spent: ${identity.get('lifetime_spent', 0)}
Total orders: {identity.get('total_orders', 0)}

Available tools:
- get_customer_profile: Get customer info
- get_order_status: Check order status and tracking
- get_recent_orders: List recent orders
- process_refund: Initiate refund
- check_return_policy: Verify return eligibility

Be empathetic and proactive. VIP customers get priority.
Always confirm before processing refunds."""
        
        try:
            # Step 4: Invoke Bedrock Agent
            response = bedrock_agent_runtime.invoke_agent(
                agentId=self.agent_id,
                agentAliasId=self.agent_alias_id,
                sessionId=session_id,
                inputText=user_message,
                sessionState={
                    'sessionAttributes': {
                        'customer_id': customer_id,
                        'vip_status': identity.get('vip_status', 'Regular'),
                        'system_context': system_context
                    }
                }
            )
        except Exception as e:
            return {'success': False, 'error': str(e)}
        
        # Step 5: Process EventStream response from Bedrock Agent Runtime
        # response['completion'] is an EventStream — iterate to consume chunks and traces
        final_response = ""
        tools_called = []
        
        for event in response.get("completion"):
            if "chunk" in event:
                # Text chunk from the agent's final response
                final_response += event["chunk"]["bytes"].decode("utf-8")
            elif "trace" in event:
                # Trace events reveal which action groups (tools) were invoked
                trace = event["trace"].get("trace", {})
                orch = trace.get("orchestrationTrace", {})
                ag_input = orch.get("invocationInput", {}).get("actionGroupInvocationInput", {})
                if ag_input.get("actionGroupName"):
                    tools_called.append(ag_input["actionGroupName"])
        
        # Step 6: Save to memory
        updated_messages = previous_messages + [
            {
                'role': 'user',
                'content': user_message,
                'timestamp': datetime.now().isoformat()
            },
            {
                'role': 'assistant',
                'content': final_response,
                'tools_used': tools_called,
                'timestamp': datetime.now().isoformat()
            }
        ]
        self._save_session_memory(session_id, customer_id, updated_messages)
        
        # Step 7: Evaluation metrics
        self._log_metrics(session_id, customer_id, identity, tools_called)
        
        return {
            'success': True,
            'session_id': session_id,
            'customer_id': customer_id,
            'customer_name': identity.get('name', 'Customer'),
            'vip_status': identity.get('vip_status', 'Regular'),
            'response': final_response,
            'tools_used': tools_called,
            'timestamp': datetime.now().isoformat()
        }
    
    # ===== EVALUATION =====
    def _log_metrics(self, session_id: str, customer_id: str, identity: Dict, tools: List[str]):
        """Log metrics to CloudWatch"""
        try:
            cloudwatch.put_metric_data(
                Namespace='ShoppingSupport',
                MetricData=[
                    {
                        'MetricName': 'SupportInteractions',
                        'Value': 1,
                        'Unit': 'Count',
                        'Dimensions': [
                            {'Name': 'VIPStatus', 'Value': identity.get('vip_status', 'Regular')},
                            {'Name': 'ToolCount', 'Value': str(len(tools))}
                        ]
                    }
                ]
            )
        except Exception as e:
            print(f"⚠️  Metrics logging failed: {e}")
```

**Definition of Done:**
- [ ] Agent invocation working end-to-end
- [ ] Memory save/retrieve tested
- [ ] Identity context properly injected
- [ ] Tool calls handled correctly
- [ ] Metrics logged

---

## Phase 5: Deployment & Testing (Days 13-15)

### Spec 5.1: Lambda Packaging

**Objective:** Package tools as Lambda function for agent tool execution

**Acceptance Criteria:**
- [ ] Lambda deployment package created
- [ ] All dependencies included
- [ ] Package size under 250MB
- [ ] Function tested with Bedrock
- [ ] IAM permissions correct

**Deployment Script:**

```bash
#!/bin/bash
# deployment/package_lambda.sh

set -e

echo "📦 Creating Lambda package..."

# Create temp directory
rm -rf lambda_build
mkdir -p lambda_build

# Copy source code
cp -r src lambda_build/
cp -r requirements.txt lambda_build/

# Install dependencies
pip install -r lambda_build/requirements.txt -t lambda_build/

# Create deployment package
cd lambda_build
zip -r ../shopping-support-tools.zip .
cd ..

echo "✅ Lambda package created: shopping-support-tools.zip"
echo "📊 Package size: $(du -h shopping-support-tools.zip | cut -f1)"

# Deploy to AWS
echo "🚀 Deploying to AWS Lambda..."
aws lambda create-function \
  --function-name shopping-support-tools \
  --runtime python3.11 \
  --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/lambda-shopping-tools \
  --handler src/tools/customer_tools.lambda_handler \
  --zip-file fileb://shopping-support-tools.zip \
  --timeout 60 \
  --memory-size 256

echo "✅ Lambda function deployed"
```

**Definition of Done:**
- [ ] Lambda package created and uploaded
- [ ] Function deployed successfully
- [ ] Test invocation working
- [ ] Permissions verified

---

### Spec 5.2: Integration Testing

**Objective:** End-to-end testing of agent workflow

**Acceptance Criteria:**
- [ ] All customer scenarios tested
- [ ] Memory persistence verified
- [ ] Tool execution confirmed
- [ ] Error handling tested
- [ ] Performance acceptable

**Test Spec 5.2:**

```python
# tests/e2e/test_full_conversation.py

import pytest
from moto import mock_dynamodb
import uuid
from src.agent.client import ShoppingCustomerSupportAgent
from src.models.customer import Customer, VIPStatus
from src.models.order import Order, OrderStatus, OrderItem

@mock_dynamodb
def test_full_customer_support_flow():
    """Test complete agent conversation flow"""
    
    # Setup: Create tables and sample data
    setup_test_data()
    
    # Initialize agent
    agent = ShoppingCustomerSupportAgent(
        agent_id="test-agent",
        agent_alias_id="test-alias"
    )
    
    session_id = f"sess-{uuid.uuid4().hex[:8]}"
    customer_id = "cust-test-001"
    
    # Conversation 1: Check order status
    response1 = agent.invoke_agent(
        session_id=session_id,
        customer_id=customer_id,
        user_message="Where is my order?"
    )
    
    assert response1['success'] == True
    assert response1['customer_id'] == customer_id
    assert 'response' in response1
    
    # Conversation 2: Request refund (memory should have context)
    response2 = agent.invoke_agent(
        session_id=session_id,
        customer_id=customer_id,
        user_message="I want to return this item"
    )
    
    assert response2['success'] == True
    assert len(response2['tools_used']) > 0
    
    # Verify memory was saved
    from src.agent.client import sessions_table
    mem_response = sessions_table.get_item(Key={'session_id': session_id})
    assert 'Item' in mem_response
    assert len(mem_response['Item']['conversation']) == 4  # 2 user + 2 assistant

def setup_test_data():
    """Setup mock DynamoDB tables and data"""
    import boto3
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    # Create tables
    customers_table = dynamodb.create_table(
        TableName='shopping-customers',
        KeySchema=[{'AttributeName': 'customer_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'customer_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )
    
    # Add sample customer
    customer = Customer(
        customer_id="cust-test-001",
        name="Test User",
        email="test@example.com",
        vip_status=VIPStatus.GOLD,
        lifetime_spent=5000.0,
        total_orders=10
    )
    customers_table.put_item(Item=customer.to_dynamo())
```

**Definition of Done:**
- [ ] E2E tests passing
- [ ] All scenarios covered
- [ ] Performance benchmarked
- [ ] Documentation updated

---

## Phase 6: Monitoring & Optimization (Days 16-18)

### Spec 6.1: CloudWatch Monitoring

**Objective:** Setup comprehensive monitoring and alerting

**Acceptance Criteria:**
- [ ] CloudWatch dashboards created
- [ ] Custom metrics published
- [ ] Alarms configured for errors
- [ ] Cost tracking enabled
- [ ] Logs aggregated

**Implementation:**

```python
# src/evaluations/metrics.py

import boto3
from datetime import datetime, timedelta
from typing import Dict

cloudwatch = boto3.client('cloudwatch')
logs = boto3.client('logs')

class MetricsCollector:
    
    @staticmethod
    def publish_interaction_metric(vip_status: str, tools_used: int, response_length: int):
        """Publish interaction metric"""
        cloudwatch.put_metric_data(
            Namespace='ShoppingSupport',
            MetricData=[
                {
                    'MetricName': 'Interactions',
                    'Value': 1,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'VIPStatus', 'Value': vip_status},
                        {'Name': 'ToolCount', 'Value': str(tools_used)}
                    ],
                    'Timestamp': datetime.utcnow()
                },
                {
                    'MetricName': 'ResponseLength',
                    'Value': response_length,
                    'Unit': 'Bytes',
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
    
    @staticmethod
    def create_dashboard():
        """Create CloudWatch dashboard"""
        dashboard_body = {
            'widgets': [
                {
                    'type': 'metric',
                    'properties': {
                        'metrics': [
                            ['ShoppingSupport', 'Interactions'],
                            ['.', 'ResponseLength']
                        ],
                        'period': 300,
                        'stat': 'Sum',
                        'region': 'us-west-2',
                        'title': 'Support Agent Performance'
                    }
                }
            ]
        }
        
        cloudwatch.put_dashboard(
            DashboardName='ShoppingSupport',
            DashboardBody=json.dumps(dashboard_body)
        )
    
    @staticmethod
    def create_alarms():
        """Create CloudWatch alarms"""
        cloudwatch.put_metric_alarm(
            AlarmName='SupportAgentErrors',
            MetricName='Errors',
            Namespace='ShoppingSupport',
            Statistic='Sum',
            Period=300,
            EvaluationPeriods=1,
            Threshold=10,
            ComparisonOperator='GreaterThanThreshold',
            AlarmActions=['arn:aws:sns:us-west-2:ACCOUNT:alerts']
        )
```

**Definition of Done:**
- [ ] Dashboard created and visible
- [ ] Metrics publishing correctly
- [ ] Alarms configured and tested
- [ ] Cost tracking enabled

---

### Spec 6.2: Performance Evaluation

**Objective:** Measure agent performance and ROI

**Acceptance Criteria:**
- [ ] Resolution rate calculated (>80%)
- [ ] Average response time tracked (<5s)
- [ ] Cost per interaction measured
- [ ] Customer satisfaction tracked
- [ ] Report generated

**Implementation:**

```python
# src/evaluations/analytics.py

import boto3
from datetime import datetime, timedelta
from typing import Dict

cloudwatch = boto3.client('cloudwatch')

class PerformanceAnalytics:
    
    @staticmethod
    def get_metrics_summary(days: int = 7) -> Dict:
        """Get performance metrics summary"""
        
        # Get interaction count
        interactions = cloudwatch.get_metric_statistics(
            Namespace='ShoppingSupport',
            MetricName='Interactions',
            StartTime=datetime.now() - timedelta(days=days),
            EndTime=datetime.now(),
            Period=86400,
            Statistics=['Sum']
        )
        
        total_interactions = sum(m['Sum'] for m in interactions['Datapoints'])
        
        return {
            'period_days': days,
            'total_interactions': int(total_interactions),
            'avg_per_day': int(total_interactions / days) if days > 0 else 0,
            'avg_resolution_time_seconds': 2.5,  # Example
            'cost_per_interaction': 0.02,  # Example
            'customer_satisfaction': 4.5  # Out of 5
        }
```

**Definition of Done:**
- [ ] Metrics dashboard showing results
- [ ] KPIs tracked and reported
- [ ] ROI calculated
- [ ] Optimization recommendations made

---

## Phase 7: Documentation & Handoff (Days 19-21)

### Spec 7.1: API Documentation

**File: docs/API_SPEC.md**

```markdown
# Shopping Support Agent API Specification

## Endpoint: POST /invoke-agent

### Request

\`\`\`json
{
  "session_id": "sess-abc123",
  "customer_id": "cust-12345",
  "message": "Where is my order?"
}
\`\`\`

### Response (Success)

\`\`\`json
{
  "success": true,
  "session_id": "sess-abc123",
  "customer_id": "cust-12345",
  "customer_name": "John Doe",
  "vip_status": "Gold",
  "response": "I found your order...",
  "tools_used": ["get_order_status", "check_return_policy"],
  "timestamp": "2024-01-15T10:30:00Z"
}
\`\`\`

### Response (Error)

\`\`\`json
{
  "success": false,
  "error": "Customer not found"
}
\`\`\`
```

**Definition of Done:**
- [ ] API documentation complete
- [ ] Examples provided
- [ ] Error codes documented
- [ ] Rate limits documented

---

### Spec 7.2: Operational Runbook

**File: docs/TROUBLESHOOTING.md**

```markdown
# Troubleshooting Guide

## Agent Not Responding

1. Check Lambda function logs:
   \`aws logs tail /aws/lambda/shopping-support-tools\`
2. Verify DynamoDB tables exist and have capacity
3. Check Bedrock agent status in AWS Console

## Memory Not Persisting

1. Verify DynamoDB sessions table TTL enabled
2. Check session_id is consistent across calls
3. Review CloudWatch logs for save failures

## High Latency

1. Check Lambda cold start times
2. Increase Lambda memory allocation
3. Review CloudWatch X-Ray traces
```

**Definition of Done:**
- [ ] All common issues documented
- [ ] Solutions provided
- [ ] Escalation path clear

---

## Summary Checklist

### Phase 1: Foundation ✅
- [ ] AWS permissions setup
- [ ] Project structure created
- [ ] Repository initialized

### Phase 2: Data Layer ✅
- [ ] DynamoDB tables created (4 tables)
- [ ] Pydantic models implemented (4 models)
- [ ] Unit tests passing (100% coverage)

### Phase 3: Tools ✅
- [ ] Customer tools (get_profile, update_vip)
- [ ] Order tools (get_status, get_recent)
- [ ] Refund tools (check_policy, process_refund)
- [ ] All tools tested and working

### Phase 4: Agent Layer ✅
- [ ] Bedrock agent client implemented
- [ ] Memory management (save/retrieve)
- [ ] Identity integration
- [ ] Tool invocation working

### Phase 5: Deployment ✅
- [ ] Lambda packaged and deployed
- [ ] E2E tests passing
- [ ] All scenarios covered

### Phase 6: Monitoring ✅
- [ ] CloudWatch dashboard created
- [ ] Metrics publishing
- [ ] Alarms configured
- [ ] Performance analytics enabled

### Phase 7: Documentation ✅
- [ ] API documentation complete
- [ ] Runbook created
- [ ] Architecture guide written
- [ ] Team trained

---

## Testing Strategy

```
Unit Tests (70% coverage)
├── Models: test_models.py
├── Tools: test_*_tools.py
└── Client: test_agent_client.py

Integration Tests (20% coverage)
├── DynamoDB: test_dynamodb.py
├── Agent flow: test_agent_flow.py
└── Tools integration: test_tools_integration.py

E2E Tests (10% coverage)
└── Full conversation: test_full_conversation.py
```

## Deployment Timeline

| Phase | Days | Deliverables |
|-------|------|--------------|
| Foundation | 1-3 | Setup, structure, IAM |
| Data Layer | 4-6 | DynamoDB, models, tests |
| Tools | 7-9 | Lambda functions, tests |
| Agent | 10-12 | Agent client, integration |
| Deployment | 13-15 | Packaging, E2E tests |
| Monitoring | 16-18 | CloudWatch, metrics |
| Documentation | 19-21 | Docs, runbooks, training |

## Success Metrics

- **Resolution Rate:** >80% of issues resolved without escalation
- **Response Time:** <5 seconds average
- **Availability:** 99.9% uptime
- **Cost:** <$0.02 per interaction
- **CSAT:** >4.5/5.0 stars
- **Code Coverage:** >90% unit test coverage

---

## Next Steps After Implementation

1. **A/B Testing:** Test different response styles
2. **Integrations:** Add Slack, SMS, mobile app
3. **ML Enhancements:** Fine-tune response generation
4. **Scaling:** Prepare for high-volume traffic
5. **Analytics:** Build advanced dashboards

---

## References

- [AWS Bedrock Agents Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/)
- [Lambda Performance Optimization](https://docs.aws.amazon.com/lambda/latest/dg/)
- [Spec Driven Development](https://en.wikipedia.org/wiki/Specification_by_example)

