import asyncio
import sys
sys.path.append('backend')

from backend.chatbot.agent import ChatbotAgent
from backend.mavlink_parser.parser import MAVLinkParser

async def test_comprehensive_analysis():
    agent = ChatbotAgent()
    parser = MAVLinkParser()
    
    # Test with actual .bin file
    bin_file = '1980-01-08 09-44-08.bin'
    print(f'Testing with file: {bin_file}')
    
    try:
        # Parse flight data
        flight_data = await parser.parse_file(bin_file)
        print(f'Parsed flight data: {len(flight_data.get("message_counts", {}))} message types')
        print(f'Flight duration: {flight_data.get("flight_duration", 0):.1f} seconds')
        print(f'Max altitude: {flight_data.get("flight_stats", {}).get("max_altitude", 0):.1f}m')
        
        # Test various questions in English
        test_questions = [
            'What was the maximum altitude in this flight?',
            'Were there any GPS signal losses?',
            'What was the battery temperature?',
            'What errors occurred during flight?',
            'Were there any anomalies or unusual patterns?',
            'Please provide a comprehensive flight analysis',
            'How was the RC signal quality?',
            'What was the battery voltage range?',
            'How long was the total flight time?',
            'Were there any critical errors?',
            'Show me altitude timeline',
            'Analyze battery performance'
        ]
        
        print('\n=== Testing Comprehensive Flight Data Analysis ===')
        for i, question in enumerate(test_questions, 1):
            print(f'\n[{i}] Question: {question}')
            try:
                response = await agent.process_message(question, flight_data, 'test_session')
                content = response["content"]
                print(f'Answer: {content[:300]}...' if len(content) > 300 else f'Answer: {content}')
                print(f'Response type: {response.get("type", "unknown")}')
                print(f'Has flight data: {response.get("data", {}).get("has_flight_data", False)}')
            except Exception as e:
                print(f'Error processing question: {e}')
                import traceback
                traceback.print_exc()
        
        # Test context preparation
        print('\n=== Testing Context Preparation ===')
        try:
            detailed_context = await agent._prepare_comprehensive_flight_context(flight_data)
            print(f'Context length: {len(detailed_context)} characters')
            print(f'Context preview: {detailed_context[:500]}...')
        except Exception as e:
            print(f'Error preparing context: {e}')
        
    except FileNotFoundError:
        print('Sample file not found, testing without flight data')
        response = await agent.process_message('Tell me about drone data analysis', None, 'test_session')
        print(f'No data response: {response["content"][:200]}...')
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_comprehensive_analysis()) 