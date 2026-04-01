import os
import asyncio
import uuid
import json
import traceback
from onboarding_guide_agent import OnboardingGuideAgent

SESSION_STORE_FILE = os.path.join(os.path.dirname(__file__), 'session_store.json')

def load_session_store():
    if os.path.exists(SESSION_STORE_FILE):
        with open(SESSION_STORE_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_session_store(store):
    with open(SESSION_STORE_FILE, 'w') as f:
        json.dump(store, f, indent=4)

def get_or_create_user_session(session_store):
    if session_store:
        user_id, session_data = next(iter(session_store.items()))
        session_id = session_data.get('session_id')
        current_step = session_data.get('current_step', 1)
    else:
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        current_step = 1
        session_store[user_id] = {
            'session_id': session_id,
            'current_step': current_step
        }
        save_session_store(session_store)
    return user_id, session_id, current_step

def update_session_step(session_store, user_id, current_step):
    if user_id in session_store:
        session_store[user_id]['current_step'] = current_step
        save_session_store(session_store)

async def run_simulation():
    print("=== Ndara.ai Interactive LLM + RAG Onboarding Guide ===\n")
    print("This console strictly uses real conversational APIs, memory tracking, and RAG.")
    print("Note: Ensure you have an OPENAI_API_KEY in your .env file in the root AI-PROJECT folder.\n")
    
    faq_path = os.path.join(os.path.dirname(__file__), 'platform_onboarding_faq.json')
    try:
        from database import init_db
        await init_db()
        
        # IMPORTANT: Verify your environment variables and external service availability here
        # For example, check OPENAI_API_KEY, vector DB endpoint, credentials, etc.
        
        agent = OnboardingGuideAgent(faq_path=faq_path, llm_provider='openai')
    except ImportError as e:
        print(f"Error: Missing library {e}. Run: pip install -r requirements.txt")
        return
    except Exception as e:
        print("Failed to start Agent:")
        traceback.print_exc()
        return

    session_store = load_session_store()
    user_id, session_id, current_step = get_or_create_user_session(session_store)

    print(f"User ID: {user_id}")
    print(f"Session ID: {session_id}")
    print(f"Starting at Step: {current_step}")

    print("Thinking...")
    response, _ = await agent.process_message(user_id, current_step, "Hi Ndara.ai, I'm ready to onboard!", session_id)
    print(f"\n🤖 Agent [Step {current_step}]: {response}")

    while True:
        print(f"\n--- [Context: Step {current_step}] ---")
        user_input = input("You: ")
        
        if user_input.lower() in ['quit', 'exit']:
            print("Exiting simulation. Your progress has been saved.")
            break
            
        print("\nThinking...")
        response, metadata = await agent.process_message(user_id, current_step, user_input, session_id)
        
        print(f"\n🤖 Agent: {response}")
        print(f"📊 Debug Escalate Flag: {metadata.get('escalate_to')}")
        
        if metadata.get("escalate_to") == "live_agent_bridge":
            print("\n🚨 ESCALATION ACTIVE: This conversation has been bridged to the Admin Dashboard.")
            if metadata.get("locked"):
                print("Conversation is locked to a human agent.")
            break
            
        action = input("\n[Simulation] Type 'next' to pretend you completed the step in the UI, or just hit Enter to continue chatting: ").strip().lower()
        if action == 'next':
            current_step += 1
            update_session_step(session_store, user_id, current_step)
            if current_step > 7:
                print("\n🎉 Onboarding Complete!")
                break
            response, _ = await agent.process_message(user_id, current_step, f"SYSTEM NOTE: User just successfully completed step {current_step-1}. Welcome them to step {current_step}.", session_id)
            print(f"\n🤖 Agent [Step {current_step}]: {response}")

def main():
    asyncio.run(run_simulation())

if __name__ == "__main__":
    main()
