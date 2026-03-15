import boto3
import json

bedrock_client = boto3.client(service_name='bedrock-runtime', region_name='us-east-1')
model_id = 'anthropic.claude-3-5-sonnet-20240620-v1:0'

# Helper function to clean the history for the API
def format_messages_for_bedrock(messages_history):
    formatted_messages = []
    for msg in messages_history:
        content = msg["content"]
        
        # Convert stored JSON objects into a simple string for history
        if isinstance(content, dict):
            # Format the AI's JSON response as a clean string for the history
            clean_content = f"Question: {content.get('next_question', 'N/A')}\nFeedback: {content.get('feedback', 'N/A')}\nScore: {content.get('score', 'N/A')}"
        else:
            # User messages and the first assistant question are already strings
            clean_content = content

        formatted_messages.append({
            "role": msg["role"],
            # The Bedrock messages structure uses "content" which is an array of content blocks
            # But Anthropic's message structure simplifies this for text
            "content": [{"type": "text", "text": clean_content}]
        })
    return formatted_messages


def get_ai_response_text(system_prompt, messages_history):
    """
    Gets a plain TEXT response from Claude.
    """
    # Use the new formatter before sending to Bedrock
    messages_to_send = format_messages_for_bedrock(messages_history) 
    
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2048,
        "system": system_prompt,
        "messages": messages_to_send
    })

    try:
        response = bedrock_client.invoke_model(
            body=body, modelId=model_id,
            accept='application/json', contentType='application/json'
        )
        response_body = json.loads(response.get('body').read())
        # The Anthropic format for text is nested under 'content' and 'text'
        return response_body.get('content', [{}])[0].get('text', '')
    except Exception as e:
        return f"Error: {e}"

def get_ai_response_json(system_prompt, messages_history):
    """
    Gets a structured JSON response from Claude.
    """
    # Use the new formatter before sending to Bedrock
    messages_to_send = format_messages_for_bedrock(messages_history)
    
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "system": system_prompt,
        "messages": messages_to_send
        # Note: Claude 3.5 Sonnet should be instructed to return JSON via the system prompt, 
        # as there is no specific JSON schema flag in the Bedrock API call itself.
    })

    try:
        response = bedrock_client.invoke_model(
            body=body, modelId=model_id,
            accept='application/json', contentType='application/json'
        )
        response_body = json.loads(response.get('body').read())
        # The response is usually a string containing the JSON structure
        json_text = response_body.get('content', [{}])[0].get('text', '{}')
        return json.loads(json_text)
    except Exception as e:
        # Include detailed error in the console for debugging
        print(f"Bedrock JSON Parsing Error: {e}")
        return {
            "feedback": f"Error parsing JSON response: {e}",
            "score": 0,
            "next_question": "Sorry, an error occurred. Please try again."
        }