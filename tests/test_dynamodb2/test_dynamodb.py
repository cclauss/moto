from __future__ import unicode_literals, print_function

from decimal import Decimal

import six
import boto
import boto3
from boto3.dynamodb.conditions import Attr, Key
import sure  # noqa
import requests
from moto import mock_dynamodb2, mock_dynamodb2_deprecated
from moto.dynamodb2 import dynamodb_backend2
from boto.exception import JSONResponseError
from botocore.exceptions import ClientError
from tests.helpers import requires_boto_gte
import tests.backport_assert_raises

import moto.dynamodb2.comparisons
import moto.dynamodb2.models

from nose.tools import assert_raises
try:
    import boto.dynamodb2
except ImportError:
    print("This boto version is not supported")


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_list_tables():
    name = 'TestTable'
    # Should make tables properly with boto
    dynamodb_backend2.create_table(name, schema=[
        {u'KeyType': u'HASH', u'AttributeName': u'forum_name'},
        {u'KeyType': u'RANGE', u'AttributeName': u'subject'}
    ])
    conn = boto.dynamodb2.connect_to_region(
        'us-east-1',
        aws_access_key_id="ak",
        aws_secret_access_key="sk")
    assert conn.list_tables()["TableNames"] == [name]


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_list_tables_layer_1():
    # Should make tables properly with boto
    dynamodb_backend2.create_table("test_1", schema=[
        {u'KeyType': u'HASH', u'AttributeName': u'name'}
    ])
    dynamodb_backend2.create_table("test_2", schema=[
        {u'KeyType': u'HASH', u'AttributeName': u'name'}
    ])
    conn = boto.dynamodb2.connect_to_region(
        'us-east-1',
        aws_access_key_id="ak",
        aws_secret_access_key="sk")

    res = conn.list_tables(limit=1)
    expected = {"TableNames": ["test_1"], "LastEvaluatedTableName": "test_1"}
    res.should.equal(expected)

    res = conn.list_tables(limit=1, exclusive_start_table_name="test_1")
    expected = {"TableNames": ["test_2"]}
    res.should.equal(expected)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_describe_missing_table():
    conn = boto.dynamodb2.connect_to_region(
        'us-west-2',
        aws_access_key_id="ak",
        aws_secret_access_key="sk")
    with assert_raises(JSONResponseError):
        conn.describe_table('messages')


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_list_table_tags():
    name = 'TestTable'
    conn = boto3.client('dynamodb',
                        region_name='us-west-2',
                        aws_access_key_id="ak",
                        aws_secret_access_key="sk")
    conn.create_table(TableName=name,
                      KeySchema=[{'AttributeName':'id','KeyType':'HASH'}],
                      AttributeDefinitions=[{'AttributeName':'id','AttributeType':'S'}],
                      ProvisionedThroughput={'ReadCapacityUnits':5,'WriteCapacityUnits':5})
    table_description = conn.describe_table(TableName=name)
    arn = table_description['Table']['TableArn']

    # Tag table
    tags = [{'Key': 'TestTag', 'Value': 'TestValue'}, {'Key': 'TestTag2', 'Value': 'TestValue2'}]
    conn.tag_resource(ResourceArn=arn, Tags=tags)

    # Check tags
    resp = conn.list_tags_of_resource(ResourceArn=arn)
    assert resp["Tags"] == tags

    # Remove 1 tag
    conn.untag_resource(ResourceArn=arn, TagKeys=['TestTag'])

    # Check tags
    resp = conn.list_tags_of_resource(ResourceArn=arn)
    assert resp["Tags"] == [{'Key': 'TestTag2', 'Value': 'TestValue2'}]


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_list_table_tags_empty():
    name = 'TestTable'
    conn = boto3.client('dynamodb',
                        region_name='us-west-2',
                        aws_access_key_id="ak",
                        aws_secret_access_key="sk")
    conn.create_table(TableName=name,
                      KeySchema=[{'AttributeName':'id','KeyType':'HASH'}],
                      AttributeDefinitions=[{'AttributeName':'id','AttributeType':'S'}],
                      ProvisionedThroughput={'ReadCapacityUnits':5,'WriteCapacityUnits':5})
    table_description = conn.describe_table(TableName=name)
    arn = table_description['Table']['TableArn']
    tags = [{'Key':'TestTag', 'Value': 'TestValue'}]
    # conn.tag_resource(ResourceArn=arn,
    #                   Tags=tags)
    resp = conn.list_tags_of_resource(ResourceArn=arn)
    assert resp["Tags"] == []


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_list_table_tags_paginated():
    name = 'TestTable'
    conn = boto3.client('dynamodb',
                        region_name='us-west-2',
                        aws_access_key_id="ak",
                        aws_secret_access_key="sk")
    conn.create_table(TableName=name,
                      KeySchema=[{'AttributeName':'id','KeyType':'HASH'}],
                      AttributeDefinitions=[{'AttributeName':'id','AttributeType':'S'}],
                      ProvisionedThroughput={'ReadCapacityUnits':5,'WriteCapacityUnits':5})
    table_description = conn.describe_table(TableName=name)
    arn = table_description['Table']['TableArn']
    for i in range(11):
        tags = [{'Key':'TestTag%d' % i, 'Value': 'TestValue'}]
        conn.tag_resource(ResourceArn=arn,
                          Tags=tags)
    resp = conn.list_tags_of_resource(ResourceArn=arn)
    assert len(resp["Tags"]) == 10
    assert 'NextToken' in resp.keys()
    resp2 = conn.list_tags_of_resource(ResourceArn=arn,
                                       NextToken=resp['NextToken'])
    assert len(resp2["Tags"]) == 1
    assert 'NextToken' not in resp2.keys()


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_list_not_found_table_tags():
    conn = boto3.client('dynamodb',
                        region_name='us-west-2',
                        aws_access_key_id="ak",
                        aws_secret_access_key="sk")
    arn = 'DymmyArn'
    try:
        conn.list_tags_of_resource(ResourceArn=arn)
    except ClientError as exception:
        assert exception.response['Error']['Code'] == "ResourceNotFoundException"


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_item_add_empty_string_exception():
    name = 'TestTable'
    conn = boto3.client('dynamodb',
                        region_name='us-west-2',
                        aws_access_key_id="ak",
                        aws_secret_access_key="sk")
    conn.create_table(TableName=name,
                      KeySchema=[{'AttributeName':'forum_name','KeyType':'HASH'}],
                      AttributeDefinitions=[{'AttributeName':'forum_name','AttributeType':'S'}],
                      ProvisionedThroughput={'ReadCapacityUnits':5,'WriteCapacityUnits':5})

    with assert_raises(ClientError) as ex:
        conn.put_item(
            TableName=name,
            Item={
                'forum_name': { 'S': 'LOLCat Forum' },
                'subject': { 'S': 'Check this out!' },
                'Body': { 'S': 'http://url_to_lolcat.gif'},
                'SentBy': { 'S': "" },
                'ReceivedTime': { 'S': '12/9/2011 11:36:03 PM'},
            }
        )

    ex.exception.response['Error']['Code'].should.equal('ValidationException')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(400)
    ex.exception.response['Error']['Message'].should.equal(
        'One or more parameter values were invalid: An AttributeValue may not contain an empty string'
    )


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_update_item_with_empty_string_exception():
    name = 'TestTable'
    conn = boto3.client('dynamodb',
                        region_name='us-west-2',
                        aws_access_key_id="ak",
                        aws_secret_access_key="sk")
    conn.create_table(TableName=name,
                      KeySchema=[{'AttributeName':'forum_name','KeyType':'HASH'}],
                      AttributeDefinitions=[{'AttributeName':'forum_name','AttributeType':'S'}],
                      ProvisionedThroughput={'ReadCapacityUnits':5,'WriteCapacityUnits':5})

    conn.put_item(
        TableName=name,
        Item={
            'forum_name': { 'S': 'LOLCat Forum' },
            'subject': { 'S': 'Check this out!' },
            'Body': { 'S': 'http://url_to_lolcat.gif'},
            'SentBy': { 'S': "test" },
            'ReceivedTime': { 'S': '12/9/2011 11:36:03 PM'},
        }
    )

    with assert_raises(ClientError) as ex:
        conn.update_item(
            TableName=name,
            Key={
                'forum_name': { 'S': 'LOLCat Forum'},
            },
            UpdateExpression='set Body=:Body',
            ExpressionAttributeValues={
                ':Body': {'S': ''}
            })

    ex.exception.response['Error']['Code'].should.equal('ValidationException')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(400)
    ex.exception.response['Error']['Message'].should.equal(
        'One or more parameter values were invalid: An AttributeValue may not contain an empty string'
    )


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_query_invalid_table():
    conn = boto3.client('dynamodb',
                        region_name='us-west-2',
                        aws_access_key_id="ak",
                        aws_secret_access_key="sk")
    try:
        conn.query(TableName='invalid_table', KeyConditionExpression='index1 = :partitionkeyval', ExpressionAttributeValues={':partitionkeyval': {'S':'test'}})
    except ClientError as exception:
        assert exception.response['Error']['Code'] == "ResourceNotFoundException"


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_scan_returns_consumed_capacity():
    name = 'TestTable'
    conn = boto3.client('dynamodb',
                        region_name='us-west-2',
                        aws_access_key_id="ak",
                        aws_secret_access_key="sk")

    conn.create_table(TableName=name,
                      KeySchema=[{'AttributeName':'forum_name','KeyType':'HASH'}],
                      AttributeDefinitions=[{'AttributeName':'forum_name','AttributeType':'S'}],
                      ProvisionedThroughput={'ReadCapacityUnits':5,'WriteCapacityUnits':5})

    conn.put_item(
            TableName=name,
            Item={
                'forum_name': { 'S': 'LOLCat Forum' },
                'subject': { 'S': 'Check this out!' },
                'Body': { 'S': 'http://url_to_lolcat.gif'},
                'SentBy': { 'S': "test" },
                'ReceivedTime': { 'S': '12/9/2011 11:36:03 PM'},
            }
        )

    response = conn.scan(
        TableName=name,
    )

    assert 'ConsumedCapacity' in response
    assert 'CapacityUnits' in response['ConsumedCapacity']
    assert response['ConsumedCapacity']['TableName'] == name


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_put_item_with_special_chars():
    name = 'TestTable'
    conn = boto3.client('dynamodb',
                        region_name='us-west-2',
                        aws_access_key_id="ak",
                        aws_secret_access_key="sk")

    conn.create_table(TableName=name,
                      KeySchema=[{'AttributeName':'forum_name','KeyType':'HASH'}],
                      AttributeDefinitions=[{'AttributeName':'forum_name','AttributeType':'S'}],
                      ProvisionedThroughput={'ReadCapacityUnits':5,'WriteCapacityUnits':5})

    conn.put_item(
            TableName=name,
            Item={
                'forum_name': { 'S': 'LOLCat Forum' },
                'subject': { 'S': 'Check this out!' },
                'Body': { 'S': 'http://url_to_lolcat.gif'},
                'SentBy': { 'S': "test" },
                'ReceivedTime': { 'S': '12/9/2011 11:36:03 PM'},
                '"': {"S": "foo"},
            }
        )


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_query_returns_consumed_capacity():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'forum_name',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'subject',
                'KeyType': 'RANGE'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'forum_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'subject',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    table = dynamodb.Table('users')

    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '123',
        'body': 'some test message'
    })

    results = table.query(
        KeyConditionExpression=Key('forum_name').eq(
            'the-key')
    )

    assert 'ConsumedCapacity' in results
    assert 'CapacityUnits' in results['ConsumedCapacity']
    assert results['ConsumedCapacity']['CapacityUnits'] == 1


@mock_dynamodb2
def test_basic_projection_expression_using_get_item():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'forum_name',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'subject',
                'KeyType': 'RANGE'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'forum_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'subject',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    table = dynamodb.Table('users')

    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '123',
        'body': 'some test message'
    })

    table.put_item(Item={
        'forum_name': 'not-the-key',
        'subject': '123',
        'body': 'some other test message'
    })
    result = table.get_item(
        Key = {
            'forum_name': 'the-key',
            'subject': '123'
        },
        ProjectionExpression='body, subject'
    )

    result['Item'].should.be.equal({
        'subject': '123',
        'body': 'some test message'
    })

    # The projection expression should not remove data from storage
    result = table.get_item(
        Key = {
            'forum_name': 'the-key',
            'subject': '123'
        }
    )

    result['Item'].should.be.equal({
        'forum_name': 'the-key',
        'subject': '123',
        'body': 'some test message'
    })


@mock_dynamodb2
def test_basic_projection_expressions_using_query():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'forum_name',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'subject',
                'KeyType': 'RANGE'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'forum_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'subject',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    table = dynamodb.Table('users')

    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '123',
        'body': 'some test message'
    })

    table.put_item(Item={
        'forum_name': 'not-the-key',
        'subject': '123',
        'body': 'some other test message'
    })
    # Test a query returning all items
    results = table.query(
        KeyConditionExpression=Key('forum_name').eq(
            'the-key'),
        ProjectionExpression='body, subject'
    )

    assert 'body' in results['Items'][0]
    assert results['Items'][0]['body'] == 'some test message'
    assert 'subject' in results['Items'][0]

    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '1234',
        'body': 'yet another test message'
    })

    results = table.query(
        KeyConditionExpression=Key('forum_name').eq(
            'the-key'),
        ProjectionExpression='body'
    )

    assert 'body' in results['Items'][0]
    assert 'subject' not in results['Items'][0]
    assert results['Items'][0]['body'] == 'some test message'
    assert 'body' in results['Items'][1]
    assert 'subject' not in results['Items'][1]
    assert results['Items'][1]['body'] == 'yet another test message'

    # The projection expression should not remove data from storage
    results = table.query(
        KeyConditionExpression=Key('forum_name').eq(
            'the-key'),
    )
    assert 'subject' in results['Items'][0]
    assert 'body' in results['Items'][1]
    assert 'forum_name' in results['Items'][1]


@mock_dynamodb2
def test_basic_projection_expressions_using_scan():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'forum_name',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'subject',
                'KeyType': 'RANGE'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'forum_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'subject',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    table = dynamodb.Table('users')

    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '123',
        'body': 'some test message'
    })

    table.put_item(Item={
        'forum_name': 'not-the-key',
        'subject': '123',
        'body': 'some other test message'
    })
    # Test a scan returning all items
    results = table.scan(
        FilterExpression=Key('forum_name').eq(
            'the-key'),
        ProjectionExpression='body, subject'
    )

    assert 'body' in results['Items'][0]
    assert results['Items'][0]['body'] == 'some test message'
    assert 'subject' in results['Items'][0]

    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '1234',
        'body': 'yet another test message'
    })

    results = table.scan(
        FilterExpression=Key('forum_name').eq(
            'the-key'),
        ProjectionExpression='body'
    )

    assert 'body' in results['Items'][0]
    assert 'subject' not in results['Items'][0]
    assert 'forum_name' not in results['Items'][0]
    assert 'body' in results['Items'][1]
    assert 'subject' not in results['Items'][1]
    assert 'forum_name' not in results['Items'][1]

    # The projection expression should not remove data from storage
    results = table.query(
        KeyConditionExpression=Key('forum_name').eq(
            'the-key'),
    )
    assert 'subject' in results['Items'][0]
    assert 'body' in results['Items'][1]
    assert 'forum_name' in results['Items'][1]


@mock_dynamodb2
def test_basic_projection_expression_using_get_item_with_attr_expression_names():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'forum_name',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'subject',
                'KeyType': 'RANGE'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'forum_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'subject',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    table = dynamodb.Table('users')

    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '123',
        'body': 'some test message',
        'attachment': 'something'
    })

    table.put_item(Item={
        'forum_name': 'not-the-key',
        'subject': '123',
        'body': 'some other test message',
        'attachment': 'something'
    })
    result = table.get_item(
        Key={
            'forum_name': 'the-key',
            'subject': '123'
        },
        ProjectionExpression='#rl, #rt, subject',
        ExpressionAttributeNames={
            '#rl': 'body',
            '#rt': 'attachment'
            },
    )

    result['Item'].should.be.equal({
        'subject': '123',
        'body': 'some test message',
        'attachment': 'something'
    })


@mock_dynamodb2
def test_basic_projection_expressions_using_query_with_attr_expression_names():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'forum_name',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'subject',
                'KeyType': 'RANGE'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'forum_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'subject',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    table = dynamodb.Table('users')

    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '123',
        'body': 'some test message',
        'attachment': 'something'
    })

    table.put_item(Item={
        'forum_name': 'not-the-key',
        'subject': '123',
        'body': 'some other test message',
        'attachment': 'something'
    })
    # Test a query returning all items

    results = table.query(
        KeyConditionExpression=Key('forum_name').eq(
            'the-key'),
        ProjectionExpression='#rl, #rt, subject',
        ExpressionAttributeNames={
            '#rl': 'body',
            '#rt': 'attachment'
            },
    )

    assert 'body' in results['Items'][0]
    assert results['Items'][0]['body'] == 'some test message'
    assert 'subject' in results['Items'][0]
    assert results['Items'][0]['subject'] == '123'
    assert 'attachment' in results['Items'][0]
    assert results['Items'][0]['attachment'] == 'something'


@mock_dynamodb2
def test_basic_projection_expressions_using_scan_with_attr_expression_names():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'forum_name',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'subject',
                'KeyType': 'RANGE'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'forum_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'subject',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    table = dynamodb.Table('users')

    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '123',
        'body': 'some test message',
        'attachment': 'something'
    })

    table.put_item(Item={
        'forum_name': 'not-the-key',
        'subject': '123',
        'body': 'some other test message',
        'attachment': 'something'
    })
    # Test a scan returning all items

    results = table.scan(
        FilterExpression=Key('forum_name').eq(
            'the-key'),
        ProjectionExpression='#rl, #rt, subject',
        ExpressionAttributeNames={
            '#rl': 'body',
            '#rt': 'attachment'
            },
    )

    assert 'body' in results['Items'][0]
    assert 'attachment' in results['Items'][0]
    assert 'subject' in results['Items'][0]
    assert 'form_name' not in results['Items'][0]

    # Test without a FilterExpression
    results = table.scan(
        ProjectionExpression='#rl, #rt, subject',
        ExpressionAttributeNames={
            '#rl': 'body',
            '#rt': 'attachment'
            },
    )

    assert 'body' in results['Items'][0]
    assert 'attachment' in results['Items'][0]
    assert 'subject' in results['Items'][0]
    assert 'form_name' not in results['Items'][0]


@mock_dynamodb2
def test_put_item_returns_consumed_capacity():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'forum_name',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'subject',
                'KeyType': 'RANGE'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'forum_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'subject',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    table = dynamodb.Table('users')

    response = table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '123',
        'body': 'some test message',
    })

    assert 'ConsumedCapacity' in response


@mock_dynamodb2
def test_update_item_returns_consumed_capacity():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'forum_name',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'subject',
                'KeyType': 'RANGE'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'forum_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'subject',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    table = dynamodb.Table('users')

    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '123',
        'body': 'some test message',
    })

    response = table.update_item(Key={
        'forum_name': 'the-key',
        'subject': '123'
        },
        UpdateExpression='set body=:tb',
        ExpressionAttributeValues={
            ':tb': 'a new message'
    })

    assert 'ConsumedCapacity' in response
    assert 'CapacityUnits' in response['ConsumedCapacity']
    assert 'TableName' in response['ConsumedCapacity']


@mock_dynamodb2
def test_get_item_returns_consumed_capacity():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'forum_name',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'subject',
                'KeyType': 'RANGE'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'forum_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'subject',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    table = dynamodb.Table('users')

    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '123',
        'body': 'some test message',
    })

    response = table.get_item(Key={
        'forum_name': 'the-key',
        'subject': '123'
    })

    assert 'ConsumedCapacity' in response
    assert 'CapacityUnits' in response['ConsumedCapacity']
    assert 'TableName' in response['ConsumedCapacity']


def test_filter_expression():
    row1 = moto.dynamodb2.models.Item(None, None, None, None, {'Id': {'N': '8'}, 'Subs': {'N': '5'}, 'Desc': {'S': 'Some description'}, 'KV': {'SS': ['test1', 'test2']}})
    row2 = moto.dynamodb2.models.Item(None, None, None, None, {'Id': {'N': '8'}, 'Subs': {'N': '10'}, 'Desc': {'S': 'A description'}, 'KV': {'SS': ['test3', 'test4']}})

    # NOT test 1
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('NOT attribute_not_exists(Id)', {}, {})
    filter_expr.expr(row1).should.be(True)

    # NOT test 2
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('NOT (Id = :v0)', {}, {':v0': {'N': '8'}})
    filter_expr.expr(row1).should.be(False)  # Id = 8 so should be false

    # AND test
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('Id > :v0 AND Subs < :v1', {}, {':v0': {'N': '5'}, ':v1': {'N': '7'}})
    filter_expr.expr(row1).should.be(True)
    filter_expr.expr(row2).should.be(False)

    # OR test
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('Id = :v0 OR Id=:v1', {}, {':v0': {'N': '5'}, ':v1': {'N': '8'}})
    filter_expr.expr(row1).should.be(True)

    # BETWEEN test
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('Id BETWEEN :v0 AND :v1', {}, {':v0': {'N': '5'}, ':v1': {'N': '10'}})
    filter_expr.expr(row1).should.be(True)

    # PAREN test
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('Id = :v0 AND (Subs = :v0 OR Subs = :v1)', {}, {':v0': {'N': '8'}, ':v1': {'N': '5'}})
    filter_expr.expr(row1).should.be(True)

    # IN test
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('Id IN (:v0, :v1, :v2)', {}, {
        ':v0': {'N': '7'},
        ':v1': {'N': '8'},
        ':v2': {'N': '9'}})
    filter_expr.expr(row1).should.be(True)

    # attribute function tests (with extra spaces)
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('attribute_exists(Id) AND attribute_not_exists (User)', {}, {})
    filter_expr.expr(row1).should.be(True)

    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('attribute_type(Id, :v0)', {}, {':v0': {'S': 'N'}})
    filter_expr.expr(row1).should.be(True)

    # beginswith function test
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('begins_with(Desc, :v0)', {}, {':v0': {'S': 'Some'}})
    filter_expr.expr(row1).should.be(True)
    filter_expr.expr(row2).should.be(False)

    # contains function test
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('contains(KV, :v0)', {}, {':v0': {'S': 'test1'}})
    filter_expr.expr(row1).should.be(True)
    filter_expr.expr(row2).should.be(False)

    # size function test
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('size(Desc) > size(KV)', {}, {})
    filter_expr.expr(row1).should.be(True)

    # Expression from @batkuip
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression(
        '(#n0 < :v0 AND attribute_not_exists(#n1))',
        {'#n0': 'Subs', '#n1': 'fanout_ts'},
        {':v0': {'N': '7'}}
    )
    filter_expr.expr(row1).should.be(True)
    # Expression from to check contains on string value
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression(
        'contains(#n0, :v0)',
        {'#n0': 'Desc'},
        {':v0': {'S': 'Some'}}
    )
    filter_expr.expr(row1).should.be(True)
    filter_expr.expr(row2).should.be(False)


@mock_dynamodb2
def test_query_filter():
    client = boto3.client('dynamodb', region_name='us-east-1')
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    client.create_table(
        TableName='test1',
        AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'S'}],
        KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
        ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123}
    )
    client.put_item(
        TableName='test1',
        Item={
            'client': {'S': 'client1'},
            'app': {'S': 'app1'},
            'nested': {'M': {
                'version': {'S': 'version1'},
                'contents': {'L': [
                    {'S': 'value1'}, {'S': 'value2'},
                ]},
            }},
        }
    )
    client.put_item(
        TableName='test1',
        Item={
            'client': {'S': 'client1'},
            'app': {'S': 'app2'},
            'nested': {'M': {
                'version': {'S': 'version2'},
                'contents': {'L': [
                    {'S': 'value1'}, {'S': 'value2'},
                ]},
            }},
        }
    )

    table = dynamodb.Table('test1')
    response = table.query(
        KeyConditionExpression=Key('client').eq('client1')
    )
    assert response['Count'] == 2

    response = table.query(
        KeyConditionExpression=Key('client').eq('client1'),
        FilterExpression=Attr('app').eq('app2')
    )
    assert response['Count'] == 1
    assert response['Items'][0]['app'] == 'app2'
    response = table.query(
        KeyConditionExpression=Key('client').eq('client1'),
        FilterExpression=Attr('app').contains('app')
    )
    assert response['Count'] == 2

    response = table.query(
        KeyConditionExpression=Key('client').eq('client1'),
        FilterExpression=Attr('nested.version').contains('version')
    )
    assert response['Count'] == 2

    response = table.query(
        KeyConditionExpression=Key('client').eq('client1'),
        FilterExpression=Attr('nested.contents[0]').eq('value1')
    )
    assert response['Count'] == 2


@mock_dynamodb2
def test_query_filter_overlapping_expression_prefixes():
    client = boto3.client('dynamodb', region_name='us-east-1')
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    client.create_table(
        TableName='test1',
        AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'S'}],
        KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
        ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123}
    )

    client.put_item(
        TableName='test1',
        Item={
            'client': {'S': 'client1'},
            'app': {'S': 'app1'},
            'nested': {'M': {
                'version': {'S': 'version1'},
                'contents': {'L': [
                    {'S': 'value1'}, {'S': 'value2'},
                ]},
            }},
    })

    table = dynamodb.Table('test1')
    response = table.query(
        KeyConditionExpression=Key('client').eq('client1') & Key('app').eq('app1'),
        ProjectionExpression='#1, #10, nested',
        ExpressionAttributeNames={
            '#1': 'client',
            '#10': 'app',
        }
    )

    assert response['Count'] == 1
    assert response['Items'][0] == {
        'client': 'client1',
        'app': 'app1',
        'nested': {
            'version': 'version1',
            'contents': ['value1', 'value2']
        }
    }


@mock_dynamodb2
def test_scan_filter():
    client = boto3.client('dynamodb', region_name='us-east-1')
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    client.create_table(
        TableName='test1',
        AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'S'}],
        KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
        ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123}
    )
    client.put_item(
        TableName='test1',
        Item={
            'client': {'S': 'client1'},
            'app': {'S': 'app1'}
        }
    )

    table = dynamodb.Table('test1')
    response = table.scan(
        FilterExpression=Attr('app').eq('app2')
    )
    assert response['Count'] == 0

    response = table.scan(
        FilterExpression=Attr('app').eq('app1')
    )
    assert response['Count'] == 1

    response = table.scan(
        FilterExpression=Attr('app').ne('app2')
    )
    assert response['Count'] == 1

    response = table.scan(
        FilterExpression=Attr('app').ne('app1')
    )
    assert response['Count'] == 0


@mock_dynamodb2
def test_scan_filter2():
    client = boto3.client('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    client.create_table(
        TableName='test1',
        AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'N'}],
        KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
        ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123}
    )
    client.put_item(
        TableName='test1',
        Item={
            'client': {'S': 'client1'},
            'app': {'N': '1'}
        }
    )

    response = client.scan(
        TableName='test1',
        Select='ALL_ATTRIBUTES',
        FilterExpression='#tb >= :dt',
        ExpressionAttributeNames={"#tb": "app"},
        ExpressionAttributeValues={":dt": {"N": str(1)}}
    )
    assert response['Count'] == 1


@mock_dynamodb2
def test_scan_filter3():
    client = boto3.client('dynamodb', region_name='us-east-1')
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    client.create_table(
        TableName='test1',
        AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'N'}],
        KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
        ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123}
    )
    client.put_item(
        TableName='test1',
        Item={
            'client': {'S': 'client1'},
            'app': {'N': '1'},
            'active': {'BOOL': True}
        }
    )

    table = dynamodb.Table('test1')
    response = table.scan(
        FilterExpression=Attr('active').eq(True)
    )
    assert response['Count'] == 1

    response = table.scan(
        FilterExpression=Attr('active').ne(True)
    )
    assert response['Count'] == 0

    response = table.scan(
        FilterExpression=Attr('active').ne(False)
    )
    assert response['Count'] == 1

    response = table.scan(
        FilterExpression=Attr('app').ne(1)
    )
    assert response['Count'] == 0

    response = table.scan(
        FilterExpression=Attr('app').ne(2)
    )
    assert response['Count'] == 1


@mock_dynamodb2
def test_scan_filter4():
    client = boto3.client('dynamodb', region_name='us-east-1')
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    client.create_table(
        TableName='test1',
        AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'N'}],
        KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
        ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123}
    )

    table = dynamodb.Table('test1')
    response = table.scan(
        FilterExpression=Attr('epoch_ts').lt(7) & Attr('fanout_ts').not_exists()
    )
    # Just testing
    assert response['Count'] == 0


@mock_dynamodb2
def test_bad_scan_filter():
    client = boto3.client('dynamodb', region_name='us-east-1')
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    client.create_table(
        TableName='test1',
        AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'S'}],
        KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
        ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123}
    )
    table = dynamodb.Table('test1')

    # Bad expression
    try:
        table.scan(
            FilterExpression='client test'
        )
    except ClientError as err:
        err.response['Error']['Code'].should.equal('ValidationError')
    else:
        raise RuntimeError('Should of raised ResourceInUseException')


@mock_dynamodb2
def test_create_table_pay_per_request():
    client = boto3.client('dynamodb', region_name='us-east-1')
    client.create_table(
        TableName='test1',
        AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'S'}],
        KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
        BillingMode="PAY_PER_REQUEST"
    )


@mock_dynamodb2
def test_create_table_error_pay_per_request_with_provisioned_param():
    client = boto3.client('dynamodb', region_name='us-east-1')

    try:
        client.create_table(
            TableName='test1',
            AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'S'}],
            KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
            ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123},
            BillingMode="PAY_PER_REQUEST"
        )
    except ClientError as err:
        err.response['Error']['Code'].should.equal('ValidationException')


@mock_dynamodb2
def test_duplicate_create():
    client = boto3.client('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    client.create_table(
        TableName='test1',
        AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'S'}],
        KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
        ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123}
    )

    try:
        client.create_table(
            TableName='test1',
            AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'S'}],
            KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
            ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123}
        )
    except ClientError as err:
        err.response['Error']['Code'].should.equal('ResourceInUseException')
    else:
        raise RuntimeError('Should of raised ResourceInUseException')


@mock_dynamodb2
def test_delete_table():
    client = boto3.client('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    client.create_table(
        TableName='test1',
        AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'S'}],
        KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
        ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123}
    )

    client.delete_table(TableName='test1')

    resp = client.list_tables()
    len(resp['TableNames']).should.equal(0)

    try:
        client.delete_table(TableName='test1')
    except ClientError as err:
        err.response['Error']['Code'].should.equal('ResourceNotFoundException')
    else:
        raise RuntimeError('Should of raised ResourceNotFoundException')


@mock_dynamodb2
def test_delete_item():
    client = boto3.client('dynamodb', region_name='us-east-1')
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    client.create_table(
        TableName='test1',
        AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'S'}],
        KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
        ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123}
    )
    client.put_item(
        TableName='test1',
        Item={
            'client': {'S': 'client1'},
            'app': {'S': 'app1'}
        }
    )
    client.put_item(
        TableName='test1',
        Item={
            'client': {'S': 'client1'},
            'app': {'S': 'app2'}
        }
    )

    table = dynamodb.Table('test1')
    response = table.scan()
    assert response['Count'] == 2

    # Test ReturnValues validation
    with assert_raises(ClientError) as ex:
        table.delete_item(Key={'client': 'client1', 'app': 'app1'},
                          ReturnValues='ALL_NEW')

    # Test deletion and returning old value
    response = table.delete_item(Key={'client': 'client1', 'app': 'app1'}, ReturnValues='ALL_OLD')
    response['Attributes'].should.contain('client')
    response['Attributes'].should.contain('app')

    response = table.scan()
    assert response['Count'] == 1

    # Test deletion returning nothing
    response = table.delete_item(Key={'client': 'client1', 'app': 'app2'})
    len(response['Attributes']).should.equal(0)

    response = table.scan()
    assert response['Count'] == 0


@mock_dynamodb2
def test_describe_limits():
    client = boto3.client('dynamodb', region_name='eu-central-1')
    resp = client.describe_limits()

    resp['AccountMaxReadCapacityUnits'].should.equal(20000)
    resp['AccountMaxWriteCapacityUnits'].should.equal(20000)
    resp['TableMaxWriteCapacityUnits'].should.equal(10000)
    resp['TableMaxReadCapacityUnits'].should.equal(10000)


@mock_dynamodb2
def test_set_ttl():
    client = boto3.client('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    client.create_table(
        TableName='test1',
        AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'S'}],
        KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
        ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123}
    )

    client.update_time_to_live(
        TableName='test1',
        TimeToLiveSpecification={
            'Enabled': True,
            'AttributeName': 'expire'
        }
    )

    resp = client.describe_time_to_live(TableName='test1')
    resp['TimeToLiveDescription']['TimeToLiveStatus'].should.equal('ENABLED')
    resp['TimeToLiveDescription']['AttributeName'].should.equal('expire')

    client.update_time_to_live(
        TableName='test1',
        TimeToLiveSpecification={
            'Enabled': False,
            'AttributeName': 'expire'
        }
    )

    resp = client.describe_time_to_live(TableName='test1')
    resp['TimeToLiveDescription']['TimeToLiveStatus'].should.equal('DISABLED')


# https://github.com/spulec/moto/issues/1043
@mock_dynamodb2
def test_query_missing_expr_names():
    client = boto3.client('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    client.create_table(
        TableName='test1',
        AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'S'}],
        KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
        ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123}
    )
    client.put_item(TableName='test1', Item={'client': {'S': 'test1'}, 'app': {'S': 'test1'}})
    client.put_item(TableName='test1', Item={'client': {'S': 'test2'}, 'app': {'S': 'test2'}})

    resp = client.query(TableName='test1', KeyConditionExpression='client=:client',
                        ExpressionAttributeValues={':client': {'S': 'test1'}})

    resp['Count'].should.equal(1)
    resp['Items'][0]['client']['S'].should.equal('test1')

    resp = client.query(TableName='test1', KeyConditionExpression=':name=test2',
                        ExpressionAttributeNames={':name': 'client'})

    resp['Count'].should.equal(1)
    resp['Items'][0]['client']['S'].should.equal('test2')


# https://github.com/spulec/moto/issues/2328
@mock_dynamodb2
def test_update_item_with_list():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    dynamodb.create_table(
        TableName='Table',
        KeySchema=[
            {
                'AttributeName': 'key',
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'key',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        }
    )
    table = dynamodb.Table('Table')
    table.update_item(
        Key={'key': 'the-key'},
        AttributeUpdates={
            'list': {'Value': [1, 2], 'Action': 'PUT'}
        }
    )

    resp = table.get_item(Key={'key': 'the-key'})
    resp['Item'].should.equal({
        'key': 'the-key',
        'list': [1, 2]
    })


# https://github.com/spulec/moto/issues/1342
@mock_dynamodb2
def test_update_item_on_map():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    client = boto3.client('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'forum_name',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'subject',
                'KeyType': 'RANGE'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'forum_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'subject',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    table = dynamodb.Table('users')

    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '123',
        'body': {'nested': {'data': 'test'}},
    })

    resp = table.scan()
    resp['Items'][0]['body'].should.equal({'nested': {'data': 'test'}})

    # Nonexistent nested attributes are supported for existing top-level attributes.
    table.update_item(Key={
        'forum_name': 'the-key',
        'subject': '123'
        },
        UpdateExpression='SET body.#nested.#data = :tb, body.nested.#nonexistentnested.#data = :tb2',
        ExpressionAttributeNames={
            '#nested': 'nested',
            '#nonexistentnested': 'nonexistentnested',
            '#data': 'data'
        },
        ExpressionAttributeValues={
            ':tb': 'new_value',
            ':tb2': 'other_value'
    })

    resp = table.scan()
    resp['Items'][0]['body'].should.equal({
        'nested': {
            'data': 'new_value',
            'nonexistentnested': {'data': 'other_value'}
        }
    })

    # Test nested value for a nonexistent attribute.
    with assert_raises(client.exceptions.ConditionalCheckFailedException):
        table.update_item(Key={
            'forum_name': 'the-key',
            'subject': '123'
            },
            UpdateExpression='SET nonexistent.#nested = :tb',
            ExpressionAttributeNames={
                '#nested': 'nested'
            },
            ExpressionAttributeValues={
                ':tb': 'new_value'
        })



# https://github.com/spulec/moto/issues/1358
@mock_dynamodb2
def test_update_if_not_exists():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'forum_name',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'subject',
                'KeyType': 'RANGE'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'forum_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'subject',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    table = dynamodb.Table('users')

    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '123'
    })

    table.update_item(Key={
        'forum_name': 'the-key',
        'subject': '123'
        },
        # if_not_exists without space
        UpdateExpression='SET created_at=if_not_exists(created_at,:created_at)',
        ExpressionAttributeValues={
            ':created_at': 123
        }
    )

    resp = table.scan()
    assert resp['Items'][0]['created_at'] == 123

    table.update_item(Key={
        'forum_name': 'the-key',
        'subject': '123'
        },
        # if_not_exists with space
        UpdateExpression='SET created_at = if_not_exists (created_at, :created_at)',
        ExpressionAttributeValues={
            ':created_at': 456
        }
    )

    resp = table.scan()
    # Still the original value
    assert resp['Items'][0]['created_at'] == 123


# https://github.com/spulec/moto/issues/1937
@mock_dynamodb2
def test_update_return_attributes():
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')

    dynamodb.create_table(
        TableName='moto-test',
        KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1}
    )

    def update(col, to, rv):
        return dynamodb.update_item(
            TableName='moto-test',
            Key={'id': {'S': 'foo'}},
            AttributeUpdates={col: {'Value': {'S': to}, 'Action': 'PUT'}},
            ReturnValues=rv
        )

    r = update('col1', 'val1', 'ALL_NEW')
    assert r['Attributes'] == {'id': {'S': 'foo'}, 'col1': {'S': 'val1'}}

    r = update('col1', 'val2', 'ALL_OLD')
    assert r['Attributes'] == {'id': {'S': 'foo'}, 'col1': {'S': 'val1'}}

    r = update('col2', 'val3', 'UPDATED_NEW')
    assert r['Attributes'] == {'col2': {'S': 'val3'}}

    r = update('col2', 'val4', 'UPDATED_OLD')
    assert r['Attributes'] == {'col2': {'S': 'val3'}}

    r = update('col1', 'val5', 'NONE')
    assert r['Attributes'] == {}

    with assert_raises(ClientError) as ex:
        r = update('col1', 'val6', 'WRONG')


@mock_dynamodb2
def test_put_return_attributes():
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')

    dynamodb.create_table(
        TableName='moto-test',
        KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1}
    )

    r = dynamodb.put_item(
        TableName='moto-test',
        Item={'id': {'S': 'foo'}, 'col1': {'S': 'val1'}},
        ReturnValues='NONE'
    )
    assert 'Attributes' not in r

    r = dynamodb.put_item(
        TableName='moto-test',
        Item={'id': {'S': 'foo'}, 'col1': {'S': 'val2'}},
        ReturnValues='ALL_OLD'
    )
    assert r['Attributes'] == {'id': {'S': 'foo'}, 'col1': {'S': 'val1'}}

    with assert_raises(ClientError) as ex:
        dynamodb.put_item(
            TableName='moto-test',
            Item={'id': {'S': 'foo'}, 'col1': {'S': 'val3'}},
            ReturnValues='ALL_NEW'
        )
    ex.exception.response['Error']['Code'].should.equal('ValidationException')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(400)
    ex.exception.response['Error']['Message'].should.equal('Return values set to invalid value')


@mock_dynamodb2
def test_query_global_secondary_index_when_created_via_update_table_resource():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'user_id',
                'KeyType': 'HASH'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'user_id',
                'AttributeType': 'N',
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        },
    )
    table = dynamodb.Table('users')
    table.update(
        AttributeDefinitions=[
            {
                'AttributeName': 'forum_name',
                'AttributeType': 'S'
            },
        ],
        GlobalSecondaryIndexUpdates=[
            {'Create':
                {
                    'IndexName': 'forum_name_index',
                    'KeySchema': [
                        {
                            'AttributeName': 'forum_name',
                            'KeyType': 'HASH',
                        },
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL',
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    },
                }
            }
        ]
    )

    next_user_id = 1
    for my_forum_name in ['cats', 'dogs']:
        for my_subject in ['my pet is the cutest', 'wow look at what my pet did', "don't you love my pet?"]:
            table.put_item(Item={'user_id': next_user_id, 'forum_name': my_forum_name, 'subject': my_subject})
            next_user_id += 1

    # get all the cat users
    forum_only_query_response = table.query(
        IndexName='forum_name_index',
        Select='ALL_ATTRIBUTES',
        KeyConditionExpression=Key('forum_name').eq('cats'),
    )
    forum_only_items = forum_only_query_response['Items']
    assert len(forum_only_items) == 3
    for item in forum_only_items:
        assert item['forum_name'] == 'cats'

    # query all cat users with a particular subject
    forum_and_subject_query_results = table.query(
        IndexName='forum_name_index',
        Select='ALL_ATTRIBUTES',
        KeyConditionExpression=Key('forum_name').eq('cats'),
        FilterExpression=Attr('subject').eq('my pet is the cutest'),
    )
    forum_and_subject_items = forum_and_subject_query_results['Items']
    assert len(forum_and_subject_items) == 1
    assert forum_and_subject_items[0] == {'user_id': Decimal('1'), 'forum_name': 'cats',
                                          'subject': 'my pet is the cutest'}


@mock_dynamodb2
def test_dynamodb_streams_1():
    conn = boto3.client('dynamodb', region_name='us-east-1')

    resp = conn.create_table(
        TableName='test-streams',
        KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1},
        StreamSpecification={
            'StreamEnabled': True,
            'StreamViewType': 'NEW_AND_OLD_IMAGES'
        }
    )

    assert 'StreamSpecification' in resp['TableDescription']
    assert resp['TableDescription']['StreamSpecification'] == {
        'StreamEnabled': True,
        'StreamViewType': 'NEW_AND_OLD_IMAGES'
    }
    assert 'LatestStreamLabel' in resp['TableDescription']
    assert 'LatestStreamArn' in resp['TableDescription']

    resp = conn.delete_table(TableName='test-streams')

    assert 'StreamSpecification' in resp['TableDescription']


@mock_dynamodb2
def test_dynamodb_streams_2():
    conn = boto3.client('dynamodb', region_name='us-east-1')

    resp = conn.create_table(
        TableName='test-stream-update',
        KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1},
    )

    assert 'StreamSpecification' not in resp['TableDescription']

    resp = conn.update_table(
        TableName='test-stream-update',
        StreamSpecification={
            'StreamEnabled': True,
            'StreamViewType': 'NEW_IMAGE'
        }
    )

    assert 'StreamSpecification' in resp['TableDescription']
    assert resp['TableDescription']['StreamSpecification'] == {
        'StreamEnabled': True,
        'StreamViewType': 'NEW_IMAGE'
    }
    assert 'LatestStreamLabel' in resp['TableDescription']
    assert 'LatestStreamArn' in resp['TableDescription']


@mock_dynamodb2
def test_condition_expressions():
    client = boto3.client('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    client.create_table(
        TableName='test1',
        AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'S'}],
        KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
        ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123}
    )
    client.put_item(
        TableName='test1',
        Item={
            'client': {'S': 'client1'},
            'app': {'S': 'app1'},
            'match': {'S': 'match'},
            'existing': {'S': 'existing'},
        }
    )

    client.put_item(
        TableName='test1',
        Item={
            'client': {'S': 'client1'},
            'app': {'S': 'app1'},
            'match': {'S': 'match'},
            'existing': {'S': 'existing'},
        },
        ConditionExpression='attribute_exists(#existing) AND attribute_not_exists(#nonexistent) AND #match = :match',
        ExpressionAttributeNames={
            '#existing': 'existing',
            '#nonexistent': 'nope',
            '#match': 'match',
        },
        ExpressionAttributeValues={
            ':match': {'S': 'match'}
        }
    )

    client.put_item(
        TableName='test1',
        Item={
            'client': {'S': 'client1'},
            'app': {'S': 'app1'},
            'match': {'S': 'match'},
            'existing': {'S': 'existing'},
        },
        ConditionExpression='NOT(attribute_exists(#nonexistent1) AND attribute_exists(#nonexistent2))',
        ExpressionAttributeNames={
            '#nonexistent1': 'nope',
            '#nonexistent2': 'nope2'
        }
    )

    client.put_item(
        TableName='test1',
        Item={
            'client': {'S': 'client1'},
            'app': {'S': 'app1'},
            'match': {'S': 'match'},
            'existing': {'S': 'existing'},
        },
        ConditionExpression='attribute_exists(#nonexistent) OR attribute_exists(#existing)',
        ExpressionAttributeNames={
            '#nonexistent': 'nope',
            '#existing': 'existing'
        }
    )

    client.put_item(
        TableName='test1',
        Item={
            'client': {'S': 'client1'},
            'app': {'S': 'app1'},
            'match': {'S': 'match'},
            'existing': {'S': 'existing'},
        },
        ConditionExpression='#client BETWEEN :a AND :z',
        ExpressionAttributeNames={
            '#client': 'client',
        },
        ExpressionAttributeValues={
            ':a': {'S': 'a'},
            ':z': {'S': 'z'},
        }
    )

    client.put_item(
        TableName='test1',
        Item={
            'client': {'S': 'client1'},
            'app': {'S': 'app1'},
            'match': {'S': 'match'},
            'existing': {'S': 'existing'},
        },
        ConditionExpression='#client IN (:client1, :client2)',
        ExpressionAttributeNames={
            '#client': 'client',
        },
        ExpressionAttributeValues={
            ':client1': {'S': 'client1'},
            ':client2': {'S': 'client2'},
        }
    )

    with assert_raises(client.exceptions.ConditionalCheckFailedException):
        client.put_item(
            TableName='test1',
            Item={
                'client': {'S': 'client1'},
                'app': {'S': 'app1'},
                'match': {'S': 'match'},
                'existing': {'S': 'existing'},
            },
            ConditionExpression='attribute_exists(#nonexistent1) AND attribute_exists(#nonexistent2)',
            ExpressionAttributeNames={
                '#nonexistent1': 'nope',
                '#nonexistent2': 'nope2'
            }
        )

    with assert_raises(client.exceptions.ConditionalCheckFailedException):
        client.put_item(
            TableName='test1',
            Item={
                'client': {'S': 'client1'},
                'app': {'S': 'app1'},
                'match': {'S': 'match'},
                'existing': {'S': 'existing'},
            },
            ConditionExpression='NOT(attribute_not_exists(#nonexistent1) AND attribute_not_exists(#nonexistent2))',
            ExpressionAttributeNames={
                '#nonexistent1': 'nope',
                '#nonexistent2': 'nope2'
            }
        )

    with assert_raises(client.exceptions.ConditionalCheckFailedException):
        client.put_item(
            TableName='test1',
            Item={
                'client': {'S': 'client1'},
                'app': {'S': 'app1'},
                'match': {'S': 'match'},
                'existing': {'S': 'existing'},
            },
            ConditionExpression='attribute_exists(#existing) AND attribute_not_exists(#nonexistent) AND #match = :match',
            ExpressionAttributeNames={
                '#existing': 'existing',
                '#nonexistent': 'nope',
                '#match': 'match',
            },
            ExpressionAttributeValues={
                ':match': {'S': 'match2'}
            }
        )

    # Make sure update_item honors ConditionExpression as well
    client.update_item(
        TableName='test1',
        Key={
            'client': {'S': 'client1'},
            'app': {'S': 'app1'},
        },
        UpdateExpression='set #match=:match',
        ConditionExpression='attribute_exists(#existing)',
        ExpressionAttributeNames={
            '#existing': 'existing',
            '#match': 'match',
        },
        ExpressionAttributeValues={
            ':match': {'S': 'match'}
        }
    )

    with assert_raises(client.exceptions.ConditionalCheckFailedException):
        client.update_item(
            TableName='test1',
            Key={
                'client': { 'S': 'client1'},
                'app': { 'S': 'app1'},
            },
            UpdateExpression='set #match=:match',
            ConditionExpression='attribute_not_exists(#existing)',
            ExpressionAttributeValues={
                ':match': {'S': 'match'}
            },
            ExpressionAttributeNames={
                '#existing': 'existing',
                '#match': 'match',
            },
        )

    with assert_raises(client.exceptions.ConditionalCheckFailedException):
        client.delete_item(
            TableName = 'test1',
            Key = {
                'client': {'S': 'client1'},
                'app': {'S': 'app1'},
            },
            ConditionExpression = 'attribute_not_exists(#existing)',
            ExpressionAttributeValues = {
                ':match': {'S': 'match'}
            },
            ExpressionAttributeNames = {
                '#existing': 'existing',
                '#match': 'match',
            },
        )


@mock_dynamodb2
def test_condition_expression__attr_doesnt_exist():
    client = boto3.client('dynamodb', region_name='us-east-1')

    client.create_table(
        TableName='test',
        KeySchema=[{'AttributeName': 'forum_name', 'KeyType': 'HASH'}],
        AttributeDefinitions=[
            {'AttributeName': 'forum_name', 'AttributeType': 'S'},
        ],
        ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1},
    )

    client.put_item(
        TableName='test',
        Item={
            'forum_name': {'S': 'foo'},
            'ttl': {'N': 'bar'},
        }
    )


    def update_if_attr_doesnt_exist():
        # Test nonexistent top-level attribute.
        client.update_item(
            TableName='test',
            Key={
                'forum_name': {'S': 'the-key'},
                'subject': {'S': 'the-subject'},
            },
            UpdateExpression='set #new_state=:new_state, #ttl=:ttl',
            ConditionExpression='attribute_not_exists(#new_state)',
            ExpressionAttributeNames={'#new_state': 'foobar', '#ttl': 'ttl'},
            ExpressionAttributeValues={
                ':new_state': {'S': 'some-value'},
                ':ttl': {'N': '12345.67'},
            },
            ReturnValues='ALL_NEW',
        )

    update_if_attr_doesnt_exist()

    # Second time should fail
    with assert_raises(client.exceptions.ConditionalCheckFailedException):
        update_if_attr_doesnt_exist()


@mock_dynamodb2
def test_condition_expression__or_order():
    client = boto3.client('dynamodb', region_name='us-east-1')

    client.create_table(
        TableName='test',
        KeySchema=[{'AttributeName': 'forum_name', 'KeyType': 'HASH'}],
        AttributeDefinitions=[
            {'AttributeName': 'forum_name', 'AttributeType': 'S'},
        ],
        ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1},
    )

    # ensure that the RHS of the OR expression is not evaluated if the LHS
    # returns true (as it would result an error)
    client.update_item(
        TableName='test',
        Key={
            'forum_name': {'S': 'the-key'},
        },
        UpdateExpression='set #ttl=:ttl',
        ConditionExpression='attribute_not_exists(#ttl) OR #ttl <= :old_ttl',
        ExpressionAttributeNames={'#ttl': 'ttl'},
        ExpressionAttributeValues={
            ':ttl': {'N': '6'},
            ':old_ttl': {'N': '5'},
        }
    )


@mock_dynamodb2
def test_condition_expression__and_order():
    client = boto3.client('dynamodb', region_name='us-east-1')

    client.create_table(
        TableName='test',
        KeySchema=[{'AttributeName': 'forum_name', 'KeyType': 'HASH'}],
        AttributeDefinitions=[
            {'AttributeName': 'forum_name', 'AttributeType': 'S'},
        ],
        ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1},
    )
    
    # ensure that the RHS of the AND expression is not evaluated if the LHS
    # returns true (as it would result an error)
    with assert_raises(client.exceptions.ConditionalCheckFailedException):
        client.update_item(
            TableName='test',
            Key={
                'forum_name': {'S': 'the-key'},
            },
            UpdateExpression='set #ttl=:ttl',
            ConditionExpression='attribute_exists(#ttl) AND #ttl <= :old_ttl',
            ExpressionAttributeNames={'#ttl': 'ttl'},
            ExpressionAttributeValues={
                ':ttl': {'N': '6'},
                ':old_ttl': {'N': '5'},
            }
        )

@mock_dynamodb2
def test_query_gsi_with_range_key():
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')
    dynamodb.create_table(
        TableName='test',
        KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'gsi_hash_key', 'AttributeType': 'S'},
            {'AttributeName': 'gsi_range_key', 'AttributeType': 'S'}
        ],
        ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1},
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'test_gsi',
                'KeySchema': [
                    {
                        'AttributeName': 'gsi_hash_key',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'gsi_range_key',
                        'KeyType': 'RANGE'
                    },
                ],
                'Projection': {
                    'ProjectionType': 'ALL',
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 1,
                    'WriteCapacityUnits': 1
                }
            },
        ]
    )

    dynamodb.put_item(
        TableName='test',
        Item={
            'id': {'S': 'test1'},
            'gsi_hash_key': {'S': 'key1'},
            'gsi_range_key': {'S': 'range1'},
        }
    )
    dynamodb.put_item(
        TableName='test',
        Item={
            'id': {'S': 'test2'},
            'gsi_hash_key': {'S': 'key1'},
        }
    )

    res = dynamodb.query(TableName='test', IndexName='test_gsi',
                         KeyConditionExpression='gsi_hash_key = :gsi_hash_key AND gsi_range_key = :gsi_range_key',
                         ExpressionAttributeValues={
                             ':gsi_hash_key': {'S': 'key1'},
                             ':gsi_range_key': {'S': 'range1'}
                         })
    res.should.have.key("Count").equal(1)
    res.should.have.key("Items")
    res['Items'][0].should.equal({
        'id': {'S': 'test1'},
        'gsi_hash_key': {'S': 'key1'},
        'gsi_range_key': {'S': 'range1'},
    })


@mock_dynamodb2
def test_scan_by_non_exists_index():
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')

    dynamodb.create_table(
        TableName='test',
        KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'gsi_col', 'AttributeType': 'S'}
        ],
        ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1},
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'test_gsi',
                'KeySchema': [
                    {
                        'AttributeName': 'gsi_col',
                        'KeyType': 'HASH'
                    },
                ],
                'Projection': {
                    'ProjectionType': 'ALL',
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 1,
                    'WriteCapacityUnits': 1
                }
            },
        ]
    )

    with assert_raises(ClientError) as ex:
        dynamodb.scan(TableName='test', IndexName='non_exists_index')

    ex.exception.response['Error']['Code'].should.equal('ValidationException')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(400)
    ex.exception.response['Error']['Message'].should.equal(
        'The table does not have the specified index: non_exists_index'
    )


@mock_dynamodb2
def test_batch_items_returns_all():
    dynamodb = _create_user_table()
    returned_items = dynamodb.batch_get_item(RequestItems={
        'users': {
            'Keys': [{
                'username': {'S': 'user0'}
            }, {
                'username': {'S': 'user1'}
            }, {
                'username': {'S': 'user2'}
            }, {
                'username': {'S': 'user3'}
            }],
            'ConsistentRead': True
        }
    })['Responses']['users']
    assert len(returned_items) == 3
    assert [item['username']['S'] for item in returned_items] == ['user1', 'user2', 'user3']


@mock_dynamodb2
def test_batch_items_with_basic_projection_expression():
    dynamodb = _create_user_table()
    returned_items = dynamodb.batch_get_item(RequestItems={
        'users': {
            'Keys': [{
                'username': {'S': 'user0'}
            }, {
                'username': {'S': 'user1'}
            }, {
                'username': {'S': 'user2'}
            }, {
                'username': {'S': 'user3'}
            }],
            'ConsistentRead': True,
            'ProjectionExpression': 'username'
        }
    })['Responses']['users']

    returned_items.should.have.length_of(3)
    [item['username']['S'] for item in returned_items].should.be.equal(['user1', 'user2', 'user3'])
    [item.get('foo') for item in returned_items].should.be.equal([None, None, None])

    # The projection expression should not remove data from storage
    returned_items = dynamodb.batch_get_item(RequestItems = {
        'users': {
            'Keys': [{
                'username': {'S': 'user0'}
            }, {
                'username': {'S': 'user1'}
            }, {
                'username': {'S': 'user2'}
            }, {
                'username': {'S': 'user3'}
            }],
            'ConsistentRead': True
        }
    })['Responses']['users']

    [item['username']['S'] for item in returned_items].should.be.equal(['user1', 'user2', 'user3'])
    [item['foo']['S'] for item in returned_items].should.be.equal(['bar', 'bar', 'bar'])


@mock_dynamodb2
def test_batch_items_with_basic_projection_expression_and_attr_expression_names():
    dynamodb = _create_user_table()
    returned_items = dynamodb.batch_get_item(RequestItems={
        'users': {
            'Keys': [{
                'username': {'S': 'user0'}
            }, {
                'username': {'S': 'user1'}
            }, {
                'username': {'S': 'user2'}
            }, {
                'username': {'S': 'user3'}
            }],
            'ConsistentRead': True,
            'ProjectionExpression': '#rl',
            'ExpressionAttributeNames': {
                '#rl': 'username'
            },
        }
    })['Responses']['users']

    returned_items.should.have.length_of(3)
    [item['username']['S'] for item in returned_items].should.be.equal(['user1', 'user2', 'user3'])
    [item.get('foo') for item in returned_items].should.be.equal([None, None, None])


@mock_dynamodb2
def test_batch_items_should_throw_exception_for_duplicate_request():
    client = _create_user_table()
    with assert_raises(ClientError) as ex:
        client.batch_get_item(RequestItems={
            'users': {
                'Keys': [{
                    'username': {'S': 'user0'}
                }, {
                    'username': {'S': 'user0'}
                }],
                'ConsistentRead': True
            }})
    ex.exception.response['Error']['Code'].should.equal('ValidationException')
    ex.exception.response['Error']['Message'].should.equal('Provided list of item keys contains duplicates')


@mock_dynamodb2
def test_index_with_unknown_attributes_should_fail():
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')

    expected_exception = 'Some index key attributes are not defined in AttributeDefinitions.'

    with assert_raises(ClientError) as ex:
        dynamodb.create_table(
            AttributeDefinitions=[
                {'AttributeName': 'customer_nr', 'AttributeType': 'S'},
                {'AttributeName': 'last_name', 'AttributeType': 'S'}],
            TableName='table_with_missing_attribute_definitions',
            KeySchema=[
                {'AttributeName': 'customer_nr', 'KeyType': 'HASH'},
                {'AttributeName': 'last_name', 'KeyType': 'RANGE'}],
            LocalSecondaryIndexes=[{
                'IndexName': 'indexthataddsanadditionalattribute',
                'KeySchema': [
                    {'AttributeName': 'customer_nr', 'KeyType': 'HASH'},
                    {'AttributeName': 'postcode', 'KeyType': 'RANGE'}],
                'Projection': { 'ProjectionType': 'ALL' }
            }],
            BillingMode='PAY_PER_REQUEST')

    ex.exception.response['Error']['Code'].should.equal('ValidationException')
    ex.exception.response['Error']['Message'].should.contain(expected_exception)


@mock_dynamodb2
def test_update_list_index__set_existing_index():
    table_name = 'test_list_index_access'
    client = create_table_with_list(table_name)
    client.update_item(TableName=table_name, Key={'id': {'S': 'foo'}},
                       UpdateExpression='set itemlist[1]=:Item',
                       ExpressionAttributeValues={':Item': {'S': 'bar2_update'}})
    #
    result = client.get_item(TableName=table_name, Key={'id': {'S': 'foo'}})['Item']
    assert result['id'] == {'S': 'foo'}
    assert result['itemlist'] == {'L': [{'S': 'bar1'}, {'S': 'bar2_update'}, {'S': 'bar3'}]}


@mock_dynamodb2
def test_update_list_index__set_existing_nested_index():
    table_name = 'test_list_index_access'
    client = create_table_with_list(table_name)
    client.put_item(TableName=table_name,
                    Item={'id': {'S': 'foo2'}, 'itemmap': {'M': {'itemlist': {'L': [{'S': 'bar1'}, {'S': 'bar2'}, {'S': 'bar3'}]}}}})
    client.update_item(TableName=table_name, Key={'id': {'S': 'foo2'}},
                       UpdateExpression='set itemmap.itemlist[1]=:Item',
                       ExpressionAttributeValues={':Item': {'S': 'bar2_update'}})
    #
    result = client.get_item(TableName=table_name, Key={'id': {'S': 'foo2'}})['Item']
    assert result['id'] == {'S': 'foo2'}
    assert result['itemmap']['M']['itemlist']['L'] == [{'S': 'bar1'}, {'S': 'bar2_update'}, {'S': 'bar3'}]


@mock_dynamodb2
def test_update_list_index__set_index_out_of_range():
    table_name = 'test_list_index_access'
    client = create_table_with_list(table_name)
    client.update_item(TableName=table_name, Key={'id': {'S': 'foo'}},
                       UpdateExpression='set itemlist[10]=:Item',
                       ExpressionAttributeValues={':Item': {'S': 'bar10'}})
    #
    result = client.get_item(TableName=table_name, Key={'id': {'S': 'foo'}})['Item']
    assert result['id'] == {'S': 'foo'}
    assert result['itemlist'] == {'L': [{'S': 'bar1'}, {'S': 'bar2'}, {'S': 'bar3'}, {'S': 'bar10'}]}


@mock_dynamodb2
def test_update_list_index__set_nested_index_out_of_range():
    table_name = 'test_list_index_access'
    client = create_table_with_list(table_name)
    client.put_item(TableName=table_name,
                    Item={'id': {'S': 'foo2'}, 'itemmap': {'M': {'itemlist': {'L': [{'S': 'bar1'}, {'S': 'bar2'}, {'S': 'bar3'}]}}}})
    client.update_item(TableName=table_name, Key={'id': {'S': 'foo2'}},
                       UpdateExpression='set itemmap.itemlist[10]=:Item',
                       ExpressionAttributeValues={':Item': {'S': 'bar10'}})
    #
    result = client.get_item(TableName=table_name, Key={'id': {'S': 'foo2'}})['Item']
    assert result['id'] == {'S': 'foo2'}
    assert result['itemmap']['M']['itemlist']['L'] == [{'S': 'bar1'}, {'S': 'bar2'}, {'S': 'bar3'}, {'S': 'bar10'}]


@mock_dynamodb2
def test_update_list_index__set_index_of_a_string():
    table_name = 'test_list_index_access'
    client = create_table_with_list(table_name)
    client.put_item(TableName=table_name, Item={'id': {'S': 'foo2'}, 'itemstr': {'S': 'somestring'}})
    with assert_raises(ClientError) as ex:
        client.update_item(TableName=table_name, Key={'id': {'S': 'foo2'}},
                           UpdateExpression='set itemstr[1]=:Item',
                           ExpressionAttributeValues={':Item': {'S': 'string_update'}})
        result = client.get_item(TableName=table_name, Key={'id': {'S': 'foo2'}})['Item']

    ex.exception.response['Error']['Code'].should.equal('ValidationException')
    ex.exception.response['Error']['Message'].should.equal(
        'The document path provided in the update expression is invalid for update')


@mock_dynamodb2
def test_remove_list_index__remove_existing_index():
    table_name = 'test_list_index_access'
    client = create_table_with_list(table_name)
    client.update_item(TableName=table_name, Key={'id': {'S': 'foo'}}, UpdateExpression='REMOVE itemlist[1]')
    #
    result = client.get_item(TableName=table_name, Key={'id': {'S': 'foo'}})['Item']
    assert result['id'] == {'S': 'foo'}
    assert result['itemlist'] == {'L': [{'S': 'bar1'}, {'S': 'bar3'}]}


@mock_dynamodb2
def test_remove_list_index__remove_existing_nested_index():
    table_name = 'test_list_index_access'
    client = create_table_with_list(table_name)
    client.put_item(TableName=table_name,
                    Item={'id': {'S': 'foo2'}, 'itemmap': {'M': {'itemlist': {'L': [{'S': 'bar1'}, {'S': 'bar2'}]}}}})
    client.update_item(TableName=table_name, Key={'id': {'S': 'foo2'}}, UpdateExpression='REMOVE itemmap.itemlist[1]')
    #
    result = client.get_item(TableName=table_name, Key={'id': {'S': 'foo2'}})['Item']
    assert result['id'] == {'S': 'foo2'}
    assert result['itemmap']['M']['itemlist']['L'] == [{'S': 'bar1'}]


@mock_dynamodb2
def test_remove_list_index__remove_existing_double_nested_index():
    table_name = 'test_list_index_access'
    client = create_table_with_list(table_name)
    client.put_item(TableName=table_name,
                    Item={'id': {'S': 'foo2'},
                          'itemmap': {'M': {'itemlist': {'L': [{'M': {'foo00': {'S': 'bar1'},
                                                                      'foo01': {'S': 'bar2'}}},
                                                               {'M': {'foo10': {'S': 'bar1'},
                                                                      'foo11': {'S': 'bar2'}}}]}}}})
    client.update_item(TableName=table_name, Key={'id': {'S': 'foo2'}},
                       UpdateExpression='REMOVE itemmap.itemlist[1].foo10')
    #
    result = client.get_item(TableName=table_name, Key={'id': {'S': 'foo2'}})['Item']
    assert result['id'] == {'S': 'foo2'}
    assert result['itemmap']['M']['itemlist']['L'][0]['M'].should.equal({'foo00': {'S': 'bar1'},
                                                                         'foo01': {'S': 'bar2'}})  # untouched
    assert result['itemmap']['M']['itemlist']['L'][1]['M'].should.equal({'foo11': {'S': 'bar2'}})  # changed


@mock_dynamodb2
def test_remove_list_index__remove_index_out_of_range():
    table_name = 'test_list_index_access'
    client = create_table_with_list(table_name)
    client.update_item(TableName=table_name, Key={'id': {'S': 'foo'}}, UpdateExpression='REMOVE itemlist[10]')
    #
    result = client.get_item(TableName=table_name, Key={'id': {'S': 'foo'}})['Item']
    assert result['id'] == {'S': 'foo'}
    assert result['itemlist'] == {'L': [{'S': 'bar1'}, {'S': 'bar2'}, {'S': 'bar3'}]}


def create_table_with_list(table_name):
    client = boto3.client('dynamodb', region_name='us-east-1')
    client.create_table(TableName=table_name,
                        KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
                        AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
                        BillingMode='PAY_PER_REQUEST')
    client.put_item(TableName=table_name,
                    Item={'id': {'S': 'foo'}, 'itemlist': {'L': [{'S': 'bar1'}, {'S': 'bar2'}, {'S': 'bar3'}]}})
    return client


@mock_dynamodb2
def test_sorted_query_with_numerical_sort_key():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    dynamodb.create_table(TableName="CarCollection",
                          KeySchema=[{ 'AttributeName': "CarModel", 'KeyType': 'HASH'},
                                     {'AttributeName': "CarPrice", 'KeyType': 'RANGE'}],
                          AttributeDefinitions=[{'AttributeName': "CarModel", 'AttributeType': "S"},
                                                {'AttributeName': "CarPrice", 'AttributeType': "N"}],
                          ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1})

    def create_item(price):
        return {"CarModel": "M", "CarPrice": price}

    table = dynamodb.Table('CarCollection')
    items = list(map(create_item, [2, 1, 10, 3]))
    for item in items:
        table.put_item(Item=item)

    response = table.query(KeyConditionExpression=Key('CarModel').eq("M"))

    response_items = response['Items']
    assert len(items) == len(response_items)
    assert all(isinstance(item["CarPrice"], Decimal) for item in response_items)
    response_prices = [item["CarPrice"] for item in response_items]
    expected_prices = [Decimal(item["CarPrice"]) for item in items]
    expected_prices.sort()
    assert expected_prices == response_prices, "result items are not sorted by numerical value"


# https://github.com/spulec/moto/issues/1874
@mock_dynamodb2
def test_item_size_is_under_400KB():
    dynamodb = boto3.resource('dynamodb')
    client = boto3.client('dynamodb')

    dynamodb.create_table(
        TableName='moto-test',
        KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1}
    )
    table = dynamodb.Table('moto-test')

    large_item = 'x' * 410 * 1000
    assert_failure_due_to_item_size(func=client.put_item,
                                    TableName='moto-test',
                                    Item={'id': {'S': 'foo'}, 'item': {'S': large_item}})
    assert_failure_due_to_item_size(func=table.put_item, Item = {'id': 'bar', 'item': large_item})
    assert_failure_due_to_item_size(func=client.update_item,
                                    TableName='moto-test',
                                    Key={'id': {'S': 'foo2'}},
                                    UpdateExpression='set item=:Item',
                                    ExpressionAttributeValues={':Item': {'S': large_item}})
    # Assert op fails when updating a nested item
    assert_failure_due_to_item_size(func=table.put_item,
                                    Item={'id': 'bar', 'itemlist': [{'item': large_item}]})
    assert_failure_due_to_item_size(func=client.put_item,
                                    TableName='moto-test',
                                    Item={'id': {'S': 'foo'}, 'itemlist': {'L': [{'M': {'item1': {'S': large_item}}}]}})


def assert_failure_due_to_item_size(func, **kwargs):
    with assert_raises(ClientError) as ex:
        func(**kwargs)
    ex.exception.response['Error']['Code'].should.equal('ValidationException')
    ex.exception.response['Error']['Message'].should.equal('Item size has exceeded the maximum allowed size')


def _create_user_table():
    client = boto3.client('dynamodb', region_name='us-east-1')
    client.create_table(
        TableName='users',
        KeySchema=[{'AttributeName': 'username', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'username', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
    )
    client.put_item(TableName='users', Item={'username': {'S': 'user1'}, 'foo': {'S': 'bar'}})
    client.put_item(TableName='users', Item={'username': {'S': 'user2'}, 'foo': {'S': 'bar'}})
    client.put_item(TableName='users', Item={'username': {'S': 'user3'}, 'foo': {'S': 'bar'}})
    return client
