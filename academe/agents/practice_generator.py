"""
Practice Generator Agent - Creates practice problems from documents.

This agent generates practice questions, exercises, and assessments
based on the user's uploaded documents and learning preferences.
"""

import random
from typing import List, Dict, Optional, Any
from academe.config import get_llm
from academe.models import UserProfile, LearningLevel
from academe.models.agent_responses import PracticeSetResponse, PracticeQuestion
from academe.rag import RAGPipeline
from academe.documents import DocumentManager


class PracticeGenerator:
    """Agent that generates practice problems from documents."""

    def __init__(
        self,
        rag_pipeline: Optional[RAGPipeline] = None,
        document_manager: Optional[DocumentManager] = None
    ):
        """
        Initialize practice generator.

        Args:
            rag_pipeline: RAG pipeline for content retrieval
            document_manager: Document manager
        """
        self.rag_pipeline = rag_pipeline or RAGPipeline()
        self.document_manager = document_manager or DocumentManager()

    def generate_practice_set(
        self,
        topic: str,
        user: UserProfile,
        num_questions: int = 5,
        question_types: Optional[List[str]] = None,
        memory_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a set of practice questions on a topic.

        Args:
            topic: Topic for practice
            user: User profile
            num_questions: Number of questions to generate
            question_types: Types of questions (mcq, short, code, explain)
            memory_context: Memory context for adaptive question generation (v0.4)

        Returns:
            Dictionary with questions and answers
        """
        # Default question types if not specified
        if not question_types:
            question_types = ["mcq", "short", "explain"]

        # Get relevant content from documents
        content, sources = self.rag_pipeline.query_with_context(
            query=f"Key concepts, formulas, and examples about {topic}",
            user=user,
            top_k=5
        )

        if not content:
            return {
                "error": "No content found for this topic in your documents.",
                "questions": []
            }

        # Generate questions based on user level AND memory
        questions = self._generate_questions(
            topic=topic,
            content=content,
            user=user,
            num_questions=num_questions,
            question_types=question_types,
            memory_context=memory_context
        )

        # Add source information
        source_docs = list(set(
            s.document.title or s.document.original_filename
            for s in sources
        ))

        return {
            "topic": topic,
            "difficulty": user.learning_level.value,
            "questions": questions,
            "sources": source_docs,
            "total_questions": len(questions)
        }

    def generate_quiz(
        self,
        document_id: str,
        user: UserProfile,
        quiz_length: int = 10
    ) -> Dict[str, Any]:
        """
        Generate a quiz from a specific document.

        Args:
            document_id: Document to create quiz from
            user: User profile
            quiz_length: Number of questions

        Returns:
            Quiz with questions and answers
        """
        # Get document
        document = self.document_manager.doc_repo.get_document(document_id)
        if not document or document.user_id != user.id:
            return {"error": "Document not found"}

        # Get chunks from document
        chunks = self.document_manager.get_document_chunks(document_id, user.id)
        if not chunks:
            return {"error": "No content in document"}

        # Sample diverse chunks
        sample_size = min(10, len(chunks))
        sampled_chunks = random.sample(chunks, sample_size)

        # Build content for quiz generation
        content = "\n\n".join([chunk.content for chunk in sampled_chunks])

        # Generate quiz questions
        questions = self._generate_quiz_questions(
            document_title=document.title or document.original_filename,
            content=content,
            user=user,
            num_questions=quiz_length
        )

        return {
            "document": document.title or document.original_filename,
            "quiz_type": "comprehensive",
            "questions": questions,
            "total_questions": len(questions),
            "difficulty": user.learning_level.value
        }

    def generate_flashcards(
        self,
        topic: str,
        user: UserProfile,
        num_cards: int = 10
    ) -> List[Dict[str, str]]:
        """
        Generate flashcards for memorization.

        Args:
            topic: Topic for flashcards
            user: User profile
            num_cards: Number of flashcards

        Returns:
            List of flashcards with front and back
        """
        # Get key concepts and definitions
        content, _ = self.rag_pipeline.query_with_context(
            query=f"Key terms, concepts, formulas, and definitions about {topic}",
            user=user,
            top_k=5
        )

        if not content:
            return []

        # Generate flashcards
        flashcards = self._generate_flashcards(
            topic=topic,
            content=content,
            user=user,
            num_cards=num_cards
        )

        return flashcards

    def generate_code_exercise(
        self,
        concept: str,
        user: UserProfile,
        include_solution: bool = True
    ) -> Dict[str, str]:
        """
        Generate a coding exercise.

        Args:
            concept: Programming concept
            user: User profile
            include_solution: Whether to include solution

        Returns:
            Exercise with optional solution
        """
        # Get code examples from documents
        content, _ = self.rag_pipeline.query_with_context(
            query=f"Code examples and implementations of {concept}",
            user=user,
            top_k=3
        )

        # Generate exercise
        exercise = self._generate_code_exercise(
            concept=concept,
            content=content,
            user=user,
            include_solution=include_solution
        )

        return exercise

    def _generate_questions(
        self,
        topic: str,
        content: str,
        user: UserProfile,
        num_questions: int,
        question_types: List[str],
        memory_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate practice questions using structured output with memory awareness."""

        # Adjust prompt based on user level
        level_instructions = {
            LearningLevel.BEGINNER: "Create simple, foundational questions focusing on basic understanding",
            LearningLevel.INTERMEDIATE: "Create moderate difficulty questions that test application of concepts",
            LearningLevel.ADVANCED: "Create challenging questions that require deep understanding and analysis"
        }

        # Map question types for clarity
        type_descriptions = {
            "mcq": "Multiple choice with 4 options",
            "short": "Short answer questions",
            "code": "Coding problems",
            "explain": "Explanation questions"
        }
        
        types_str = ", ".join([f"{t} ({type_descriptions.get(t, t)})" for t in question_types])
        
        # Build memory context string
        memory_instructions = ""
        if memory_context:
            memory_parts = []
            
            # Focus on weak areas
            if memory_context.get("weak_areas"):
                memory_parts.append(f"FOCUS AREAS (user struggling): {', '.join(memory_context['weak_areas'])}")
                memory_parts.append("- Generate more questions on these weak areas")
                memory_parts.append("- Keep questions simpler for struggling topics")
            
            # Avoid topics they've mastered
            if memory_context.get("learning_progress", {}).get("recent_concepts"):
                strong_concepts = [
                    c["concept"] for c in memory_context["learning_progress"]["recent_concepts"]
                    if c.get("mastery") in ["proficient", "expert"]
                ]
                if strong_concepts:
                    memory_parts.append(f"MASTERED (avoid unless relevant): {', '.join(strong_concepts)}")
            
            if memory_parts:
                memory_instructions = "\n\nMEMORY-BASED ADAPTATION:\n" + "\n".join(memory_parts)

        prompt = f"""Generate EXACTLY {num_questions} practice questions about {topic}.

Content to base questions on:
{content[:1500]}

Requirements:
- User Level: {user.learning_level.value}
- {level_instructions.get(user.learning_level, level_instructions[LearningLevel.INTERMEDIATE])}
- Question Types: {types_str}
- Generate EXACTLY {num_questions} questions, no more, no less
{memory_instructions}

For MCQ questions:
- Provide exactly 4 answer options
- Make one option clearly correct
- Make other options plausible but incorrect

For all questions:
- Provide clear, unambiguous question text
- Include correct answer
- Provide brief explanation

Focus on practical understanding and real-world application."""

        try:
            llm = get_llm(temperature=0.7)
            
            # Use structured output with Pydantic
            structured_llm = llm.with_structured_output(PracticeSetResponse)
            
            response = structured_llm.invoke(prompt)
            
            # Convert Pydantic models to dicts for compatibility
            questions = []
            for q in response.questions:
                q_dict = {
                    "question": q.question_text,
                    "type": q.question_type,
                    "answer": q.correct_answer,
                    "explanation": q.explanation
                }
                
                # Add options for MCQ
                if q.question_type == "mcq" and q.options:
                    q_dict["options"] = q.options
                
                questions.append(q_dict)
            
            return questions

        except Exception as e:
            print(f"Error generating structured questions: {e}")
            print("Falling back to simple text parsing...")
            
            # Fallback to simple generation without structured output
            try:
                llm = get_llm(temperature=0.7)
                response = llm.invoke(prompt)
                
                # Parse response into structured questions
                questions = self._parse_questions_fallback(
                    response.content if hasattr(response, 'content') else str(response),
                    num_questions
                )
                
                return questions
                
            except Exception as e2:
                return [{
                    "type": "error",
                    "question": f"Failed to generate questions: {str(e2)}",
                    "answer": "",
                    "explanation": ""
                }]

    def _generate_quiz_questions(
        self,
        document_title: str,
        content: str,
        user: UserProfile,
        num_questions: int
    ) -> List[Dict[str, Any]]:
        """Generate quiz questions from document."""

        prompt = f"""Create a {num_questions}-question quiz from this document: {document_title}

Content:
{content[:2000]}

Create a mix of:
- Multiple choice questions (4 options each)
- True/False questions
- Short answer questions

Difficulty: {user.learning_level.value}

For each question provide the correct answer and a brief explanation."""

        try:
            llm = get_llm(temperature=0.7)
            response = llm.invoke(prompt)

            questions = self._parse_questions(
                response.content if hasattr(response, 'content') else str(response)
            )

            return questions

        except Exception as e:
            return []

    def _generate_flashcards(
        self,
        topic: str,
        content: str,
        user: UserProfile,
        num_cards: int
    ) -> List[Dict[str, str]]:
        """Generate flashcards."""

        prompt = f"""Create {num_cards} flashcards about {topic} from this content:

{content[:1500]}

User Level: {user.learning_level.value}

For each flashcard:
- Front: A term, concept, or question
- Back: Definition, answer, or explanation

Make them suitable for memorization and quick review."""

        try:
            llm = get_llm(temperature=0.6)
            response = llm.invoke(prompt)

            # Parse into flashcards
            flashcards = self._parse_flashcards(
                response.content if hasattr(response, 'content') else str(response)
            )

            return flashcards

        except Exception as e:
            return []

    def _generate_code_exercise(
        self,
        concept: str,
        content: str,
        user: UserProfile,
        include_solution: bool
    ) -> Dict[str, str]:
        """Generate coding exercise."""

        level_map = {
            LearningLevel.BEGINNER: "simple, with clear requirements",
            LearningLevel.INTERMEDIATE: "moderate, requiring some problem-solving",
            LearningLevel.ADVANCED: "challenging, requiring optimization or advanced techniques"
        }

        prompt = f"""Create a coding exercise about {concept}.

Reference content:
{content[:1000] if content else "General knowledge about " + concept}

Difficulty: {level_map.get(user.learning_level, level_map[LearningLevel.INTERMEDIATE])}

Provide:
1. Problem description
2. Input/output examples
3. Constraints
{f"4. Solution code with explanation" if include_solution else ""}"""

        try:
            llm = get_llm(temperature=0.7)
            response = llm.invoke(prompt)

            exercise_text = response.content if hasattr(response, 'content') else str(response)

            # Structure the exercise
            exercise = {
                "concept": concept,
                "difficulty": user.learning_level.value,
                "problem": exercise_text
            }

            return exercise

        except Exception as e:
            return {
                "concept": concept,
                "problem": f"Failed to generate exercise: {str(e)}"
            }

    def _parse_questions_fallback(self, text: str, num_questions: int) -> List[Dict[str, Any]]:
        """Parse generated text into structured questions (fallback method)."""
        questions = []

        # Simple parsing - in production, use more sophisticated parsing
        lines = text.split('\n')
        current_question = {}

        for line in lines:
            line = line.strip()
            if not line:
                if current_question:
                    questions.append(current_question)
                    current_question = {}
            elif line.startswith('Question') or line.startswith('Q:') or line.startswith('1.') or line.startswith('2.'):
                if current_question:
                    questions.append(current_question)
                current_question = {"question": line, "type": "short"}
            elif line.startswith('Answer') or line.startswith('A:'):
                if current_question:
                    current_question["answer"] = line
            elif line.startswith('Explanation'):
                if current_question:
                    current_question["explanation"] = line

        if current_question:
            questions.append(current_question)

        # Ensure all questions have required fields
        for q in questions:
            if "answer" not in q:
                q["answer"] = "Answer not provided"
            if "explanation" not in q:
                q["explanation"] = ""
            if "type" not in q:
                q["type"] = "short"
        
        # Limit to requested number
        return questions[:num_questions]

    def _parse_flashcards(self, text: str) -> List[Dict[str, str]]:
        """Parse generated text into flashcards."""
        flashcards = []

        lines = text.split('\n')
        current_card = {}

        for line in lines:
            line = line.strip()
            if line.startswith('Front:') or line.startswith('Q:'):
                if current_card:
                    flashcards.append(current_card)
                current_card = {"front": line.replace('Front:', '').replace('Q:', '').strip()}
            elif line.startswith('Back:') or line.startswith('A:'):
                if current_card:
                    current_card["back"] = line.replace('Back:', '').replace('A:', '').strip()

        if current_card and "front" in current_card and "back" in current_card:
            flashcards.append(current_card)

        return flashcards


# Export main components
__all__ = ["PracticeGenerator"]