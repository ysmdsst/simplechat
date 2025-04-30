# # lambda/index.py
# import json
# import os
# import boto3
# import re  # 正規表現モジュールをインポート
# from botocore.exceptions import ClientError


# # Lambda コンテキストからリージョンを抽出する関数
# def extract_region_from_arn(arn):
#     # ARN 形式: arn:aws:lambda:region:account-id:function:function-name
#     match = re.search('arn:aws:lambda:([^:]+):', arn)
#     if match:
#         return match.group(1)
#     return "us-east-1"  # デフォルト値

# # グローバル変数としてクライアントを初期化（初期値）
# bedrock_client = None

# # モデルID
# MODEL_ID = os.environ.get("MODEL_ID", "us.amazon.nova-lite-v1:0")

# def lambda_handler(event, context):
#     try:
#         # コンテキストから実行リージョンを取得し、クライアントを初期化
#         global bedrock_client
#         if bedrock_client is None:
#             region = extract_region_from_arn(context.invoked_function_arn)
#             bedrock_client = boto3.client('bedrock-runtime', region_name=region)
#             print(f"Initialized Bedrock client in region: {region}")
        
#         print("Received event:", json.dumps(event))
        
#         # Cognitoで認証されたユーザー情報を取得
#         user_info = None
#         if 'requestContext' in event and 'authorizer' in event['requestContext']:
#             user_info = event['requestContext']['authorizer']['claims']
#             print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
#         # リクエストボディの解析
#         body = json.loads(event['body'])
#         message = body['message']
#         conversation_history = body.get('conversationHistory', [])
        
#         print("Processing message:", message)
#         print("Using model:", MODEL_ID)
        
#         # 会話履歴を使用
#         messages = conversation_history.copy()
        
#         # ユーザーメッセージを追加
#         messages.append({
#             "role": "user",
#             "content": message
#         })
        
#         # Nova Liteモデル用のリクエストペイロードを構築
#         # 会話履歴を含める
#         bedrock_messages = []
#         for msg in messages:
#             if msg["role"] == "user":
#                 bedrock_messages.append({
#                     "role": "user",
#                     "content": [{"text": msg["content"]}]
#                 })
#             elif msg["role"] == "assistant":
#                 bedrock_messages.append({
#                     "role": "assistant", 
#                     "content": [{"text": msg["content"]}]
#                 })
        
#         # invoke_model用のリクエストペイロード
#         request_payload = {
#             "messages": bedrock_messages,
#             "inferenceConfig": {
#                 "maxTokens": 512,
#                 "stopSequences": [],
#                 "temperature": 0.7,
#                 "topP": 0.9
#             }
#         }
        
#         print("Calling Bedrock invoke_model API with payload:", json.dumps(request_payload))
        
#         # invoke_model APIを呼び出し
#         response = bedrock_client.invoke_model(
#             modelId=MODEL_ID,
#             body=json.dumps(request_payload),
#             contentType="application/json"
#         )
        
#         # レスポンスを解析
#         response_body = json.loads(response['body'].read())
#         print("Bedrock response:", json.dumps(response_body, default=str))
        
#         # 応答の検証
#         if not response_body.get('output') or not response_body['output'].get('message') or not response_body['output']['message'].get('content'):
#             raise Exception("No response content from the model")
        
#         # アシスタントの応答を取得
#         assistant_response = response_body['output']['message']['content'][0]['text']
        
#         # アシスタントの応答を会話履歴に追加
#         messages.append({
#             "role": "assistant",
#             "content": assistant_response
#         })
        
#         # 成功レスポンスの返却
#         return {
#             "statusCode": 200,
#             "headers": {
#                 "Content-Type": "application/json",
#                 "Access-Control-Allow-Origin": "*",
#                 "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
#                 "Access-Control-Allow-Methods": "OPTIONS,POST"
#             },
#             "body": json.dumps({
#                 "success": True,
#                 "response": assistant_response,
#                 "conversationHistory": messages
#             })
#         }
        
#     except Exception as error:
#         print("Error:", str(error))
        
#         return {
#             "statusCode": 500,
#             "headers": {
#                 "Content-Type": "application/json",
#                 "Access-Control-Allow-Origin": "*",
#                 "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
#                 "Access-Control-Allow-Methods": "OPTIONS,POST"
#             },
#             "body": json.dumps({
#                 "success": False,
#                 "error": str(error)
#             })
#         }

import json
import os
import urllib.request
import traceback

FASTAPI_URL = "https://2330-35-198-242-173.ngrok-free.app/generate"  

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")

        # イベントのボディを安全に読み込む
        if isinstance(event['body'], str):
            body = json.loads(event['body'])
        else:
            body = event['body']

        message = body['message']  # フロント側から送られるメッセージ
        # conversationHistory = body.get('conversationHistory', [])  # 使用しない場合は省略可能

        print("Sending message to FastAPI server as prompt:", message)

        # FastAPIのモデルに一致するpayloadを構築
        payload = {
            "prompt": message,
            "max_new_tokens": 512,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9
        }

        # POSTリクエストを作成・送信
        req = urllib.request.Request(
            FASTAPI_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        # FastAPIからのレスポンス受信
        with urllib.request.urlopen(req) as res:
            res_body = res.read().decode('utf-8')
            response_json = json.loads(res_body)

        print("Response from FastAPI server:", response_json)

        # レスポンスの取り出し
        assistant_response = response_json.get("generated_text", "")
        # updated_history = conversation_history  # 会話履歴管理が必要なら後ほど実装

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                # "conversationHistory": updated_history  # 会話履歴が必要な場合はこちらも返却
            })
        }

    except Exception as error:
        print("Error:", str(error))
        traceback.print_exc()  # スタックトレースを出力（CloudWatchで詳細確認できる）
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }


