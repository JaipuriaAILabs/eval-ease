import os
from dotenv import load_dotenv
import google.generativeai as genai
import io
import re
import json
import base64
from openai import OpenAI
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from .data_models import QuestionEvaluation, GeminiEvaluationResponse, PydanticQuestionEvaluation, PydanticEvaluationResponse

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def build_prompt(criteria_list, questions_dict) -> str:
    """
    Builds a structured prompt for the AI model to evaluate student responses.

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

    # Instruction for structured output and JSON format
    prompt += "\nINSTRUCTIONS:\n"
    prompt += "1. Evaluate the student's response against each question and the rubric criteria.\n"
    prompt += "2. For each question, provide a score (0-10) and detailed feedback.\n"
    prompt += "3. Provide an overall assessment of the student's work.\n"
    prompt += "4. Format your response as a JSON object with the following structure:\n"
    prompt += """
    {
      "question_evaluations": [
        {
          "question_id": "Q1",
          "score": 8.5,
          "feedback": "Detailed feedback here"
        },
        ...
      ],
      "overall_feedback": "Overall assessment here"
    }
    """

    return prompt

def evaluate_with_gemini(pdf_bytes, questions_dict, criteria_list, model_name="gpt-4.1") -> Dict[str, Any]:
    """
    Evaluates a student's PDF submission using the OpenAI API with GPT-4o.
    Despite the function name, this uses OpenAI's models instead of Gemini.

    Args:
        pdf_bytes (bytes): The PDF content in bytes.
        questions_dict (Dict): Dictionary mapping question IDs to QuestionRubric objects.
        criteria_list (List): List of RubricCriteria objects for evaluation.
        model_name (str, optional): Ignored for OpenAI. Always uses gpt-4o.

    Returns:
        Dict[str, Any]: A dictionary containing structured evaluation results with:
            - "results": A list of evaluation results for each question
            - "overall_feedback": Overall feedback on the submission
            - Potential "error" key if processing fails
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set in environment.")

    # Create OpenAI client
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Build the prompt
    prompt = build_prompt(criteria_list, questions_dict)

    try:
        # Convert PDF to base64 for sending in the message
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

        # Call the OpenAI API with PDF file
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are an AI evaluator for student responses. Provide detailed evaluation based on the rubric."},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "file", "file": {
                        "file_data": f"data:application/pdf;base64,{pdf_base64}",
                        "filename": "student_submission.pdf"
                    }}
                ]}
            ],
            response_format={"type": "json_object"}  # Only specify json_object without schema
        )

        # Parse the response
        parsed_response = json.loads(response.choices[0].message.content)

        # Convert to our expected format
        question_evaluations = []
        for eval_item in parsed_response.get("question_evaluations", []):
            question_evaluations.append(QuestionEvaluation(
                question_id=eval_item.get("question_id", ""),
                score=float(eval_item.get("score", 0)),
                feedback=eval_item.get("feedback", "")
            ))

        # Create our dataclass model
        evaluation_response = GeminiEvaluationResponse(
            question_evaluations=question_evaluations,
            overall_feedback=parsed_response.get("overall_feedback", "")
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

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "error": f"Failed to process with OpenAI: {str(e)}",
            "results": [],
            "overall_feedback": "Error occurred during evaluation."
        }
