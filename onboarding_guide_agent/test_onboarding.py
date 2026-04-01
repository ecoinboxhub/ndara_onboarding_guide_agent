import os
import asyncio
from onboarding_guide_agent import OnboardingGuideAgent

async def run_simulation():
    print("=== Ndara.ai Interactive LLM + RAG Onboarding Guide ===\n")
    print("This console strictly uses real conversational APIs, memory tracking, and RAG.")
    print("Note: Ensure you have an OPENAI_API_KEY in your .env file in the root AI-PROJECT folder.\n")
    
    faq_path = os.path.join(os.path.dirname(__file__), 'platform_onboarding_faq.json')
    try:
        from database import init_db
        await init_db()
        agent = OnboardingGuideAgent(faq_path=faq_path, llm_provider='openai')
    except ImportError as e:
        print(f"Error: Missing library {e}. Run: pip install -r requirements.txt")
        return
    except Exception as e:
        print(f"Failed to start Agent: {e}")
        return
        
    user_id = "test_user_001"
    current_step = 1
    session_id = "test_session_1"
    
    print("Thinking...")
    response, _ = await agent.process_message(user_id, current_step, "Hi Ndara.ai, I'm ready to onboard!", session_id)
    print(f"\n🤖 Agent [Step {current_step}]: {response}")

    while True:
        print(f"\n--- [Context: Step {current_step}] ---")
        user_input = input("You: ")
        
        if user_input.lower() in ['quit', 'exit']:
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
            if current_step > 7:
                print("\n🎉 Onboarding Complete!")
                break
            response, _ = await agent.process_message(user_id, current_step, f"SYSTEM NOTE: User just successfully completed step {current_step-1}. Welcome them to step {current_step}.", session_id)
            print(f"\n🤖 Agent [Step {current_step}]: {response}")

def main():
    asyncio.run(run_simulation())

if __name__ == "__main__":
    main()
