"""Returns & Refunds Assistant - Streamlit Chat UI.

Authenticates users via Cognito and connects to the deployed AgentCore Runtime agent.
The agent has access to DynamoDB (orders, customers, products), a Knowledge Base
(return policies), and persistent memory (customer preferences).
"""

import json
import uuid
import streamlit as st
import boto3

# --- Configuration ---
AWS_REGION = "us-west-2"
USER_POOL_ID = "us-west-2_4RJSTexeJ"
UI_CLIENT_ID = "2lbfq7b54vlkibr6ut9j4s3mf4"
AGENT_RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-west-2:115805780657:runtime/AgentCoreProject_CustomerAssistantAgent-SGvjcL9Z3r"

WELCOME_MESSAGE = (
    "Hello! I'm your Returns & Refunds Assistant. I can help you look up orders, "
    "check return eligibility, calculate refunds and answer policy questions. "
    "How can I help you today?"
)


# --- Cognito Authentication ---

def authenticate_user(username: str, password: str) -> dict:
    """Authenticate with Cognito using USER_PASSWORD_AUTH flow.

    Returns the auth result dict on success, or a challenge dict if
    NEW_PASSWORD_REQUIRED is triggered (first login).
    """
    client = boto3.client("cognito-idp", region_name=AWS_REGION)
    response = client.initiate_auth(
        ClientId=UI_CLIENT_ID,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": username,
            "PASSWORD": password,
        },
    )

    # Check for challenge (first-time password change)
    if response.get("ChallengeName") == "NEW_PASSWORD_REQUIRED":
        return {
            "challenge": "NEW_PASSWORD_REQUIRED",
            "session": response["Session"],
            "username": username,
        }

    # Successful auth
    return {
        "authenticated": True,
        "tokens": response["AuthenticationResult"],
    }


def respond_to_new_password_challenge(username: str, new_password: str, session: str) -> dict:
    """Complete the NEW_PASSWORD_REQUIRED challenge."""
    client = boto3.client("cognito-idp", region_name=AWS_REGION)
    response = client.respond_to_auth_challenge(
        ClientId=UI_CLIENT_ID,
        ChallengeName="NEW_PASSWORD_REQUIRED",
        Session=session,
        ChallengeResponses={
            "USERNAME": username,
            "NEW_PASSWORD": new_password,
        },
    )
    return {
        "authenticated": True,
        "tokens": response["AuthenticationResult"],
    }


# --- Agent Invocation ---

def invoke_agent(prompt: str, session_id: str, actor_id: str):
    """Invoke the deployed AgentCore Runtime agent and yield response chunks.

    Uses the bedrock-agentcore SDK to stream the response in real time.
    """
    client = boto3.client("bedrock-agentcore", region_name=AWS_REGION)

    payload = json.dumps({"prompt": prompt}).encode()

    response = client.invoke_agent_runtime(
        agentRuntimeArn=AGENT_RUNTIME_ARN,
        runtimeSessionId=session_id,
        runtimeUserId=actor_id,
        payload=payload,
    )

    # Process the streaming response
    content_type = response.get("contentType", "")

    if "text/event-stream" in content_type:
        for line in response["response"].iter_lines(chunk_size=10):
            if line:
                decoded = line.decode("utf-8")
                if decoded.startswith("data: "):
                    data = decoded[6:]
                    # Try to parse as JSON and extract text
                    try:
                        event = json.loads(data)
                        delta = event.get("event", {}).get("contentBlockDelta", {})
                        text = delta.get("delta", {}).get("text")
                        if text:
                            yield text
                    except (json.JSONDecodeError, KeyError):
                        yield data
    elif content_type == "application/json":
        chunks = []
        for chunk in response.get("response", []):
            chunks.append(chunk.decode("utf-8"))
        full_response = "".join(chunks)
        try:
            parsed = json.loads(full_response)
            yield str(parsed)
        except json.JSONDecodeError:
            yield full_response
    else:
        yield str(response)


# --- Streamlit UI ---

st.set_page_config(
    page_title="Returns & Refunds Assistant",
    page_icon="R",
    layout="centered",
)

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4()) + "-streamlit"
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "challenge" not in st.session_state:
    st.session_state.challenge = None


def show_login_page():
    """Render the login form."""
    st.title("Returns & Refunds Assistant")
    st.markdown("Sign in to access the assistant.")

    # Handle NEW_PASSWORD_REQUIRED challenge
    if st.session_state.challenge:
        st.warning("You must set a new password on first login.")
        with st.form("new_password_form"):
            new_password = st.text_input("New Password", type="password")
            submitted = st.form_submit_button("Set Password")
            if submitted and new_password:
                try:
                    result = respond_to_new_password_challenge(
                        st.session_state.challenge["username"],
                        new_password,
                        st.session_state.challenge["session"],
                    )
                    st.session_state.authenticated = True
                    st.session_state.user_email = st.session_state.challenge["username"]
                    st.session_state.challenge = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to set password: {e}")
        return

    # Normal login form
    with st.form("login_form"):
        email = st.text_input("Email", value="administrator@example.com")
        password = st.text_input("Password", type="password", value="Workshop2024!")
        submitted = st.form_submit_button("Sign In")

        if submitted:
            try:
                result = authenticate_user(email, password)
                if result.get("challenge") == "NEW_PASSWORD_REQUIRED":
                    st.session_state.challenge = result
                    st.rerun()
                elif result.get("authenticated"):
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.rerun()
            except Exception as e:
                st.error(f"Authentication failed: {e}")


def show_chat_page():
    """Render the chat interface."""
    # Sidebar with user info
    with st.sidebar:
        st.markdown(f"**User:** {st.session_state.user_email}")
        st.markdown(f"**Session:** `{st.session_state.session_id[:8]}...`")
        st.divider()
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.messages = []
            st.session_state.session_id = str(uuid.uuid4()) + "-streamlit"
            st.session_state.user_email = ""
            st.rerun()

    st.title("Returns & Refunds Assistant")

    # Show welcome message if no messages yet
    if not st.session_state.messages:
        st.session_state.messages.append({
            "role": "assistant",
            "content": WELCOME_MESSAGE,
        })

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask about orders, returns, or policies..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get agent response
        with st.chat_message("assistant"):
            # Derive actor_id from email (part before @)
            actor_id = st.session_state.user_email.split("@")[0]

            try:
                response_chunks = invoke_agent(
                    prompt=prompt,
                    session_id=st.session_state.session_id,
                    actor_id=actor_id,
                )
                # Stream the response
                full_response = st.write_stream(response_chunks)
            except Exception as e:
                full_response = f"Error communicating with the agent: {e}"
                st.error(full_response)

            # Save to history
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response,
            })


# --- Main ---
if st.session_state.authenticated:
    show_chat_page()
else:
    show_login_page()
