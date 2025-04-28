import os
from dotenv import load_dotenv
import google.generativeai as genai
import io
import re
import json
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from .data_models import QuestionEvaluation, GeminiEvaluationResponse

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def build_prompt(criteria_list, questions_dict) -> str:
    """
    Builds a structured prompt for the Gemini model to evaluate student responses.

    Args:
        criteria_list: List of RubricCriteria objects containing evaluation criteria.
        questions_dict: Dictionary of question IDs to QuestionRubric objects.

    Returns:
        str: A formatted prompt string with instructions, rubric criteria, and questions.
    """
    # Build a prompt that instructs the model about the expected output format
    prompt = "You are an AI evaluator. Use the following rubric criteria and questions to evaluate the student's PDF response.\n\n"

    # Add rubric criteria
    prompt += "RUBRIC CRITERIA:\n"
    for i, criteria in enumerate(criteria_list):
        prompt += f"R{i+1}. {criteria.title}: {criteria.explanation}\n"

    # Add questions and standard answers
    prompt += "\nQUESTIONS AND STANDARD ANSWERS:\n"
    for q_id, q_data in questions_dict.items():
        prompt += f"{q_id}: {q_data.question}\nStandard Answer: {q_data.standard_answer}\n\n"

    # Instruction for structured output
    prompt += "\nINSTRUCTIONS:\n"
    prompt += "1. Evaluate the student's response against each question and the rubric criteria.\n"
    prompt += "2. For each question, provide a score (0-10) and detailed feedback.\n"
    prompt += "3. Provide an overall assessment of the student's work.\n"

    return prompt

# Define Pydantic models for structured output with Gemini
class PydanticQuestionEvaluation(BaseModel):
    """
    Pydantic model for individual question evaluation results from Gemini API.

    Attributes:
        question_id (str): The ID of the question (e.g., "Q1", "Q2").
        score (float): Numerical score assigned to the answer, typically 0-10.
        feedback (str): Detailed feedback on the student's answer.
    """
    question_id: str
    score: float
    feedback: str

class PydanticEvaluationResponse(BaseModel):
    """
    Pydantic model for complete evaluation response from Gemini API.

    Attributes:
        question_evaluations (List[PydanticQuestionEvaluation]): List of question evaluation results.
        overall_feedback (str): Overall feedback on the student's submission.
    """
    question_evaluations: List[PydanticQuestionEvaluation]
    overall_feedback: str

def evaluate_with_gemini(pdf_bytes, questions_dict, criteria_list, model_name="gemini-2.0-flash") -> Dict[str, Any]:
    """
    Evaluates a student's PDF submission using the Gemini API with structured output.

    Args:
        pdf_bytes (bytes): The PDF content in bytes.
        questions_dict (Dict): Dictionary mapping question IDs to QuestionRubric objects.
        criteria_list (List): List of RubricCriteria objects for evaluation.
        model_name (str, optional): The Gemini model to use. Defaults to "gemini-2.0-flash".

    Returns:
        Dict[str, Any]: A dictionary containing structured evaluation results with:
            - "results": A list of evaluation results for each question
            - "overall_feedback": Overall feedback on the submission
            - Potential "error" key if processing fails

    Raises:
        ValueError: If GEMINI_API_KEY is not set.
        Exception: Any exceptions from the Gemini API will be caught and formatted as error responses.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set in environment.")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(model_name)

    # Build the prompt
    prompt = build_prompt(criteria_list, questions_dict)

    # Configure the model for structured output
    response_config = {
        'response_mime_type': 'application/json',
        'response_schema': PydanticEvaluationResponse
    }

    # Generate content with structured output
    try:
        pdf_part = {"mime_type": "application/pdf", "data": pdf_bytes}
        response = model.generate_content(
            [pdf_part, prompt],
            generation_config=response_config
        )

        # Parse the structured response
        if hasattr(response, 'parsed'):
            # Convert to our own dataclass models
            question_evaluations = []
            parsed_data = response.parsed

            # Handle the case where parsed_data is a dictionary
            if isinstance(parsed_data, dict):
                evals = parsed_data.get("question_evaluations", [])
                overall_feedback = parsed_data.get("overall_feedback", "")

                for eval_item in evals:
                    question_evaluations.append(QuestionEvaluation(
                        question_id=eval_item.get("question_id", ""),
                        score=eval_item.get("score", 0.0),
                        feedback=eval_item.get("feedback", "")
                    ))
            else:
                # Handle the case where parsed_data is the actual PydanticEvaluationResponse
                evals = parsed_data.question_evaluations
                overall_feedback = parsed_data.overall_feedback

                for eval_item in evals:
                    question_evaluations.append(QuestionEvaluation(
                        question_id=eval_item.question_id,
                        score=eval_item.score,
                        feedback=eval_item.feedback
                    ))

            # Create our dataclass model
            evaluation_response = GeminiEvaluationResponse(
                question_evaluations=question_evaluations,
                overall_feedback=overall_feedback
            )

            # Return the formatted dictionary for application use
            formatted_response = evaluation_response.to_dict()

            # Add question text to the results for UI display
            for result in formatted_response["results"]:
                q_id = result["question_id"]
                if q_id in questions_dict:
                    result["question"] = questions_dict[q_id].question
                else:
                    result["question"] = "Unknown question"

            return formatted_response

        else:
            # Fallback to manual parsing if structured parsing fails
            parsed_response = json.loads(response.text)

            # Try to convert to our expected format
            formatted_response = {
                "results": [],
                "overall_feedback": parsed_response.get("overall_feedback", "")
            }

            # Process question evaluations
            evals = parsed_response.get("question_evaluations", [])
            for eval_item in evals:
                q_id = eval_item.get("question_id", "")
                if q_id and q_id in questions_dict:
                    formatted_response["results"].append({
                        "question_id": q_id,
                        "question": questions_dict[q_id].question,
                        "score": eval_item.get("score", 0),
                        "feedback": eval_item.get("feedback", "")
                    })

            return formatted_response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "error": f"Failed to process with Gemini: {str(e)}",
            "results": [],
            "overall_feedback": "Error occurred during evaluation."
        }
