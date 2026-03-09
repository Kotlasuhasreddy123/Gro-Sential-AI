#!/usr/bin/env python3
"""
Create DynamoDB tables for Gro-Sential
Run this once to set up your database
"""

import boto3
import os

AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-2')
ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY_ID')
SECRET_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')

def create_tables():
    """Create all required DynamoDB tables"""
    
    session = boto3.Session(
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name=AWS_REGION
    )
    dynamodb = session.client('dynamodb')
    
    print("Creating DynamoDB tables...")
    print("=" * 60)
    
    # Table 1: Users
    try:
        print("\n1. Creating 'Gro-SentialUsers' table...")
        dynamodb.create_table(
            TableName='Gro-SentialUsers',
            KeySchema=[
                {'AttributeName': 'UserEmail', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'UserEmail', 'AttributeType': 'S'},
                {'AttributeName': 'Pincode', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'PincodeIndex',
                    'KeySchema': [
                        {'AttributeName': 'Pincode', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print("   ✅ Gro-SentialUsers table created")
    except dynamodb.exceptions.ResourceInUseException:
        print("   ⚠️  Gro-SentialUsers table already exists")
    
    # Table 2: User Inventory
    try:
        print("\n2. Creating 'Gro-SentialInventory' table...")
        dynamodb.create_table(
            TableName='Gro-SentialInventory',
            KeySchema=[
                {'AttributeName': 'UserEmail', 'KeyType': 'HASH'},
                {'AttributeName': 'ItemName', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'UserEmail', 'AttributeType': 'S'},
                {'AttributeName': 'ItemName', 'AttributeType': 'S'},
                {'AttributeName': 'Pincode', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'ItemPincodeIndex',
                    'KeySchema': [
                        {'AttributeName': 'ItemName', 'KeyType': 'HASH'},
                        {'AttributeName': 'Pincode', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print("   ✅ Gro-SentialInventory table created")
    except dynamodb.exceptions.ResourceInUseException:
        print("   ⚠️  Gro-SentialInventory table already exists")
    
    # Table 3: Trade Requests
    try:
        print("\n3. Creating 'Gro-SentialTrades' table...")
        dynamodb.create_table(
            TableName='Gro-SentialTrades',
            KeySchema=[
                {'AttributeName': 'TradeID', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'TradeID', 'AttributeType': 'S'},
                {'AttributeName': 'RequesterEmail', 'AttributeType': 'S'},
                {'AttributeName': 'ProviderEmail', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'RequesterIndex',
                    'KeySchema': [
                        {'AttributeName': 'RequesterEmail', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                },
                {
                    'IndexName': 'ProviderIndex',
                    'KeySchema': [
                        {'AttributeName': 'ProviderEmail', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print("   ✅ Gro-SentialTrades table created")
    except dynamodb.exceptions.ResourceInUseException:
        print("   ⚠️  Gro-SentialTrades table already exists")
    
    # Table 4: Recipes (keep existing)
    try:
        print("\n4. Creating 'Gro-SentialRecipes' table...")
        dynamodb.create_table(
            TableName='Gro-SentialRecipes',
            KeySchema=[
                {'AttributeName': 'RecipeID', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'RecipeID', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("   ✅ Gro-SentialRecipes table created")
    except dynamodb.exceptions.ResourceInUseException:
        print("   ⚠️  Gro-SentialRecipes table already exists")
    
    print("\n" + "=" * 60)
    print("✅ All tables created successfully!")
    print("\nTable Summary:")
    print("  1. Gro-SentialUsers - User profiles")
    print("  2. Gro-SentialInventory - User food items")
    print("  3. Gro-SentialTrades - Trade requests")
    print("  4. Gro-SentialRecipes - Saved recipes")
    print("\nYou can now run the application!")

if __name__ == '__main__':
    create_tables()
