"""Conversational travel agent for context-aware query handling
Acts as intelligent layer between user inputs and MCP workflow.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

import google.generativeai as genai

from src.utils.logger import get_logger
from src.utils.config import Settings
from src.orchestrator.memory import MemoryManager, TripContext


@dataclass
class ConversationIntent:
    """Parsed user intent from conversational input"""
    intent_type: str  # 'plan', 'refine', 'explain', 'question', 'swap'
    query: str        # Cleaned query to pass to workflow
    context_needed: bool = True
    explanation_request: Optional[str] = None
    persona_response: Optional[str] = None


class ConversationalAgent:
    """Conversational travel buddy agent
    
    Handles context-aware refinements, explanations, and travel buddy persona.
    Parses user intent and crafts appropriate queries for the MCP workflow.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("conversational_agent")
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
    
    def parse_intent(
        self, 
        user_input: str, 
        memory_manager: MemoryManager, 
        session_id: str
    ) -> ConversationIntent:
        """Parse user intent and determine how to handle the query"""
        
        # Get current context
        trip_context = memory_manager.get_trip_context(session_id)
        history_summary = memory_manager.get_context_summary(session_id)
        
        # Build intent parsing prompt
        intent_prompt = self._build_intent_prompt(user_input, trip_context, history_summary)
        
        try:
            response = self.model.generate_content(intent_prompt)
            intent_text = response.text.strip()
            
            # Parse the structured response
            return self._parse_intent_response(intent_text, user_input)
            
        except Exception as e:
            self.logger.warning(f"Intent parsing failed: {e}, falling back to simple parsing")
            return self._fallback_intent_parsing(user_input, trip_context)
    
    def _build_intent_prompt(
        self, 
        user_input: str, 
        trip_context: Optional[TripContext], 
        history_summary: str
    ) -> str:
        """Build prompt for intent classification and query enhancement"""
        
        context_info = ""
        if trip_context:
            context_info = f"""
Current Trip Context:
- Original Query: {trip_context.query}
- Has Itinerary: {'Yes' if trip_context.current_itinerary else 'No'}
- Previous Refinements: {', '.join(trip_context.refinements[-3:]) if trip_context.refinements else 'None'}
"""
        
        return f"""You are a travel buddy AI helping users plan trips. Analyze the user's input and classify their intent.

{context_info}

Recent Conversation:
{history_summary}

User Input: "{user_input}"

Classify the intent and respond in this exact format:

INTENT: [plan|refine|explain|question|swap]
QUERY: [cleaned query to pass to travel planning system]
CONTEXT_NEEDED: [true|false]
EXPLANATION: [if user asks why/how, what they want explained]
PERSONA_RESPONSE: [friendly travel buddy response to show before results]

Guidelines:
- INTENT 'plan': New trip planning or major changes
- INTENT 'refine': Adjustments to existing plan (budget, duration, add/remove items)
- INTENT 'explain': User asks "why" something was recommended
- INTENT 'question': Simple questions about destinations/travel
- INTENT 'swap': User wants alternatives to current recommendations

- QUERY: Convert user input into clear travel planning query
- CONTEXT_NEEDED: false only for simple questions that don't need current itinerary
- EXPLANATION: Only if user explicitly asks "why" or "how"
- PERSONA_RESPONSE: Friendly 1-2 sentence response as a travel buddy

Examples:
User: "reduce budget to ₹8000"
INTENT: refine
QUERY: Adjust the current itinerary to fit within ₹8000 total budget
CONTEXT_NEEDED: true
EXPLANATION: 
PERSONA_RESPONSE: Let me help you cut costs while keeping the trip fun! 💰

User: "why did you choose this hotel?"
INTENT: explain
QUERY: Explain the reasoning behind hotel recommendation in current itinerary
CONTEXT_NEEDED: true
EXPLANATION: hotel choice reasoning
PERSONA_RESPONSE: Great question! Let me break down why I picked that hotel for you 🏨
"""
    
    def _parse_intent_response(self, response: str, original_input: str) -> ConversationIntent:
        """Parse structured response from intent classification"""
        
        lines = response.split('\n')
        intent_data = {}
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                intent_data[key.strip().upper()] = value.strip()
        
        return ConversationIntent(
            intent_type=intent_data.get('INTENT', 'plan').lower(),
            query=intent_data.get('QUERY', original_input),
            context_needed=intent_data.get('CONTEXT_NEEDED', 'true').lower() == 'true',
            explanation_request=intent_data.get('EXPLANATION') if intent_data.get('EXPLANATION') else None,
            persona_response=intent_data.get('PERSONA_RESPONSE') if intent_data.get('PERSONA_RESPONSE') else None
        )
    
    def _fallback_intent_parsing(
        self, 
        user_input: str, 
        trip_context: Optional[TripContext]
    ) -> ConversationIntent:
        """Simple rule-based fallback for intent parsing"""
        
        input_lower = user_input.lower()
        
        # Question patterns
        if any(word in input_lower for word in ['why', 'how', 'what', 'where', 'when']):
            if 'why' in input_lower:
                return ConversationIntent(
                    intent_type='explain',
                    query=f"Explain: {user_input}",
                    explanation_request=user_input,
                    persona_response="Let me explain that for you! 🤔"
                )
            else:
                return ConversationIntent(
                    intent_type='question',
                    query=user_input,
                    context_needed=False,
                    persona_response="Let me find that info for you! ✈️"
                )
        
        # Refinement patterns
        refinement_keywords = ['budget', 'reduce', 'increase', 'add', 'remove', 'change', 'adjust', 'extend', 'shorten']
        if any(keyword in input_lower for keyword in refinement_keywords):
            return ConversationIntent(
                intent_type='refine',
                query=f"Refine current itinerary: {user_input}",
                persona_response="I'll adjust your plan! 🔧"
            )
        
        # Alternative/swap patterns
        if any(word in input_lower for word in ['alternative', 'instead', 'different', 'other', 'swap']):
            return ConversationIntent(
                intent_type='swap',
                query=f"Find alternatives: {user_input}",
                persona_response="Let me find some other great options! 🔄"
            )
        
        # Default to plan
        return ConversationIntent(
            intent_type='plan',
            query=user_input,
            persona_response="Let me create an awesome itinerary for you! 🗺️"
        )
    
    def enhance_query_with_context(
        self, 
        intent: ConversationIntent, 
        memory_manager: MemoryManager, 
        session_id: str
    ) -> str:
        """Enhance query with conversation context for better results"""
        
        if not intent.context_needed:
            return intent.query
        
        # Get conversation context
        trip_context = memory_manager.get_trip_context(session_id)
        recent_messages = memory_manager.get_conversation_history(session_id, limit=5)
        
        # Build enhanced query
        enhanced_parts = [intent.query]
        
        if trip_context:
            if intent.intent_type == 'refine' and trip_context.current_itinerary:
                enhanced_parts.append("\n[Context: Current itinerary exists, user wants to modify it]")
            
            if trip_context.refinements:
                enhanced_parts.append(f"\n[Previous refinements: {', '.join(trip_context.refinements[-3:])}]")
        
        if recent_messages:
            conversation_context = []
            for msg in recent_messages[-3:]:
                role_prefix = "User" if msg.role == "user" else "Assistant"
                conversation_context.append(f"{role_prefix}: {msg.content[:100]}")
            
            enhanced_parts.append(f"\n[Recent conversation context: {' | '.join(conversation_context)}]")
        
        # Add travel buddy persona instructions
        buddy_instructions = self._get_buddy_persona_instructions(intent.intent_type)
        enhanced_parts.append(f"\n[Response style: {buddy_instructions}]")
        
        return "\n".join(enhanced_parts)
    
    def _get_buddy_persona_instructions(self, intent_type: str) -> str:
        """Get persona instructions based on intent type"""
        
        persona_map = {
            'plan': "Act as an experienced travel buddy. Include practical warnings about scams, budget hacks, and insider tips. Be enthusiastic but realistic about costs and logistics.",
            'refine': "Help adjust the plan while explaining trade-offs. Show what changes when budget/duration changes. Be supportive and solution-oriented.",
            'explain': "Provide clear reasoning behind recommendations. Explain why certain choices were made considering budget, safety, convenience, and experience quality.",
            'question': "Answer as a knowledgeable local friend. Provide practical, current information with helpful context.",
            'swap': "Suggest creative alternatives while explaining pros/cons of each option. Help user understand different choices available."
        }
        
        return persona_map.get(intent_type, persona_map['plan'])
    
    def format_response_with_persona(
        self, 
        intent: ConversationIntent, 
        workflow_result: str,
        memory_manager: MemoryManager,
        session_id: str
    ) -> str:
        """Add travel buddy persona and context to workflow results"""
        
        # Add persona greeting if provided
        response_parts = []
        
        if intent.persona_response:
            response_parts.append(f"🧳 **{intent.persona_response}**\n")
        
        # For explanations, add specific reasoning
        if intent.intent_type == 'explain' and intent.explanation_request:
            explanation = self._generate_explanation(
                intent.explanation_request, 
                workflow_result, 
                memory_manager, 
                session_id
            )
            if explanation:
                response_parts.append(f"💡 **Explanation:** {explanation}\n")
        
        # Add the main workflow result
        response_parts.append(workflow_result)
        
        # Add contextual follow-up suggestions
        follow_ups = self._generate_follow_up_suggestions(intent, memory_manager, session_id)
        if follow_ups:
            response_parts.append(f"\n🎯 **What's next?** {follow_ups}")
        
        return "\n".join(response_parts)
    
    def _generate_explanation(
        self, 
        explanation_request: str, 
        itinerary: str, 
        memory_manager: MemoryManager, 
        session_id: str
    ) -> Optional[str]:
        """Generate specific explanation for user's why/how question"""
        
        try:
            explanation_prompt = f"""
Based on this travel itinerary, answer the user's specific question as a knowledgeable travel buddy.

Itinerary:
{itinerary[:1000]}...

User's Question: "{explanation_request}"

Provide a clear, practical explanation in 2-3 sentences. Focus on:
- Safety considerations
- Budget efficiency  
- Convenience factors
- Local insights
- Experience quality

Keep it friendly and informative.
"""
            
            response = self.model.generate_content(explanation_prompt)
            return response.text.strip()
            
        except Exception as e:
            self.logger.warning(f"Explanation generation failed: {e}")
            return None
    
    def _generate_follow_up_suggestions(
        self, 
        intent: ConversationIntent, 
        memory_manager: MemoryManager, 
        session_id: str
    ) -> Optional[str]:
        """Generate contextual follow-up suggestions"""
        
        suggestions_map = {
            'plan': "Try: `refine 'reduce budget'` or `add 'include food tour'` or `why 'hotel choice'`",
            'refine': "Try: `show` to see updated plan or `add` more preferences",
            'explain': "Try: `refine` to adjust based on this info or ask about other choices",
            'question': "Try: `plan` to start your itinerary or ask more specific questions",
            'swap': "Try: `refine` to pick an alternative or `show` current plan"
        }
        
        return suggestions_map.get(intent.intent_type)