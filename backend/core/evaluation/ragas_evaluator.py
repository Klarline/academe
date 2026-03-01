"""
RAGAS Evaluation Framework for Academe

Evaluates system quality using RAGAS metrics:
- Faithfulness: How grounded are the answers in the context
- Answer Relevancy: How relevant is the answer to the question
- Context Recall: How much relevant info is retrieved
- Context Precision: How precise is the retrieved context

Uses OpenAI as the judge LLM for RAGAS (best supported and most reliable).
Falls back to simple evaluation if RAGAS or OpenAI is unavailable.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

# Handle optional RAGAS import
try:
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_recall,
        context_precision
    )
    from datasets import Dataset
    import pandas as pd
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False
    Dataset = None
    pd = None

from core.graph.workflow import process_with_langgraph
from core.models import UserProfile

logger = logging.getLogger(__name__)


def _get_ragas_llm():
    """Get OpenAI LLM configured for RAGAS evaluation."""
    try:
        from core.config import get_openai_llm
        return get_openai_llm(model="gpt-4o", temperature=0.0)
    except Exception:
        return None


class RAGASEvaluator:
    """
    Evaluate system quality using RAGAS framework.

    This evaluator measures:
    1. Answer quality (relevancy, faithfulness)
    2. Retrieval quality (recall, precision)
    3. Overall system performance
    """

    def __init__(self, use_ragas: bool = None):
        """
        Initialize the evaluator.

        Args:
            use_ragas: Whether to use RAGAS (None = auto-detect)
        """
        if use_ragas is None:
            self.use_ragas = RAGAS_AVAILABLE
        else:
            self.use_ragas = use_ragas and RAGAS_AVAILABLE

        if self.use_ragas:
            self.metrics = [
                faithfulness,
                answer_relevancy,
                context_recall,
                context_precision
            ]
            logger.info("RAGAS metrics initialized")
        else:
            self.metrics = []
            logger.info("RAGAS not available, using simplified evaluation")

        self.evaluation_results = []

    def create_test_dataset(
        self,
        test_questions: List[Dict[str, Any]]
    ) -> Optional[Dataset]:
        """
        Create a RAGAS-compatible dataset from test questions.

        Args:
            test_questions: List of test question dictionaries

        Returns:
            Dataset object or None if RAGAS not available
        """
        if not self.use_ragas or not pd:
            return None

        # Format for RAGAS
        formatted_data = []
        for q in test_questions:
            formatted_data.append({
                "question": q["question"],
                "ground_truth": q.get("ground_truth", ""),
                "contexts": q.get("contexts", []),
                "topic": q.get("topic", "general"),
                "difficulty": q.get("difficulty", "intermediate")
            })

        df = pd.DataFrame(formatted_data)
        return Dataset.from_pandas(df)

    def evaluate_system(
        self,
        test_queries: List[Dict[str, Any]],
        user: Optional[UserProfile] = None
    ) -> Dict[str, Any]:
        """
        Run evaluation on test queries.

        Args:
            test_queries: List of test query dictionaries
            user: User profile for personalized evaluation

        Returns:
            Evaluation results dictionary
        """
        if not user:
            # Create default test user
            user = UserProfile(
                id="test_evaluator",
                username="evaluator",
                email="test@example.com",
                learning_level="intermediate",
                learning_goal="understand_deeply",
                explanation_style="balanced"
            )

        results = []
        conversation_id = f"eval_{datetime.now().timestamp()}"

        for i, query in enumerate(test_queries):
            logger.info(f"Evaluating query {i+1}/{len(test_queries)}: {query['question'][:50]}...")

            try:
                # Get system response
                response_data = self.get_system_response(
                    question=query['question'],
                    user=user,
                    conversation_id=conversation_id
                )

                # Prepare evaluation data
                eval_data = {
                    'question': query['question'],
                    'answer': response_data['answer'],
                    'contexts': response_data.get('contexts', []),
                    'ground_truth': query.get('ground_truth', ''),
                    'topic': query.get('topic', 'unknown'),
                    'difficulty': query.get('difficulty', 'unknown'),
                    'agent_used': response_data.get('agent_used', 'unknown'),
                    'response_time': response_data.get('response_time', 0)
                }

                # Simple evaluation if RAGAS not available
                if not self.use_ragas:
                    eval_data['simple_score'] = self._simple_evaluate(
                        query['question'],
                        response_data['answer'],
                        query.get('ground_truth', '')
                    )

                results.append(eval_data)

            except Exception as e:
                logger.error(f"Error evaluating query: {e}")
                results.append({
                    'question': query['question'],
                    'error': str(e)
                })

        # Run RAGAS evaluation if available
        if self.use_ragas and pd and len(results) > 0:
            try:
                # Create dataset
                df = pd.DataFrame(results)
                dataset = Dataset.from_pandas(df)

                # Run RAGAS metrics (use OpenAI as judge when available)
                ragas_llm = _get_ragas_llm()
                eval_kwargs = {"dataset": dataset, "metrics": self.metrics}
                if ragas_llm:
                    eval_kwargs["llm"] = ragas_llm
                scores = evaluate(**eval_kwargs)

                # Add RAGAS scores to results
                evaluation_summary = {
                    'ragas_scores': scores,
                    'num_queries': len(test_queries),
                    'timestamp': datetime.now().isoformat()
                }

            except Exception as e:
                logger.error(f"RAGAS evaluation failed: {e}")
                evaluation_summary = self._create_simple_summary(results)
        else:
            evaluation_summary = self._create_simple_summary(results)

        # Store results
        self.evaluation_results.append({
            'summary': evaluation_summary,
            'detailed_results': results
        })

        return evaluation_summary

    def get_system_response(
        self,
        question: str,
        user: UserProfile,
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        Get response from the system for evaluation.

        Args:
            question: Test question
            user: User profile
            conversation_id: Conversation ID

        Returns:
            Response data including answer and metadata
        """
        import time
        start_time = time.time()

        try:
            # Use the workflow
            state = process_with_langgraph(
                question=question,
                user_id=user.id,
                conversation_id=conversation_id,
                user_profile=user.model_dump() if hasattr(user, 'model_dump') else {}
            )

            response_time = time.time() - start_time

            return {
                'answer': state.get('response', ''),
                'contexts': [s.get('content', '') for s in state.get('sources', [])],
                'agent_used': state.get('agent_used', 'unknown'),
                'route': state.get('route', 'unknown'),
                'response_time': response_time,
                'metadata': state
            }

        except Exception as e:
            logger.error(f"Error getting system response: {e}")
            return {
                'answer': f"Error: {str(e)}",
                'contexts': [],
                'agent_used': 'error',
                'response_time': time.time() - start_time,
                'error': str(e)
            }

    def _simple_evaluate(
        self,
        question: str,
        answer: str,
        ground_truth: str
    ) -> float:
        """
        Simple evaluation when RAGAS is not available.

        Returns a basic score based on:
        - Answer length
        - Keyword overlap
        - Basic quality checks
        """
        if not answer or answer.startswith("Error:"):
            return 0.0

        score = 0.0

        # Check answer length (not too short, not too long)
        if 50 < len(answer) < 2000:
            score += 0.3
        elif len(answer) > 0:
            score += 0.1

        # Check if answer addresses the question (simple keyword check)
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        overlap = len(question_words & answer_words) / max(len(question_words), 1)
        score += min(0.3, overlap)

        # Check for ground truth overlap if available
        if ground_truth:
            truth_words = set(ground_truth.lower().split())
            truth_overlap = len(answer_words & truth_words) / max(len(truth_words), 1)
            score += min(0.4, truth_overlap)
        else:
            # Give benefit of doubt if no ground truth
            score += 0.2

        return min(1.0, score)

    def _create_simple_summary(
        self,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create summary without RAGAS metrics."""
        valid_results = [r for r in results if 'error' not in r]
        error_results = [r for r in results if 'error' in r]

        if valid_results and 'simple_score' in valid_results[0]:
            avg_score = sum(r['simple_score'] for r in valid_results) / len(valid_results)
        else:
            avg_score = 0.0

        # Calculate average response time
        response_times = [r.get('response_time', 0) for r in valid_results]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        # Count by topic
        topics = {}
        for r in valid_results:
            topic = r.get('topic', 'unknown')
            topics[topic] = topics.get(topic, 0) + 1

        # Count by agent
        agents = {}
        for r in valid_results:
            agent = r.get('agent_used', 'unknown')
            agents[agent] = agents.get(agent, 0) + 1

        return {
            'evaluation_type': 'simple',
            'num_queries': len(results),
            'num_successful': len(valid_results),
            'num_errors': len(error_results),
            'average_score': avg_score,
            'average_response_time': avg_response_time,
            'topics_evaluated': topics,
            'agents_used': agents,
            'timestamp': datetime.now().isoformat()
        }

    def generate_report(
        self,
        output_file: Optional[str] = None
    ) -> str:
        """
        Generate a detailed evaluation report.

        Args:
            output_file: Optional file path to save report

        Returns:
            Report as string
        """
        if not self.evaluation_results:
            return "No evaluation results available. Run evaluate_system() first."

        report_lines = [
            "=" * 60,
            "ACADEME EVALUATION REPORT",
            "=" * 60,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]

        for i, result in enumerate(self.evaluation_results):
            summary = result['summary']
            report_lines.append(f"\nEvaluation Run #{i+1}")
            report_lines.append("-" * 40)

            if 'ragas_scores' in summary:
                report_lines.append("\nRAGAS Metrics:")
                scores = summary['ragas_scores']
                for metric, value in scores.items():
                    report_lines.append(f"  {metric}: {value:.3f}")
            else:
                report_lines.append("\nSimple Evaluation:")
                report_lines.append(f"  Average Score: {summary.get('average_score', 0):.3f}")

            report_lines.append(f"\nQueries Evaluated: {summary['num_queries']}")

            if 'num_successful' in summary:
                report_lines.append(f"Successful: {summary['num_successful']}")
                report_lines.append(f"Errors: {summary['num_errors']}")

            if 'average_response_time' in summary:
                report_lines.append(f"\nAverage Response Time: {summary['average_response_time']:.2f}s")

            if 'topics_evaluated' in summary:
                report_lines.append("\nTopics Evaluated:")
                for topic, count in summary['topics_evaluated'].items():
                    report_lines.append(f"  {topic}: {count}")

            if 'agents_used' in summary:
                report_lines.append("\nAgents Used:")
                for agent, count in summary['agents_used'].items():
                    report_lines.append(f"  {agent}: {count}")

        # Add recommendations
        report_lines.extend([
            "",
            "=" * 60,
            "RECOMMENDATIONS",
            "=" * 60
        ])

        recommendations = self._generate_recommendations()
        report_lines.extend(recommendations)

        report = "\n".join(report_lines)

        # Save to file if specified
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(report)
                logger.info(f"Report saved to {output_file}")
            except Exception as e:
                logger.error(f"Failed to save report: {e}")

        return report

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on evaluation results."""
        recommendations = []

        if not self.evaluation_results:
            return ["Run evaluation first to generate recommendations."]

        latest_result = self.evaluation_results[-1]
        summary = latest_result['summary']

        # Check if using RAGAS
        if 'ragas_scores' not in summary:
            recommendations.append("• Install RAGAS for more detailed evaluation metrics")

        # Check response time
        avg_time = summary.get('average_response_time', 0)
        if avg_time > 5:
            recommendations.append(f"• Response time is high ({avg_time:.1f}s). Consider optimization.")
        elif avg_time < 2:
            recommendations.append(f"• Excellent response time ({avg_time:.1f}s)")

        # Check error rate
        if 'num_errors' in summary:
            error_rate = summary['num_errors'] / summary['num_queries']
            if error_rate > 0.1:
                recommendations.append(f"• High error rate ({error_rate:.1%}). Review error handling.")

        # Check score if available
        if 'average_score' in summary:
            score = summary['average_score']
            if score < 0.5:
                recommendations.append("• Low evaluation score. Review answer quality.")
            elif score > 0.8:
                recommendations.append("• Good evaluation score!")

        return recommendations if recommendations else ["• System performing within normal parameters."]


# Export evaluator
__all__ = ["RAGASEvaluator"]