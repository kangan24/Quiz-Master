from dotenv import load_dotenv
import os
from google import genai
import json
from datetime import datetime

load_dotenv()
api_key= os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)


# Generate Quiz
def generate_quiz(topic, difficulty):
    prompt = f"""
    Generate exactly 5 MCQ questions about {topic}.

    Difficulty: {difficulty}

    Return ONLY valid JSON in this format:
    [
        {{
            "question": "Question text",
            "options": {{
                "A": "Option A",
                "B": "Option B",
                "C": "Option C",
                "D": "Option D"
            }},
            "answer": "A",
            "explanation": "Explanation here in exactly 1 or 2 line"
        }}
    ]
    """
    try: 
        response= client.models.generate_content(
            model= "gemini-2.5-flash",
            contents= prompt,
            config={
                "response_mime_type": "application/json"
            }
        )
    except Exception as e:
        print("Error generating quiz:", e)
        return []

    try:
        quiz = json.loads(response.text)
        return quiz
    except json.JSONDecodeError:
        print("Failed to parse quiz data.")
        return []


# Ask Questions
def run_quiz(quiz):

    score = 0
    guesses = []

    for i, q in enumerate(quiz, start=1):

        print("\n" + "=" * 50)
        print(f"Question {i}/{len(quiz)}")
        print("=" * 50)

        print(q["question"])

        for key, value in q["options"].items():
            print(f"{key}. {value}")

        guess = input("\nEnter answer (A/B/C/D): ").upper()

        while guess not in ["A", "B", "C", "D"]:
            guess = input("Invalid choice. Enter A, B, C, or D: ").upper()

        guesses.append(guess)

        if guess == q["answer"]:
            print("✅ Correct!")
            score += 1
        else:
            print("❌ Wrong!")
            print(f"Correct Answer: {q['answer']}")
            print(f"Explanation: {q['explanation']}")
    
    percentage= (score / len(quiz)) * 100

    return score, percentage


#  AI Feedback
def generate_feedback(topic, difficulty, score, total_questions):

    percentage = (score / total_questions) * 100

    report_prompt = f"""
    The user completed a quiz.

    Topic: {topic}
    Difficulty: {difficulty}

    Score: {score}/{total_questions}
    Percentage: {percentage:.2f}%

    Provide:
    1. A short performance review.
    2. Strengths.
    3. Areas to improve.

    Keep it under 100 words point wise.
    """

    report = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=report_prompt
    )

    return report.text

# Show quiz history
def show_history():

    try:
        with open("quiz_history.txt", "r") as file:

            print("\n" + "=" * 50)
            print("QUIZ HISTORY")
            print("=" * 50)

            print(file.read())

    except FileNotFoundError:
        print("No quiz history found.")


# main execution

while True: 
    print("\n" + "=" * 50)
    print("QUIZ MASTER")
    print("=" * 50)

    choice = input(
        "\n1. Take Quiz"
        "\n2. View History"
        "\n3. Exit"
        "\n\nChoose option: "
    )

    if choice == "1":

        topic= input("Enter a topic to generate quiz on: ")
        difficulty= input("Choose difficulty level (Easy/Medium/Hard): ")

        quiz = generate_quiz(topic, difficulty)
        if not quiz:
            print("Could not generate quiz.")
            continue

        score, percentage = run_quiz(quiz)

        # results
        print("\n" + "=" * 50)
        print("RESULTS")
        print("=" * 50)

        print(f"Score: {score}/{len(quiz)}")
        print(f"Percentage: {percentage:.2f}%")

        # feedback
        feedback = generate_feedback(
            topic,
            difficulty,
            score,
            len(quiz)
        )

        print("\n" + "=" * 50)
        print("AI FEEDBACK")
        print("=" * 50)

        print(feedback)

        # history file
        with open("quiz_history.txt", "a") as file:
            file.write(
                f"{datetime.now():%Y-%m-%d %H:%M} | "
                f"{topic} | "
                f"{difficulty} | "
                f"{score}/{len(quiz)} | "
                f"{percentage:.2f}%\n"
            )
        
        input("\nPress Enter to return to menu...")

    elif choice == "2":
        show_history()
        input("\nPress Enter to return to menu...")

    elif choice == "3":
        print("Goodbye!")
        break

    else:
        print("Invalid choice.")